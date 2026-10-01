"""Read-only audit of supplied data and frozen models; never fits or scores hidden anew."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.ml.reference_knn import (
    FEATURES, OBSERVED, PHYSICS, RESIDUAL, ROOT, WorkbookKNN, data, metrics,
)
from backend.app.ml.registry import infer, registry
from backend.app.ml.train import MODEL_FEATURES, features

TYPES = ("Lightning", "Switching")
SPLITS = ("Train", "Validation", "Hidden Test")
TARGETS = ("Front/peak (µs)", "Tail (µs)", "Crest (kV)")


def clean(value):
    """Strict JSON: undefined correlations become null, never nonstandard NaN."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def compliance_mask(frame, outputs=OBSERVED):
    """Workbook H13 challenge rules, inclusive boundaries, independent of models."""
    rules = json.loads((ROOT / "config/compliance.json").read_text())
    front, tail, crest = (frame[c].to_numpy(float) for c in outputs)
    limits = [rules[t] for t in frame.Impulse_Type]
    return (
        (front >= [r["front_min_us"] for r in limits])
        & (front <= [r["front_max_us"] for r in limits])
        & (tail >= [r["tail_min_us"] for r in limits])
        & (tail <= [r["tail_max_us"] for r in limits])
        & (abs(crest / frame.Test_kV.to_numpy(float) - 1) <= rules["crest_tolerance_fraction"])
    )


def partition_integrity(frame, bundle):
    checks = {}
    for typ, model in bundle.items():
        train_ids = set(frame.loc[(frame.Split == "Train") & (frame.Impulse_Type == typ), "ID"])
        fit, cal = set(model["fit_ids"]), set(model["calibration_ids"])
        checks[typ] = {
            "official_train_count": len(train_ids), "fit_count": len(fit),
            "calibration_count": len(cal), "fit_calibration_overlap": len(fit & cal),
            "non_train_ids_used": len((fit | cal) - train_ids),
            "train_partition_complete": fit | cal == train_ids,
        }
    return checks


def feature_integrity(frame):
    values = features(frame)
    forbidden = set(OBSERVED + RESIDUAL + ["ID", "Split", "Impulse_Type"])
    return {
        "model_features": MODEL_FEATURES,
        "observed_or_residual_features": sorted(set(MODEL_FEATURES) & forbidden),
        "all_features_finite": bool(np.isfinite(values).all()),
        "derived_total_c_exact": bool(np.allclose(values[:, -1], frame.Load_C_pF + frame.Divider_C_pF + frame.Stray_C_pF)),
        "physics_crest_equals_requested_voltage": bool(np.allclose(frame.Physics_Crest_kV, frame.Test_kV)),
        "residual_identity_max_absolute_error": np.max(abs(frame[OBSERVED].to_numpy() - frame[PHYSICS].to_numpy() - frame[RESIDUAL].to_numpy()), axis=0).tolist(),
        "interpretation": "Physics_Crest_kV duplicates requested voltage by source definition. It is not measured-target leakage; it adds no independent information. Observed and residual columns are excluded from inference features.",
    }


def inventory_audit(frame):
    profiles = json.loads((ROOT / "config/generator_profiles.json").read_text())
    result = {}
    for profile in profiles:
        by_type = {}
        for typ in TYPES:
            f = frame[frame.Impulse_Type == typ]
            tail = profile["lightning_tail_values" if typ == "Lightning" else "switching_tail_values"]
            count = profile["units_per_value_per_stage"]
            maximum = sum(profile["front_values"]) * count if count is not None else None
            by_type[typ] = {
                "rows": len(f),
                "front_not_a_literal_stock_value": int((~f.Front_R_Stage.isin(profile["front_values"])).sum()),
                "tail_not_a_literal_stock_value": int((~f.Tail_R_Stage.isin(tail)).sum()),
                "all_front_stock_series_upper_bound_ohm": maximum,
                "front_above_all_stock_series_upper_bound": int((f.Front_R_Stage > maximum).sum()) if maximum is not None else None,
                "note": "Not a literal stock value does not imply impossible: networks can realize some values. Above the all-series bound does prove impossible for any passive series/parallel combination of this positive stock.",
            }
        result[profile["id"]] = {"by_type": by_type,
            "stock_quantity_verified": count is not None,
            "source_capacitance_uf": profile["stage_c_uf"],
            "dataset_profile_compatible": profile["id"] == "workbook_reference_profile",
            "production_ml_enabled_for_profile": profile["id"] == "workbook_reference_profile",
            "notes": profile["notes"]}
    return result


