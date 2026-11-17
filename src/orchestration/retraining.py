from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from src.core.config import settings
from src.core.dependencies import get_model_repository, get_order_repository
from src.core.logging import setup_logging
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_repository import OrderRepository
from src.ml.training import evaluate_pipeline_on_split, train_candidate

logger = logging.getLogger("orchestrator.retraining")


class RetrainingOrchestrator:
    """Orchestrates ML model retraining with dynamic growth triggers and Champion-Challenger.

    Implements the MLOps principles from Course Slides 7 & 8:
    - Training is an execution process, not a build-time process.
    - Dynamic hybrid trigger: max(min_new_orders, last_trained_order_count * growth_ratio).
    - Same-split Champion vs. Challenger evaluation before saving promoted artifacts.
    - Optional JSON state persistence so stateless Airflow/CLI runs preserve order watermarks.
    """

    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        model_repo: Optional[ModelRepository] = None,
        min_roc_auc: float = settings.retrain_min_roc_auc,
        min_f1_score: float = settings.retrain_min_f1_score,
        growth_ratio: float = settings.retrain_growth_ratio,
        f1_regression_tolerance: float = 0.01,
        state_path: Optional[Path | str] = None,
    ):
        self.order_repo = order_repo or get_order_repository()
        self.model_repo = model_repo or get_model_repository()
        self.min_roc_auc = min_roc_auc
        self.min_f1_score = min_f1_score
        self.growth_ratio = growth_ratio
        self.f1_regression_tolerance = f1_regression_tolerance
        self.state_path = Path(state_path) if state_path is not None else None
        self.last_trained_order_count: int = 0
        self.last_checked_order_count: int = 0
        self._load_state()

    @staticmethod
    def default_state_path() -> Path:
        """Return default persisted state file path inside the artifacts directory."""
        return Path(settings.artifacts_dir) / "retraining_state.json"

    def _load_state(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.last_trained_order_count = int(payload.get("last_trained_order_count", 0))
            self.last_checked_order_count = int(payload.get("last_checked_order_count", 0))
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Could not load orchestrator state from %s: %s", self.state_path, exc)

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "last_trained_order_count": self.last_trained_order_count,
                "last_checked_order_count": self.last_checked_order_count,
            }
            self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not persist orchestrator state to %s: %s", self.state_path, exc)

    def get_current_order_count(self) -> int:
        """Query current total order count in the repository."""
        try:
            return self.order_repo.count()
        except Exception as exc:
            logger.warning("Could not count orders from repository: %s", exc)
            return 0

    def compute_retrain_threshold(
        self, min_new_orders: int = settings.retrain_min_new_orders
    ) -> int:
        """Compute hybrid trigger threshold: max(min_new_orders, last_trained * growth_ratio)."""
        relative_growth = int(self.last_trained_order_count * self.growth_ratio)
        return max(min_new_orders, relative_growth)

    def should_trigger_retrain(
        self, min_new_orders: int = settings.retrain_min_new_orders
    ) -> bool:
        """Check whether enough new orders have arrived to justify candidate retraining."""
        current_count = self.get_current_order_count()
        new_orders = current_count - self.last_checked_order_count
        threshold = self.compute_retrain_threshold(min_new_orders=min_new_orders)

        logger.info(
            "Retraining check: total_orders=%d, last_trained=%d, new_since_check=%d, "
            "threshold=%d (min=%d, growth_ratio=%.2f)",
            current_count,
            self.last_trained_order_count,
            new_orders,
            threshold,
            min_new_orders,
            self.growth_ratio,
        )

        should_run = current_count > 0 and (
            self.last_checked_order_count == 0 or new_orders >= threshold
        )
        if not should_run:
            logger.info(
                "Not enough new orders for retraining yet (%d < %d).",
                new_orders,
                threshold,
            )
        return should_run

    def _get_champion_metrics(self, X_test: Any, y_test: list[int]) -> Optional[dict[str, float]]:
        """Evaluate the active champion model on the exact same held-out split."""
        if not self.model_repo.is_available():
            return None

        try:
            if X_test is not None and len(y_test) > 0:
                champion_pipeline = self.model_repo.load_pipeline()
                return evaluate_pipeline_on_split(champion_pipeline, X_test, y_test)
        except Exception as exc:
            logger.warning(
                "Could not evaluate active champion on current split (%s); "
                "falling back to stored champion metrics.",
                exc,
            )

        try:
            return self.model_repo.load_model_card().get("metrics", {})
        except Exception as exc:
            logger.warning("Could not load stored champion model card: %s", exc)
            return None

    def _should_promote(
        self,
        candidate_metrics: dict[str, float],
        champion_metrics: Optional[dict[str, float]],
    ) -> bool:
        """Verify quality floor and same-split Champion vs. Challenger non-regression."""
        cand_roc = float(candidate_metrics.get("roc_auc", 0.0))
        cand_f1 = float(candidate_metrics.get("f1_score", 0.0))

        if cand_roc < self.min_roc_auc or cand_f1 < self.min_f1_score:
            logger.warning(
                "Candidate rejected by quality floor: roc_auc=%.4f (min=%.4f), "
                "f1=%.4f (min=%.4f).",
                cand_roc,
                self.min_roc_auc,
                cand_f1,
                self.min_f1_score,
            )
            return False

        if not champion_metrics:
            return True

        champ_roc = float(champion_metrics.get("roc_auc", 0.0))
        champ_f1 = float(champion_metrics.get("f1_score", 0.0))
        beats_roc = cand_roc >= champ_roc
        within_f1_guardrail = cand_f1 >= (champ_f1 - self.f1_regression_tolerance)

        if not (beats_roc and within_f1_guardrail):
            logger.warning(
                "Candidate rejected by Champion-Challenger gate: candidate(roc=%.4f, f1=%.4f) "
                "vs champion(roc=%.4f, f1=%.4f).",
                cand_roc,
                cand_f1,
                champ_roc,
                champ_f1,
            )
            return False

        logger.info(
            "Candidate beat/matched champion on identical split: "
            "candidate(roc=%.4f, f1=%.4f) vs champion(roc=%.4f, f1=%.4f).",
            cand_roc,
            cand_f1,
            champ_roc,
            champ_f1,
        )
        return True

    def trigger_retrain_if_needed(
        self, min_new_orders: int = settings.retrain_min_new_orders
    ) -> bool:
        """Evaluate hybrid growth threshold and promote candidate only if it passes."""
        if not self.should_trigger_retrain(min_new_orders=min_new_orders):
            return False

        current_count = self.get_current_order_count()
        logger.info("Threshold reached. Training candidate model without overwriting champion...")
        self.last_checked_order_count = current_count
        self._save_state()
        try:
            candidate_pipeline, candidate_card, X_test, y_test = train_candidate(
                order_store=self.order_repo
            )
            champion_metrics = self._get_champion_metrics(X_test, y_test)
            if not self._should_promote(candidate_card.metrics, champion_metrics):
                return False

            self.model_repo.save(candidate_pipeline, candidate_card)
            self.last_trained_order_count = current_count
            self._save_state()
            logger.info(
                "Candidate promoted and saved (roc_auc=%.4f, f1=%.4f).",
                candidate_card.metrics.get("roc_auc", 0.0),
                candidate_card.metrics.get("f1_score", 0.0),
            )
            return True
        except Exception as exc:
            logger.error("Retraining failed with error: %s", exc, exc_info=True)
            return False

    def run_daemon_loop(
        self,
        interval_seconds: float = settings.retrain_interval_seconds,
        min_new_orders: int = settings.retrain_min_new_orders,
        max_cycles: Optional[int] = None,
    ) -> None:
        """Continuously monitor database for retraining in a background loop."""
        logger.info(
            "Starting retraining orchestrator daemon (interval=%.1fs, min_new=%d, "
            "growth_ratio=%.2f)",
            interval_seconds,
            min_new_orders,
            self.growth_ratio,
        )
        cycles = 0
        while max_cycles is None or cycles < max_cycles:
            self.trigger_retrain_if_needed(min_new_orders=min_new_orders)
            cycles += 1
            time.sleep(interval_seconds)


def run_orchestrator() -> None:
    """Entrypoint function for standalone containerized orchestrator service."""
    setup_logging()
    orchestrator = RetrainingOrchestrator(state_path=RetrainingOrchestrator.default_state_path())
    orchestrator.run_daemon_loop(
        interval_seconds=settings.retrain_interval_seconds,
        min_new_orders=settings.retrain_min_new_orders,
    )


if __name__ == "__main__":
    run_orchestrator()
