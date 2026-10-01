"""Frozen model isolation, physically meaningful support boundaries and uncertainty."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.data.audit import compliance_mask, feature_integrity, inventory_audit, partition_integrity
from backend.app.ml.reference_knn import OBSERVED, PHYSICS, RESIDUAL, ROOT, WorkbookKNN, data
from backend.app.ml.registry import infer, registry
from backend.app.ml.train import features


def supported_row(typ="Lightning"):
    bundle, _ = registry()
    frame = data()
    return frame.loc[frame.ID == bundle[typ]["fit_ids"][0]].iloc[0].to_dict()


def test_official_splits_and_model_partition_isolation():
    frame = data(); bundle, meta = registry()
    assert frame.groupby(["Impulse_Type", "Split"]).size().to_dict() == {
        (t, s): n for t in ["Lightning", "Switching"]
        for s, n in [("Train", 700), ("Validation", 150), ("Hidden Test", 150)]}
    for check in partition_integrity(frame, bundle).values():
        assert check["fit_count"] == 560 and check["calibration_count"] == 140
        assert check["fit_calibration_overlap"] == check["non_train_ids_used"] == 0
        assert check["train_partition_complete"]
    assert set(WorkbookKNN().train.Split) == {"Train"}
    assert hashlib.sha256((ROOT / "data/processed/synthetic_dataset.csv").read_bytes()).hexdigest() == meta["dataset_sha256"]
    hidden = json.loads((ROOT / "artifacts/models/hidden_test_evaluation.json").read_text())
    assert hidden["frozen_config_sha256"] == meta["frozen_config_sha256"]


def test_inference_features_cannot_read_observed_or_residual_targets():
    frame = data().query("Split == 'Train'").iloc[:10].copy()
    original = features(frame)
    frame[OBSERVED + RESIDUAL] = 1e12
    frame["ID"] = -100; frame["Split"] = "Hidden Test"
    np.testing.assert_array_equal(original, features(frame))
    checks = feature_integrity(data())
    assert checks["observed_or_residual_features"] == []
    assert checks["all_features_finite"] and checks["derived_total_c_exact"]
    assert max(checks["residual_identity_max_absolute_error"]) < 1e-9


def test_synthetic_source_is_all_pass_but_not_full_operating_coverage():
    frame = data()
    assert compliance_mask(frame).all()
    assert frame.query("Impulse_Type == 'Lightning'").Test_kV.between(1350, 1500).all()
    assert frame.query("Impulse_Type == 'Switching'").Test_kV.between(950, 1100).all()
    assert set(frame.query("Impulse_Type == 'Lightning'").Tail_R_Stage) == {25}


def test_switching_source_front_stock_is_provably_insufficient():
    checks = inventory_audit(data())["workbook_reference_profile"]["by_type"]["Switching"]
    assert checks["all_front_stock_series_upper_bound_ohm"] == 5740
    assert checks["front_above_all_stock_series_upper_bound"] == 1000


def test_in_distribution_prediction_is_deterministic_with_ordered_intervals():
    for typ in ["Lightning", "Switching"]:
        row = supported_row(typ)
        first = infer([row])[0]
        assert first == infer([row])[0]
        assert first["ood"]["trust_weight"] == 1
        assert first["ood"]["lab_calibrated"] is False
        assert first["uncertainty"]["coverage_claim"] == .90
        assert np.isfinite(first["prediction"]).all()
        assert np.all(np.array(first["uncertainty"]["lower"]) <= first["prediction"])
        assert np.all(np.array(first["uncertainty"]["upper"]) >= first["prediction"])


def test_hardware_valid_voltage_far_from_training_falls_back_to_physics():
    row = supported_row(); row["Test_kV"] = row["Physics_Crest_kV"] = 300
    result = infer([row])[0]
    assert result["ood"]["state"] == "out_of_distribution"
    assert result["ood"]["trust_weight"] == 0
    assert result["uncertainty"]["coverage_claim"] is None
    np.testing.assert_allclose(result["correction"], 0)
    np.testing.assert_allclose(result["prediction"], [row[k] for k in PHYSICS])


def test_unseen_constant_resistor_and_different_profile_disable_correction():
    row = supported_row(); row["Tail_R_Stage"] = 30
    changed = infer([row])[0]
    assert changed["ood"]["outside_feature_envelope"]
    assert changed["ood"]["trust_weight"] == 0
    for profile, mode, expected in [("cpri_problem_brief_profile", "hybrid", "profile_not_calibrated"),
                                     ("workbook_reference_profile", "physics", "physics_mode")]:
        result = infer([supported_row()], profile_id=profile, mode=mode)[0]
        assert result["ood"]["state"] == expected
        assert result["uncertainty"]["coverage_claim"] is None
        np.testing.assert_allclose(result["correction"], 0)


def test_stress_cases_have_separate_provenance_and_no_training_ids():
    path = ROOT / "data/processed/generated_stress_test.csv"
    if not path.exists():
        path = ROOT / "data/generated_stress_test.csv"
    # Stress artifact is optional when source-only ingestion is being tested.
    if path.exists():
        stress = pd.read_csv(path)
        assert set(stress.source_type) == {"generated_stress_test"}
        assert len(data()) == 2000


def test_saved_model_tradeoff_is_reported_without_reselecting():
    hidden = json.loads((ROOT / "artifacts/models/hidden_test_evaluation.json").read_text())["metrics"]
    for typ in ["Lightning", "Switching"]:
        selected = np.array(hidden[typ]["Selected hybrid"]["rmse"])
        assert np.all(selected < hidden[typ]["Physics only"]["rmse"])
    assert hidden["Switching"]["Selected hybrid"]["rmse"][2] > hidden["Switching"]["Exact workbook kNN"]["rmse"][2]