def validation_diagnostics(frame):
    """Additional validation diagnostics only; hidden outcomes never predicted here."""
    diagnostics, pooled_y, pooled_k = {}, [], []
    exact = WorkbookKNN()
    for typ in TYPES:
        va = frame[(frame.Split == "Validation") & (frame.Impulse_Type == typ)]
        outputs = infer(va.to_dict("records"))
        predicted = np.array([r["prediction"] for r in outputs])
        y = va[OBSERVED].to_numpy()
        lower = np.array([r["uncertainty"]["lower"] for r in outputs])
        upper = np.array([r["uncertainty"]["upper"] for r in outputs])
        covered = (y >= lower) & (y <= upper)
        knn = va[PHYSICS].to_numpy() + exact.predict(va)
        actual_pass = compliance_mask(va)
        copy = va.copy(); copy[OBSERVED] = predicted
        predicted_pass = compliance_mask(copy)
        diagnostics[typ] = {
            "deployed_gated_metrics": metrics(y, predicted),
            "support_counts": dict(Counter(o["ood"]["state"] for o in outputs)),
            "interval_coverage_by_target_validation": covered.mean(axis=0).tolist(),
            "interval_joint_coverage_validation": float(covered.all(axis=1).mean()),
            "interval_caveat": "Descriptive Validation diagnostic, not a coverage guarantee; uncalibrated widened OOD envelopes included.",
            "decision_diagnostics": {
                "actual_pass_count": int(actual_pass.sum()), "actual_fail_count": int((~actual_pass).sum()),
                "nominal_false_pass_count": int((predicted_pass & ~actual_pass).sum()),
                "nominal_false_fail_count": int((~predicted_pass & actual_pass).sum()),
                "false_pass_rate_on_actual_failures": float((predicted_pass & ~actual_pass).sum() / (~actual_pass).sum()) if (~actual_pass).any() else None,
                "accuracy": float((predicted_pass == actual_pass).mean()),
                "note": "All-pass source data cannot estimate failure-detection sensitivity or false-pass rate on failures.",
            },
        }
        pooled_y.append(y); pooled_k.append(knn)
    return diagnostics, metrics(np.concatenate(pooled_y), np.concatenate(pooled_k))


