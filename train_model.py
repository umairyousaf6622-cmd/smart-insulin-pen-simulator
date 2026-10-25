"""
Phase 2 - Train a classifier to detect faulty injections.

Pipeline:
    raw time series (force, velocity)  ->  engineered features per injection
    ->  Random Forest classifier  ->  accuracy report

Two views of the same model are reported:
    1. Multi-class : normal / fast_injection / premature_release
    2. Binary      : successful vs faulty (what a patient-facing app would show)

Run `python simulate_injections.py` first to create the dataset.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from simulate_injections import DT, SCENARIOS, generate_trial

ROOT = Path(__file__).resolve().parent
PRESS_THRESHOLD_N = 1.0        # force above this = thumb is pressing
MOVING_THRESHOLD_MM_S = 0.10   # velocity above this = plunger is moving

FEATURE_COLUMNS = [
    "peak_force_N",
    "mean_force_N",
    "force_std_N",
    "peak_to_mean_force",
    "max_force_rise_rate_N_s",
    "time_to_peak_force_s",
    "press_duration_s",
    "peak_velocity_mm_s",
    "mean_velocity_moving_mm_s",
    "motion_duration_s",
    "total_displacement_mm",
    "hold_after_motion_s",
]


# --------------------------------------------------------------------------
# Feature engineering
# --------------------------------------------------------------------------
def _smooth(x: np.ndarray, width: int = 5) -> np.ndarray:
    return np.convolve(x, np.ones(width) / width, mode="same")


def extract_features(force: np.ndarray, velocity: np.ndarray, dt: float = DT) -> dict:
    """Turn one injection's raw signals into a fixed-length feature vector."""
    f, v = _smooth(force), _smooth(velocity)
    pressing = f > PRESS_THRESHOLD_N
    moving = v > MOVING_THRESHOLD_MM_S

    feats = dict.fromkeys(FEATURE_COLUMNS, 0.0)
    feats["total_displacement_mm"] = float(np.sum(velocity) * dt)   # firmware-style integral
    feats["peak_force_N"] = float(f.max())
    feats["peak_velocity_mm_s"] = float(v.max())
    feats["max_force_rise_rate_N_s"] = float(np.max(np.diff(f)) / dt)

    if pressing.any():
        idx = np.flatnonzero(pressing)
        start, end = idx[0], idx[-1]
        feats["mean_force_N"] = float(f[pressing].mean())
        feats["force_std_N"] = float(f[pressing].std())
        feats["peak_to_mean_force"] = feats["peak_force_N"] / feats["mean_force_N"]
        feats["time_to_peak_force_s"] = float((np.argmax(f) - start) * dt)
        feats["press_duration_s"] = float((end - start + 1) * dt)

        if moving.any():
            last_motion = np.flatnonzero(moving)[-1]
            feats["hold_after_motion_s"] = float(max(end - last_motion, 0) * dt)

    if moving.any():
        feats["mean_velocity_moving_mm_s"] = float(v[moving].mean())
        feats["motion_duration_s"] = float(moving.sum() * dt)

    return feats


def build_feature_table(csv_path: Path) -> pd.DataFrame:
    """One row of features per injection trial."""
    df = pd.read_csv(csv_path)
    rows = []
    for trial_id, g in df.groupby("trial_id", sort=True):
        feats = extract_features(g["force_N"].to_numpy(), g["velocity_mm_s"].to_numpy())
        feats["trial_id"] = trial_id
        feats["scenario"] = g["scenario"].iloc[0]
        rows.append(feats)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Inference helper (what the pen's companion app would call)
# --------------------------------------------------------------------------
def predict_injection(model, force: np.ndarray, velocity: np.ndarray) -> dict:
    X = pd.DataFrame([extract_features(force, velocity)])[FEATURE_COLUMNS]
    proba = model.predict_proba(X)[0]
    label = model.classes_[int(np.argmax(proba))]
    return {
        "predicted_class": label,
        "status": "SUCCESS" if label == "normal" else "FAULTY",
        "confidence": float(proba.max()),
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    csv_path = ROOT / "data" / "injection_dataset.csv"
    if not csv_path.exists():
        raise SystemExit("Dataset not found. Run `python simulate_injections.py` first.")

    features = build_feature_table(csv_path)
    X, y = features[FEATURE_COLUMNS], features["scenario"]
    print(f"Feature table: {X.shape[0]} injections x {X.shape[1]} features")
    print(y.value_counts().to_string(), "\n")

    # Hold out 25 % of injections the model never sees during training
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=42
    )

    # ---- Compare a simple baseline against the Random Forest (5-fold CV) ----
    models = {
        "Logistic Regression (baseline)": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000)
        ),
        "Random Forest": RandomForestClassifier(n_estimators=300, random_state=42),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    print("5-fold cross-validation on training set:")
    for name, mdl in models.items():
        scores = cross_val_score(mdl, X_train, y_train, cv=cv)
        print(f"  {name:32s} accuracy = {scores.mean():.3f} +/- {scores.std():.3f}")

    # ---- Final model ----
    model = models["Random Forest"].fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("\n" + "=" * 62)
    print("HOLD-OUT TEST RESULTS - 3-class fault detection")
    print("=" * 62)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}\n")
    print(classification_report(y_test, y_pred, digits=3))

    # Binary view: successful vs faulty
    y_test_bin = np.where(y_test == "normal", "successful", "faulty")
    y_pred_bin = np.where(y_pred == "normal", "successful", "faulty")
    print("=" * 62)
    print("HOLD-OUT TEST RESULTS - binary (successful vs faulty)")
    print("=" * 62)
    print(f"Accuracy: {accuracy_score(y_test_bin, y_pred_bin):.3f}\n")
    print(classification_report(y_test_bin, y_pred_bin, digits=3))

    # ---- Figures ----
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred, labels=list(SCENARIOS), cmap="Blues", ax=ax, xticks_rotation=20
    )
    ax.set_title("Confusion matrix (hold-out test set)")
    fig.tight_layout()
    fig.savefig(fig_dir / "confusion_matrix.png", dpi=150)
    plt.close(fig)

    importances = pd.Series(model.feature_importances_, index=FEATURE_COLUMNS).sort_values()
    fig, ax = plt.subplots(figsize=(7, 5))
    importances.plot.barh(ax=ax, color="steelblue")
    ax.set_title("Random Forest feature importance")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(fig_dir / "feature_importance.png", dpi=150)
    plt.close(fig)

    print("Top 5 features:")
    print(importances.sort_values(ascending=False).head(5).round(3).to_string(), "\n")

    # ---- Save the trained model ----
    (ROOT / "models").mkdir(exist_ok=True)
    joblib.dump(model, ROOT / "models" / "injection_classifier.joblib")

    # ---- Demo: classify brand-new injections the model has never seen ----
    print("=" * 62)
    print("DEMO: new, unseen injections")
    print("=" * 62)
    rng = np.random.default_rng(2026)
    for scenario in SCENARIOS:
        sig, _ = generate_trial(scenario, rng)
        res = predict_injection(model, sig["force_N"].to_numpy(), sig["velocity_mm_s"].to_numpy())
        print(
            f"true: {scenario:18s} -> predicted: {res['predicted_class']:18s} "
            f"[{res['status']}] (confidence {res['confidence']:.0%})"
        )


if __name__ == "__main__":
    main()
