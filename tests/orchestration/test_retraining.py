from unittest.mock import patch

import pandas as pd

from src.domain.entities import ModelEntity
from src.infra.local.memory_order_store import MemoryOrderStore
from src.orchestration.retraining import RetrainingOrchestrator
from tests.conftest import FakeModelRepository, FakePipeline


def _make_card(roc_auc: float, f1_score: float) -> ModelEntity:
    return ModelEntity(
        project="eligibilite-livraison-express",
        model_version="1.0.0",
        model_type="LogisticRegression",
        task="binary classification",
        target="express_eligible",
        threshold=0.5,
        features=["distance_km"],
        metrics={"roc_auc": roc_auc, "f1_score": f1_score},
    )


def test_orchestrator_hybrid_threshold_and_promotion_cycle(sample_order_dict):
    order_repo = MemoryOrderStore()
    model_repo = FakeModelRepository(available=False)

    orchestrator = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        min_roc_auc=0.75,
        min_f1_score=0.75,
        growth_ratio=0.5,
    )

    # Database is empty -> no retraining
    assert orchestrator.get_current_order_count() == 0
    assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is False

    # Seed 30 orders; initial trigger establishes baseline champion
    for i in range(30):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)

    initial_pipeline = FakePipeline(positive_proba=0.80)
    initial_card = _make_card(roc_auc=0.84, f1_score=0.83)
    dummy_X = pd.DataFrame([sample_order_dict, sample_order_dict])
    dummy_y = [1, 0]

    with patch(
        "src.orchestration.retraining.train_candidate",
        return_value=(initial_pipeline, initial_card, dummy_X, dummy_y),
    ):
        assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is True
        assert orchestrator.last_trained_order_count == 30
        assert model_repo.load_pipeline() is initial_pipeline

        # Hybrid threshold = max(10, int(30 * 0.5)) = 15
        assert orchestrator.compute_retrain_threshold(min_new_orders=10) == 15

        # Add only 12 orders (< 15) -> should skip retraining
        for i in range(30, 42):
            order_repo.save(f"CMD-{i:03d}", sample_order_dict)
        assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is False

    # Add 3 more orders -> 15 new orders total -> threshold reached
    for i in range(42, 45):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)

    challenger_pipeline = FakePipeline(positive_proba=0.90)
    challenger_card = _make_card(roc_auc=0.89, f1_score=0.86)

    with (
        patch(
            "src.orchestration.retraining.train_candidate",
            return_value=(challenger_pipeline, challenger_card, dummy_X, dummy_y),
        ),
        patch(
            "src.orchestration.retraining.evaluate_pipeline_on_split",
            return_value={"roc_auc": 0.85, "f1_score": 0.84},
        ),
    ):
        assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is True
        assert orchestrator.last_trained_order_count == 45
        assert model_repo.load_pipeline() is challenger_pipeline


def test_orchestrator_rejects_below_floor_and_preserves_champion(sample_order_dict):
    order_repo = MemoryOrderStore()
    model_repo = FakeModelRepository(available=True, positive_proba=0.85)
    original_champion = model_repo.load_pipeline()

    orchestrator = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        min_roc_auc=0.75,
        min_f1_score=0.75,
    )

    for i in range(20):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)

    bad_pipeline = FakePipeline(positive_proba=0.51)
    bad_card = _make_card(roc_auc=0.72, f1_score=0.70)
    dummy_X = pd.DataFrame([sample_order_dict, sample_order_dict])
    dummy_y = [1, 0]

    with (
        patch(
            "src.orchestration.retraining.train_candidate",
            return_value=(bad_pipeline, bad_card, dummy_X, dummy_y),
        ),
        patch(
            "src.orchestration.retraining.evaluate_pipeline_on_split",
            return_value={"roc_auc": 0.85, "f1_score": 0.84},
        ),
    ):
        assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is False
        assert orchestrator.last_trained_order_count == 0
        # Ensure rejected candidate did NOT overwrite active champion
        assert model_repo.load_pipeline() is original_champion


def test_orchestrator_rejects_candidate_weaker_than_champion(sample_order_dict):
    order_repo = MemoryOrderStore()
    model_repo = FakeModelRepository(available=True, positive_proba=0.85)
    original_champion = model_repo.load_pipeline()

    orchestrator = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        min_roc_auc=0.75,
        min_f1_score=0.75,
    )

    for i in range(20):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)

    # Candidate passes hard floor (0.81 >= 0.75) but loses to champion (0.85) on same split
    weaker_pipeline = FakePipeline(positive_proba=0.70)
    weaker_card = _make_card(roc_auc=0.81, f1_score=0.82)
    dummy_X = pd.DataFrame([sample_order_dict, sample_order_dict])
    dummy_y = [1, 0]

    with (
        patch(
            "src.orchestration.retraining.train_candidate",
            return_value=(weaker_pipeline, weaker_card, dummy_X, dummy_y),
        ),
        patch(
            "src.orchestration.retraining.evaluate_pipeline_on_split",
            return_value={"roc_auc": 0.85, "f1_score": 0.84},
        ),
    ):
        assert orchestrator.trigger_retrain_if_needed(min_new_orders=10) is False
        assert model_repo.load_pipeline() is original_champion


def test_orchestrator_persists_state_across_airflow_runs(tmp_path, sample_order_dict):
    state_file = tmp_path / "retraining_state.json"
    order_repo = MemoryOrderStore()
    model_repo = FakeModelRepository(available=False)

    for i in range(20):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)

    dummy_X = pd.DataFrame([sample_order_dict, sample_order_dict])
    dummy_y = [1, 0]
    card = _make_card(roc_auc=0.86, f1_score=0.84)
    pipeline = FakePipeline(positive_proba=0.85)

    # First Airflow/CLI invocation triggers training and saves watermarks
    run_1 = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        growth_ratio=0.5,
        state_path=state_file,
    )
    assert run_1.should_trigger_retrain(min_new_orders=10) is True
    with patch(
        "src.orchestration.retraining.train_candidate",
        return_value=(pipeline, card, dummy_X, dummy_y),
    ):
        assert run_1.trigger_retrain_if_needed(min_new_orders=10) is True

    # Second independent process loads persisted watermarks (threshold = max(10, 20*0.5) = 10)
    run_2 = RetrainingOrchestrator(
        order_repo=order_repo,
        model_repo=model_repo,
        growth_ratio=0.5,
        state_path=state_file,
    )
    assert run_2.last_trained_order_count == 20
    assert run_2.should_trigger_retrain(min_new_orders=10) is False

    # Adding 10 more orders triggers next cycle in the new process
    for i in range(20, 30):
        order_repo.save(f"CMD-{i:03d}", sample_order_dict)
    assert run_2.should_trigger_retrain(min_new_orders=10) is True