def collect():
    frame = data(); bundle, meta = registry()
    # The immutable saved hidden evaluation is read, never recalculated or used for selection.
    hidden_path = ROOT / "artifacts/models/hidden_test_evaluation.json"
    hidden = json.loads(hidden_path.read_text())
    numeric = [c for c in frame.select_dtypes("number").columns if c != "ID"]
    distributions, correlations, combinations = {}, {}, {}
    for typ in TYPES:
        g = frame[frame.Impulse_Type == typ]
        correlations[typ] = g[numeric].corr().to_dict()
        combos = g.groupby(["Stages", "Front_R_Stage", "Tail_R_Stage"]).size().reset_index(name="count")
        combinations[typ] = {"unique_count": len(combos), "combinations": combos.to_dict("records")}
        distributions[typ] = {}
        for split in SPLITS:
            part = g[g.Split == split]
            summary = part[numeric].describe(percentiles=[.05, .25, .5, .75, .95]).T
            summary["unique"] = part[numeric].nunique()
            distributions[typ][split] = summary.to_dict("index")
    non_id = [c for c in frame.columns if c not in ["ID", "Split"]]
    source_features = ["Impulse_Type"] + FEATURES + ["Stages", "Charge_kV_Stage"]
    duplicate_inputs = frame.duplicated(source_features, keep=False)
    cross_split = frame.loc[duplicate_inputs].groupby(source_features, dropna=False).Split.nunique()
    diag, pooled = validation_diagnostics(frame)
    coverage = {}
    for typ in TYPES:
        train = frame[(frame.Split == "Train") & (frame.Impulse_Type == typ)]
        coverage[typ] = {"train_voltage_min_kv": float(train.Test_kV.min()), "train_voltage_max_kv": float(train.Test_kV.max()),
                         "train_stages": sorted(train.Stages.unique().tolist()),
                         "train_tail_resistors": sorted(train.Tail_R_Stage.unique().tolist())}
    compliance = {}
    for (typ, split), f in frame.groupby(["Impulse_Type", "Split"]):
        compliance[f"{typ}/{split}"] = {"rows": len(f), "observed_pass": int(compliance_mask(f).sum()),
                                       "reference_physics_pass": int(compliance_mask(f, PHYSICS).sum())}
    stress_path = ROOT / "artifacts/stress_test_summary.json"
    return clean({
        "audit_version": "data-audit-v1", "source_type": "supplied_synthetic",
        "dataset_sha256": hashlib.sha256((ROOT / "data/processed/synthetic_dataset.csv").read_bytes()).hexdigest(),
        "frozen_model_version": meta["version"], "frozen_config_sha256": meta["frozen_config_sha256"],
        "hidden_evaluation_sha256": hashlib.sha256(hidden_path.read_bytes()).hexdigest(),
        "hidden_policy": "Only previously saved evaluation metrics are displayed. No new hidden predictions, model fits, threshold changes or model selection in audit.",
        "counts": {"rows": len(frame), "columns": len(frame.columns), "splits": frame.Split.value_counts().to_dict(),
                   "by_type_and_split": {f"{a}/{b}": n for (a, b), n in frame.groupby(["Impulse_Type", "Split"]).size().items()}},
        "integrity": {"missing_values": int(frame.isna().sum().sum()), "duplicate_ids": int(frame.ID.duplicated().sum()),
                      "duplicate_rows_ignoring_id_split": int(frame.duplicated(non_id).sum()),
                      "duplicate_input_rows": int(duplicate_inputs.sum()),
                      "input_signatures_crossing_splits": int((cross_split > 1).sum()),
                      "schema_matches_manifest": frame.columns.tolist() == json.loads((ROOT / "data/processed/manifest.json").read_text())["columns"],
                      "frozen_training_dataset_hash_matches": meta["dataset_sha256"] == hashlib.sha256((ROOT / "data/processed/synthetic_dataset.csv").read_bytes()).hexdigest(),
                      "hidden_freeze_hash_matches": meta["frozen_config_sha256"] == hidden["frozen_config_sha256"]},
        "partitions": partition_integrity(frame, bundle), "feature_integrity": feature_integrity(frame),
        "distributions": distributions, "correlations_pearson": correlations, "stage_resistor_combinations": combinations,
        "training_support": coverage, "compliance_balance": compliance, "profile_compatibility": inventory_audit(frame),
        "validation_models_frozen": meta["validation"], "selected_models_frozen": meta["selection"],
        "cv_frozen": meta["cv"], "hidden_metrics_saved": hidden["metrics"],
        "validation_deployed_diagnostics": diag, "pooled_exact_knn_validation_secondary": pooled,
        "interval_halfwidths": {typ: b["interval_halfwidth"].tolist() for typ, b in bundle.items()},
        "stress_tests_separate": json.loads(stress_path.read_text()) if stress_path.exists() else None,
    })


def metric_rows(audit, split):
    source = audit["validation_models_frozen"] if split == "Validation" else audit["hidden_metrics_saved"]
    rows = []
    for typ in TYPES:
        for model, metric in source[typ].items():
            for j, target in enumerate(TARGETS):
                rows.append({"Impulse": typ, "Target": target, "Model": model,
                             "MAE": metric["mae"][j], "RMSE": metric["rmse"][j],
                             "MAPE (%)": metric["mape_pct"][j], "R²": metric["r2"][j],
                             "RMSE / tolerance": metric["normalized_rmse_tolerance"][j],
                             "RMSE gain vs physics (%)": metric["rmse_improvement_vs_physics_pct"][j],
                             "Latency (ms/record)": metric.get("inference_ms_per_record")})
    return rows


