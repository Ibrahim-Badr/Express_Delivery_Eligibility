from unittest.mock import MagicMock, patch

from src.domain.entities import ModelEntity
from src.infra.local.memory_order_store import MemoryOrderStore
from src.orchestration.retraining import RetrainingOrchestrator
from tests.conftest import FakeModelRepository


def test_orchestrator_retraining_trigger_cycle(sample_order_dict):
    order_repo = MemoryOrderStore()
    model_repo = FakeModelRepository(available=True)

    orchestrator = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        min_roc_auc=0.75,
    )

    # Database is empty -> no retraining
    assert orchestrator.get_current_order_count() == 0
    assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is False

    # Populate 15 orders
    for i in range(15):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)
    assert orchestrator.get_current_order_count() == 15

    # Mock successful training producing ROC AUC = 0.88
    fake_card = ModelEntity(
        project="eligibilite-livraison-express",
        model_version="1.0.0",
        model_type="LogisticRegression",
        task="binary classification",
        target="express_eligible",
        threshold=0.5,
        features=["distance_km"],
        metrics={"roc_auc": 0.88},
    )

    with patch("src.orchestration.retraining.train", return_value=fake_card):
        # First trigger succeeds
        promoted = orchestrator.trigger_retrain_if_needed(min_new_orders=10)
        assert promoted is True
        assert orchestrator.last_trained_order_count == 15

        # Second trigger without new orders skips
        promoted_again = orchestrator.trigger_retrain_if_needed(min_new_orders=10)
        assert promoted_again is False

        # Add 10 more orders -> threshold reached again
        for i in range(15, 26):
            order_repo.save(f"CMD-{i:03d}", sample_order_dict)

        promoted_after_batch = orchestrator.trigger_retrain_if_needed(min_new_orders=10)
        assert promoted_after_batch is True
        assert orchestrator.last_trained_order_count == 26


def test_orchestrator_rejects_candidate_below_metric_threshold(sample_order_dict):
    order_repo = MemoryOrderStore()
    model_repo = FakeModelRepository(available=True)

    orchestrator = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        min_roc_auc=0.85,
    )

    for i in range(20):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)

    # Candidate with low metric (0.65 < 0.85)
    bad_card = ModelEntity(
        project="eligibilite-livraison-express",
        model_version="1.0.0",
        model_type="LogisticRegression",
        task="binary classification",
        target="express_eligible",
        threshold=0.5,
        features=["distance_km"],
        metrics={"roc_auc": 0.65},
    )

    with patch("src.orchestration.retraining.train", return_value=bad_card):
        promoted = orchestrator.trigger_retrain_if_needed(min_new_orders=10)
        assert promoted is False
        assert orchestrator.last_trained_order_count == 0
