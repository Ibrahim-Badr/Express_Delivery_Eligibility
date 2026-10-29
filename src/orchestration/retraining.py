from __future__ import annotations

import logging
import time
from typing import Optional

from src.core.config import settings
from src.core.dependencies import get_model_repository, get_order_repository
from src.core.logging import setup_logging
from src.domain.entities import ModelEntity
from src.infra.abstractions.model_repository import ModelRepository
from src.infra.abstractions.order_repository import OrderRepository
from src.ml.training import train

logger = logging.getLogger("orchestrator.retraining")


class RetrainingOrchestrator:
    """Orchestrates ML model retraining based on incoming data volume or schedule.

    Implements the MLOps principle from Course Slides 7 & 8:
    - Training is an execution process, not a build-time process.
    - Automatically retrains when sufficient new orders arrive from the ERP stream.
    - Validates new candidate model performance before promoting artifacts.
    """

    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        model_repo: Optional[ModelRepository] = None,
        min_roc_auc: float = 0.70,
    ):
        self.order_repo = order_repo or get_order_repository()
        self.model_repo = model_repo or get_model_repository()
        self.min_roc_auc = min_roc_auc
        self.last_trained_order_count: int = 0

    def get_current_order_count(self) -> int:
        """Query current total order count in the database."""
        try:
            return self.order_repo.count()
        except Exception as exc:
            logger.warning("Could not count orders from repository: %s", exc)
            return 0

    def trigger_retrain_if_needed(self, min_new_orders: int = 50) -> bool:
        """Evaluate order growth and trigger model retraining if threshold reached."""
        current_count = self.get_current_order_count()
        new_orders = current_count - self.last_trained_order_count

        logger.info(
            "Retraining check: total_orders=%d, last_trained=%d, new_orders=%d, threshold=%d",
            current_count,
            self.last_trained_order_count,
            new_orders,
            min_new_orders,
        )

        should_retrain = current_count > 0 and (
            self.last_trained_order_count == 0 or new_orders >= min_new_orders
        )
        if should_retrain:
            logger.info("Threshold reached. Starting model retraining...")
            try:
                candidate_card: ModelEntity = train(
                    order_store=self.order_repo,
                    model_repo=self.model_repo,
                )
                roc_auc = candidate_card.metrics.get("roc_auc", 0.0)

                if roc_auc >= self.min_roc_auc:
                    self.last_trained_order_count = current_count
                    logger.info(
                        "Retraining successful! Candidate promoted with ROC AUC: %.4f",
                        roc_auc,
                    )
                    return True

                logger.warning(
                    "Retrained candidate rejected: ROC AUC %.4f below minimum %.4f",
                    roc_auc,
                    self.min_roc_auc,
                )
                return False
            except Exception as exc:
                logger.error("Retraining failed with error: %s", exc, exc_info=True)
                return False

        logger.info(
            "Not enough new orders for retraining yet (%d < %d).",
            new_orders,
            min_new_orders,
        )
        return False

    def run_daemon_loop(
        self,
        interval_seconds: float = 30.0,
        min_new_orders: int = 50,
        max_cycles: Optional[int] = None,
    ) -> None:
        """Continuously monitor database for retraining in a background loop."""
        logger.info(
            "Starting retraining orchestrator daemon (interval=%.1fs, threshold=%d)",
            interval_seconds,
            min_new_orders,
        )
        cycles = 0
        while max_cycles is None or cycles < max_cycles:
            self.trigger_retrain_if_needed(min_new_orders=min_new_orders)
            cycles += 1
            time.sleep(interval_seconds)


def run_orchestrator():
    """Entrypoint function for containerized orchestrator service."""
    setup_logging()
    orchestrator = RetrainingOrchestrator()
    orchestrator.run_daemon_loop(
        interval_seconds=settings.retrain_interval_seconds,
        min_new_orders=settings.retrain_min_new_orders,
    )


if __name__ == "__main__":
    run_orchestrator()