def markdown(a):
    lines = ["# Supplied data and frozen model audit", "",
        "All benchmark data is supplied synthetic data. Laboratory validation is pending. The frozen production models and previously saved Hidden Test evaluation were not changed or retrained by this audit.", "",
        "## Findings that change how the product should be used", "",
        "- All 2,000 supplied observations pass the challenge waveform limits. This dataset cannot demonstrate failure-detection sensitivity or a laboratory false-pass rate.",
        "- The voltage support is narrow: Lightning approximately 1,350–1,500 kV and Switching approximately 950–1,100 kV. Hardware-valid requests elsewhere require physics fallback and an explicit support warning.",
        "- All 1,000 Switching front resistances (9,370–21,810 Ω/stage) exceed 5,740 Ω/stage, the maximum obtained by putting every workbook front component in series. Those settings are impossible with the supplied workbook stock. Reference predictions cannot be presented as constructible recommendations.",
        "- The dataset uses 3 µF/stage; the PDF machine uses 0.125 µF/stage. PDF stock quantities are unknown. Synthetic residual corrections are disabled outside the workbook profile. An explicit stock assumption is not a verified hardware inventory.",
        "- The exact workbook formula reproduces the displayed case and all 1,400 helper distances/weights. Its recomputed Validation scores differ from the hardcoded published table; the unresolved source discrepancy is preserved in source reconciliation.", "",
        "## Frozen per-target performance", "",
        "The table compares the selected residual predictor before production OOD gating. Validation selects models and therefore has selection optimism. Hidden Test is the saved one-time evaluation after freeze. No hidden result changed the selection.", "",
        "| Split | Regime / target | Physics RMSE | Exact kNN RMSE | Selected RMSE | Gain vs physics | Gain vs kNN |", "|---|---|---:|---:|---:|---:|---:|"]
    for split, source in [("Validation", a["validation_models_frozen"]), ("Hidden Test", a["hidden_metrics_saved"])]:
        for typ in TYPES:
            for j, target in enumerate(TARGETS):
                p, k, s = [source[typ][name]["rmse"][j] for name in ["Physics only", "Exact workbook kNN", "Selected hybrid"]]
                lines.append(f"| {split} | {typ} {target} | {p:.6g} | {k:.6g} | {s:.6g} | {100*(1-s/p):.2f}% | {100*(1-s/k):.2f}% |")
    lines += ["", "The selected hybrid improves all six Hidden Test outputs against physics; five of six improve against exact kNN. Switching crest RMSE is 4.1209 kV versus exact kNN 3.9293 kV (4.88% worse). Preserve this result: do not claim uniform improvement.", "",
        "Exact kNN uses all 1,400 Train rows. Advanced models fit 560 rows per regime and reserve 140 per regime for calibration. Exact kNN is excluded from calibrated model selection because its fitted reference uses those calibration rows; comparing its raw benchmark is still useful, but its data budget differs.", "",
        "Pooled exact-kNN Validation R² is approximately 0.9999 for front and 0.9997 for tail, but within-regime R² is much weaker: Lightning tail 0.2791; Switching peak 0.3395; Switching tail 0.0790. The separation of 1.2/50 and 250/2500 timescales drives the pooled result. Headline metrics must remain per regime.", "",
        "## Splits, features and leakage checks", "",
        f"The source has {a['counts']['rows']} rows and the original {a['counts']['columns']}-column schema: Train 1,400, Validation 300, Hidden Test 300, balanced 700/150/150 within each regime. Missing values: {a['integrity']['missing_values']}. Duplicate IDs: {a['integrity']['duplicate_ids']}. Duplicate full records ignoring ID/Split: {a['integrity']['duplicate_rows_ignoring_id_split']}. Repeated input signatures crossing splits: {a['integrity']['input_signatures_crossing_splits']}.", "",
        "Fit and calibration IDs are disjoint, collectively cover official Train, and contain no Validation or Hidden Test ID. Features exclude observed values, residual targets, ID and Split. Derived total capacitance is checked. Source residuals equal observed minus physics to numerical precision. Physics crest equals requested voltage by definition, so its perfect correlation is expected; it is not an independent learned physical quantity.", "",
        "No claim of causal independence follows from these structural checks: all outcomes were generated synthetically by an unavailable generator script. Source-generation bias and correlations cannot establish laboratory generalization.", "",
        "## Uncertainty review", "",
        "The calibration partition is held out from fitting, hyperparameter CV and Validation model selection. Selecting a model using the separate Validation set does not itself contaminate calibration. Calibration residuals are computed only after the per-target selection.", "",
        "The 90% conformal statement is marginal, per target, under exchangeability with the supplied synthetic distribution. It is not simultaneous coverage of all three outputs, conditional coverage among supported inputs, coverage of an optimizer-selected candidate, or laboratory coverage. The quantile implementation is slightly conservative: with 140 calibration rows, its higher-interpolated quantile can select one order statistic above the minimal finite-sample rank.", "",
        "Production uses the calibrated widths only with full residual weight. Partial trust or another profile uses an explicitly uncalibrated widened sensitivity envelope. Any robust-PASS statement means the returned interval lies inside the challenge limits; it is not a measured safety probability. OOD distances depend on scaled features and the fit partition; a feature range breach greater than 20% disables the correction. Constant features form especially strict boundaries: Lightning tail is always 25 Ω/stage in the data.", "",
        "Saved ungated marginal Validation coverage (front, tail, crest): " + "; ".join(f"{t}: {a['validation_models_frozen'][t]['Selected hybrid']['interval_coverage_validation']}" for t in TYPES) + ". The HTML report separately shows coverage of the deployed gated output. These empirical proportions do not upgrade the theoretical guarantee.", "",
        "## Model-selection limitations and next-version work", "",
        "Five advanced families were compared: Ridge, scaled SVR, Random Forest, Extra Trees and HistGradientBoosting. Three-fold CV occurs inside the fit partition. Validation selects one model per target. Optional external boosting libraries were not needed.", "",
        "The frozen CV scorer averages MSE in original output units, despite scaling the training targets. Larger-unit targets therefore dominate hyperparameter selection (crest for Lightning, tail for Switching). A future version should preregister tolerance-normalized or per-target CV, nested selection and a new untouched evaluation set. Do not change this version using the exposed Hidden Test. Add uncertainty for model-selection variability, joint intervals and calibrated decision risk only after suitable data exists.", "",
        "Stored Hidden Test latency is unavailable, not zero. Validation latency is batch timing from the training run and excludes API/optimizer overhead. Small differences between models have not been significance-tested.", "",
        "## Engineering stress tests remain separate", "",
        "Stress cases carry source_type=generated_stress_test and never enter training or official model benchmarks. The 120 generated circuit scenarios contain 23 reference PASS cases, 2 circuit PASS cases and 21 reference-PASS/circuit-FAIL disagreements. These are model disagreements between unvalidated simulators, not measured false passes. The report must not turn 82.5% agreement into a laboratory accuracy claim.", "",
        "## Reproduce", "", "Run `python3 -m backend.app.data.audit` to rebuild the standalone HTML and JSON audit without modifying frozen models. Run `python3 -m pytest tests/test_data_ml.py tests/test_workbook_parity.py -q` for data/model isolation and parity checks.", "",
        "Sources: original workbook preserved in data/source; full cell/formula snapshot in artifacts/reference_workbook_snapshot.json; schema manifest in data/processed/manifest.json; profile definitions in config/generator_profiles.json; frozen metrics in artifacts/models/registry.json and hidden_test_evaluation.json. Exhaustive feature distributions, correlations and setting combinations are in artifacts/data_audit.json; reports/data_audit.html provides the readable tables and charts."]
    return "\n".join(lines) + "\n"


def figure_data_uri(fig):
    buffer = io.BytesIO(); fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def charts(frame, audit):
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/impulsetwin-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    output = {}
    palette = ["#127b76", "#b87819", "#5965ad"]
    for typ in TYPES:
        f = frame[frame.Impulse_Type == typ]
        plot_cols = FEATURES + ["Stages", "Charge_kV_Stage"] + PHYSICS + RESIDUAL
        fig, axes = plt.subplots(4, 4, figsize=(16, 12))
        for ax, col in zip(axes.flat, plot_cols):
            bins = np.histogram_bin_edges(f[col], bins=18)
            for split, color in zip(SPLITS, palette):
                ax.hist(f.loc[f.Split == split, col], bins=bins, density=True, histtype="step", linewidth=1.5, label=split, color=color)
            ax.set_title(col.replace("_", " "), fontsize=9); ax.tick_params(labelsize=8)
        axes.flat[0].legend(fontsize=8)
        fig.suptitle(f"{typ}: source feature and residual distributions by official split", fontsize=16)
        fig.tight_layout(); output[f"dist_{typ}"] = figure_data_uri(fig); plt.close(fig)
        corr = f[[*FEATURES, *PHYSICS, *RESIDUAL]].corr()
        fig, ax = plt.subplots(figsize=(11, 9)); im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(corr)), corr.columns, rotation=65, ha="right", fontsize=8)
        ax.set_yticks(range(len(corr)), corr.columns, fontsize=8)
        fig.colorbar(im, ax=ax, label="Pearson r"); ax.set_title(f"{typ}: feature / physics / residual correlations")
        fig.tight_layout(); output[f"corr_{typ}"] = figure_data_uri(fig); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, typ in zip(axes, TYPES):
        saved = audit["hidden_metrics_saved"][typ]
        for offset, name, color in zip([-.25, 0, .25], ["Physics only", "Exact workbook kNN", "Selected hybrid"], palette):
            vals = saved[name]["normalized_rmse_tolerance"]
            ax.bar(np.arange(3) + offset, vals, width=.25, label=name, color=color)
        ax.set_xticks(range(3), ["Front/peak", "Tail", "Crest"]); ax.set_title(typ)
        ax.set_ylabel("RMSE / challenge tolerance"); ax.legend(fontsize=8)
    fig.suptitle("Saved one-time Hidden Test: per-regime errors", fontsize=15)
    fig.tight_layout(); output["benchmark"] = figure_data_uri(fig); plt.close(fig)
    return output


def table(rows):
    return pd.DataFrame(rows).to_html(index=False, border=0, escape=True, float_format=lambda x: f"{x:.6g}", na_rep="Unavailable")


def html_report(a, images):
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ImpulseTwin · Data and model audit</title>",
    "<style>body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f0f4f6;color:#18313c}main{max-width:1280px;margin:auto;padding:36px 28px}h1{font-size:40px;line-height:1.15}h2{margin-top:36px;color:#075e5a}h3{margin-top:26px}p{max-width:100ch}.label{color:#536b75;font-size:13px;letter-spacing:.1em;text-transform:uppercase}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card,section{background:white;padding:22px;border-radius:12px;margin:14px 0;border:1px solid #d9e4e8}.card strong{font-size:32px;display:block}.warning{border-left:5px solid #c98b29;background:#fff8e9;padding:18px 22px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;background:#e7eff1;white-space:nowrap}td,th{padding:9px 10px;border-bottom:1px solid #e0e8ea}td{font-variant-numeric:tabular-nums}tbody tr:hover{background:#f1f8f7}img{max-width:100%;height:auto}summary{font-weight:650;cursor:pointer;color:#075e5a;padding:14px 0}details{border-bottom:1px solid #d9e4e8}code{font-size:13px;word-break:break-all}.muted{color:#536b75}a{color:#075e5a} @media(max-width:700px){.cards{grid-template-columns:1fr}main{padding:20px 14px}h1{font-size:32px}}@media print{details>*{display:block!important}section,.card{break-inside:avoid}body{background:white}main{padding:0}}</style><main>",
    "<div class='label'>ImpulseTwin AI · Source evidence · Frozen model review</div><h1>Know where the model earns trust</h1>",
    "<p>Official synthetic data, unchanged splits, source hardware checks and per-regime performance. This audit rebuilds reports without changing or retraining the frozen models. Laboratory validation remains pending.</p>",
    "<div class='cards'><div class='card'><strong>2,000</strong>supplied synthetic records<br>1,400 Train · 300 Validation · 300 Hidden Test</div><div class='card'><strong>6 / 6</strong>saved Hidden Test outputs improve on physics<br>5 / 6 improve on exact workbook kNN</div><div class='card'><strong>0</strong>observed waveform failures in source data<br>False-pass risk cannot be established</div></div>",
    "<div class='warning'><b>Hardware mismatch: all 1,000 Switching settings exceed workbook front stock.</b> The dataset needs 9,370–21,810 Ω per stage. Every workbook front component in series reaches only 5,740 Ω. Keep a calculator prediction distinct from a buildable setup. PDF hardware has different capacitance and unverified quantities.</div>",
    "<section><h2>Per-regime benchmark</h2><p>These are saved model scores before OOD gating. Hidden Test was evaluated once after freeze. Switching crest is 4.88% worse than exact kNN (4.1209 versus 3.9293 kV RMSE). No model was changed in response.</p>",
    f"<img alt='Errors normalized by challenge tolerance for physics, exact workbook kNN and selected models' src='{images['benchmark']}'>",
    "<p>The reference kNN uses all 1,400 Train records. Advanced models use 560 fit records per regime and keep 140 for calibration. It is excluded from calibrated selection because its reference fit includes the calibration records.</p>",
    "<details open><summary>Saved Hidden Test metrics · all targets</summary><div class='scroll'>" + table(metric_rows(a, "Hidden Test")) + "</div></details>",
    "<details><summary>Validation · every model, every target</summary><p>Validation was used to select models; its selected score has selection optimism. Timing is batch inference only, not end-to-end service latency. Hidden timing is unavailable.</p><div class='scroll'>" + table(metric_rows(a, "Validation")) + "</div></details>",
    "<p class='muted'>Do not headline pooled R²: exact kNN pooled Validation front/tail R² is approximately 0.9999/0.9997, while Lightning tail is 0.2791, Switching peak 0.3395 and Switching tail 0.0790. The broad separation between the two waveform scales inflates pooled R².</p></section>",
    "<section><h2>Split isolation and data integrity</h2><div class='scroll'>" + table([{"Regime": t, **v} for t, v in a["partitions"].items()]) + "</div><p>Zero missing values, duplicate IDs, duplicate complete records or repeated input signatures crossing splits. The original 22 columns and dataset hash match the frozen model. Calibration and fit IDs are disjoint and belong only to official Train.</p>",
    "<p>Inference features exclude observed outputs and residual targets. Total capacitance is derived from input capacitances. Physics crest is exactly requested test voltage by workbook definition, not an independent prediction. Correlation does not establish target leakage or laboratory validity. Synthetic generation bias cannot be ruled out without its generating script and real trial data.</p></section>",
    "<section><h2>Where training support ends</h2><div class='scroll'>" + table([{"Regime": t, **v} for t, v in a["training_support"].items()]) + "</div><p>The full machine voltage range is mostly outside this support. Lightning tail resistance is constant at 25 Ω. Alternative resistors or generator profiles need explicit OOD handling. These are training limits, not hardware limits.</p>"]
    for typ in TYPES:
        parts += [f"<details><summary>{typ} · distributions and residuals</summary><img alt='{typ} feature distributions by official split' src='{images[f'dist_{typ}']}'></details>",
                  f"<details><summary>{typ} · Pearson correlations</summary><p>Blank cells have undefined correlation because a variable is constant.</p><img alt='{typ} feature and residual correlation matrix' src='{images[f'corr_{typ}']}'></details>"]
        for split in SPLITS:
            parts += [f"<details><summary>{typ} / {split} · every numeric column</summary><div class='scroll'>" + table([{"Feature": c, **v} for c, v in a["distributions"][typ][split].items()]) + "</div></details>"]
        parts += [f"<details><summary>{typ} · {a['stage_resistor_combinations'][typ]['unique_count']} unique stage/resistor combinations</summary><div class='scroll'>" + table(a["stage_resistor_combinations"][typ]["combinations"]) + "</div></details>"]
    parts += ["</section><section><h2>Compliance balance and hardware compatibility</h2><div class='scroll'>" + table([{"Regime / split": k, **v} for k, v in a["compliance_balance"].items()]) + "</div><p>All source rows pass the challenge limits. An all-PASS classifier would look perfect here. There is no denominator of true failures from which to estimate false-pass risk on failures.</p>"]
    for profile, info in a["profile_compatibility"].items():
        parts += [f"<details><summary>{html.escape(profile)}</summary><p>Source stage capacitance: {info['source_capacitance_uf']} µF. ML transfer allowed: {info['production_ml_enabled_for_profile']}. Source stock quantity supplied: {info['stock_quantity_verified']}.</p><div class='scroll'>" + table([{"Regime": t, **{k:v for k,v in v.items() if k != "note"}} for t, v in info["by_type"].items()]) + "</div><p>A value absent from literal stock can sometimes be built from networks. Exceeding the sum of all positive stock proves it cannot. The PDF machine and briefing profile cannot inherit the workbook calibration.</p></details>"]
    parts += ["</section><section><h2>Uncertainty: what 90% means</h2><p>Selection on separate Validation data does not contaminate the held-out Train calibration partition. The conformal statement is <b>marginal per target under synthetic exchangeability</b>. It is not joint three-output coverage, conditional coverage within the supported subset, coverage after optimizer selection, or laboratory coverage.</p><p>Only full-trust predictions retain the calibrated residual correction. Partial trust and other profiles use an explicitly uncalibrated sensitivity envelope. Robust PASS means the returned interval lies inside tolerance; it is not a measured safety probability. The finite-sample quantile implementation is slightly conservative by one possible order statistic.</p>"]
    diagnostic_rows = []
    for typ, d in a["validation_deployed_diagnostics"].items():
        for j, name in enumerate(TARGETS):
            diagnostic_rows.append({"Regime": typ, "Target": name, "Deployed gated RMSE": d["deployed_gated_metrics"]["rmse"][j], "Empirical interval coverage": d["interval_coverage_by_target_validation"][j]})
    parts += ["<div class='scroll'>" + table(diagnostic_rows) + "</div><p>These are descriptive diagnostics on Validation, including widened uncalibrated envelopes. They are not a new nominal coverage claim.</p>",
        "<div class='scroll'>" + table([{"Regime": t, **v["support_counts"], "Empirical joint coverage": v["interval_joint_coverage_validation"]} for t, v in a["validation_deployed_diagnostics"].items()]) + "</div></section>",
        "<section><h2>Independent engineering stress tests</h2><p>Source type: <code>generated_stress_test</code>. 120 broad simulated cases are separate from the official benchmark. Reference PASS: 23; circuit PASS: 2; reference-PASS/circuit-FAIL: 21. These are disagreements between unvalidated models, not measured laboratory false passes. Their 82.5% agreement is not laboratory accuracy. Inventory feasibility is tested separately.</p></section>",
        "<section><h2>Review decisions and next version</h2><ul><li>Preserve the exact reference case and unresolved hardcoded published-table discrepancy.</li><li>Keep physics-only selectable; disable transferred ML corrections on the PDF profile.</li><li>Report the Switching crest regression against kNN and the unequal training data budgets.</li><li>Use tolerance-normalized or per-target CV in a future preregistered pipeline. Current CV averages original-unit MSE; larger-unit outputs dominate hyperparameter choice.</li><li>Acquire boundary/failure examples and measured trial shots. Keep a new untouched evaluation set for any next version.</li></ul><p>No laboratory validation or reduction in real trial-shot count has been demonstrated yet. The software establishes a reproducible benchmark and an auditable workflow for obtaining that evidence.</p></section>",
        "<footer class='muted'><p>Reproduce: <code>python3 -m backend.app.data.audit</code>. Frozen model: " + html.escape(a["frozen_model_version"]) + ".</p><p>Dataset SHA-256: <code>" + a["dataset_sha256"] + "</code><br>Frozen configuration SHA-256: <code>" + a["frozen_config_sha256"] + "</code></p><p>Sources: supplied workbook; exported source snapshot; versioned generator profiles; saved model registry and one-time Hidden Test evaluation. Original workbook remains unchanged.</p></footer></main></html>"]
    return "\n".join(parts)


def main():
    immutable = [ROOT / "artifacts/models" / name for name in ["registry.json", "residual_models.joblib", "hidden_test_evaluation.json"]]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in immutable}
    audit = collect()
    (ROOT / "artifacts/data_audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False))
    (ROOT / "docs/data_audit.md").write_text(markdown(audit))
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/data_audit.html").write_text(html_report(audit, charts(data(), audit)))
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in immutable}
    if before != after:
        raise RuntimeError("Frozen artifacts changed during audit; investigate concurrent writes.")
    print("Wrote data_audit.json, docs/data_audit.md and standalone reports/data_audit.html. Frozen artifacts unchanged.")


if __name__ == "__main__":
    main()
