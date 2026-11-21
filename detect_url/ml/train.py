"""Train the production phishing URL classifier from scratch.

Design decisions (deliberate, to avoid the common mistakes):
  * All features come from ml/features.extract(url). The IDENTICAL function runs
    at training and at inference -> zero train/serve skew. Dataset-specific
    columns (HTML/WHOIS/traffic) are intentionally NOT used: they cannot be
    recomputed for a live URL and would silently break in production.
  * Stratified 80/20 split with fixed seed; the test set is never used for
    fitting or model selection.
  * 5-fold stratified CV on the training split compares candidate models.
  * Final production model is a weighted blend of the two strongest pipelines.
    The blend weights were chosen using external real-world sanity checks
    (ml/probe.py), not the held-out test set. All numbers are reported below.

Run: python -m detect_url.ml.train
"""
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import extract

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CSV = os.path.join(ROOT, "dataset", "dataset_phishing.csv")
ARTIFACT_DIR = os.path.join(HERE, "artifacts")

RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5

# Production blend: numeric + char (75%) smoothed by pure char n-grams (25%).
FINAL_WEIGHTS = {"hybrid_logreg": 0.75, "char_logreg": 0.25}


def load_data():
    df = pd.read_csv(CSV)
    if df["url"].isna().any() or df["status"].isna().any():
        raise ValueError("Dataset has missing url/status values")
    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first").reset_index(drop=True)
    print(f"Dropped {before - len(df)} duplicate URL row(s) to avoid split leakage.")

    numeric = pd.DataFrame(df["url"].astype(str).map(extract).tolist())
    X = pd.concat([df[["url"]].reset_index(drop=True), numeric], axis=1)
    y = (df["status"].str.lower() == "phishing").astype(int).to_numpy()
    return X, y, numeric.columns.tolist()


def build_candidates(numeric_cols):
    text_col = ("char", TfidfVectorizer(
        analyzer="char", ngram_range=(2, 5), min_df=2,
        sublinear_tf=True, lowercase=True, dtype=np.float32,
    ), "url")
    num_col = ("num", StandardScaler(), numeric_cols)

    return {
        "baseline_majority": (
            Pipeline([("clf", DummyClassifier(strategy="most_frequent"))]),
            ["url"] + numeric_cols,
        ),
        "numeric_gbm": (
            Pipeline([
                ("num", StandardScaler()),
                ("clf", HistGradientBoostingClassifier(
                    max_iter=250, learning_rate=0.08, max_leaf_nodes=31,
                    l2_regularization=1.0, random_state=RANDOM_STATE,
                )),
            ]),
            numeric_cols,
        ),
        "numeric_rf": (
            Pipeline([
                ("num", StandardScaler()),
                ("clf", RandomForestClassifier(
                    n_estimators=400, min_samples_leaf=2, n_jobs=-1,
                    random_state=RANDOM_STATE,
                )),
            ]),
            numeric_cols,
        ),
        "char_logreg": (
            Pipeline([
                ("prep", ColumnTransformer([text_col])),
                ("clf", LogisticRegression(max_iter=3000, C=4.0, n_jobs=-1)),
            ]),
            ["url"] + numeric_cols,
        ),
        "hybrid_logreg": (
            Pipeline([
                ("prep", ColumnTransformer([num_col, text_col])),
                ("clf", LogisticRegression(max_iter=3000, C=2.0, n_jobs=-1)),
            ]),
            ["url"] + numeric_cols,
        ),
    }


def blended_proba(models, X, weights):
    total = np.zeros(len(X), dtype=float)
    for name, (pipe, cols) in models.items():
        total += weights[name] * pipe.predict_proba(X[cols])[:, 1]
    return total


def main():
    print("=" * 70)
    print("PHISHING URL CLASSIFIER - TRAINING")
    print("=" * 70)
    X, y, numeric_cols = load_data()
    print(f"Rows: {len(X)} | URL-derived numeric features: {len(numeric_cols)}")
    print(f"Class balance: phishing={int(y.sum())}, legitimate={int((1-y).sum())}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    print(f"Train: {len(X_train)} | Test (held out): {len(X_test)}")

    candidates = build_candidates(numeric_cols)
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scoring = {"f1": "f1", "accuracy": "accuracy", "roc_auc": "roc_auc"}

    cv_rows = []
    print("\n5-fold CV on TRAIN split (test set untouched):")
    print(f"{'model':20s} {'F1':>16s} {'Accuracy':>16s} {'ROC-AUC':>16s}")
    print("-" * 70)
    for name, (pipe, cols) in candidates.items():
        scores = cross_validate(pipe, X_train[cols], y_train, cv=cv, scoring=scoring)
        row = {
            "model": name,
            "f1_mean": float(np.mean(scores["test_f1"])),
            "f1_std": float(np.std(scores["test_f1"])),
            "accuracy_mean": float(np.mean(scores["test_accuracy"])),
            "accuracy_std": float(np.std(scores["test_accuracy"])),
            "roc_auc_mean": float(np.mean(scores["test_roc_auc"])),
            "roc_auc_std": float(np.std(scores["test_roc_auc"])),
        }
        cv_rows.append(row)
        print(f"{name:20s} "
              f"{row['f1_mean']:.4f} +/-{row['f1_std']:.4f}  "
              f"{row['accuracy_mean']:.4f} +/-{row['accuracy_std']:.4f}  "
              f"{row['roc_auc_mean']:.4f} +/-{row['roc_auc_std']:.4f}")

    # --- Fit the final production blend ---
    final_models = {}
    for name in FINAL_WEIGHTS:
        pipe, cols = candidates[name]
        pipe.fit(X_train[cols], y_train)
        final_models[name] = (pipe, cols)

    proba = blended_proba(final_models, X_test, FINAL_WEIGHTS)
    y_pred = (proba >= 0.5).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "average_precision": float(average_precision_score(y_test, proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }
    tn, fp, fn, tp = (metrics["confusion_matrix"][0][0], metrics["confusion_matrix"][0][1],
                      metrics["confusion_matrix"][1][0], metrics["confusion_matrix"][1][1])
    metrics["fpr"] = float(fp / (fp + tn)) if (fp + tn) else 0.0
    metrics["fnr"] = float(fn / (fn + tp)) if (fn + tp) else 0.0

    print("\n" + "=" * 70)
    print("HELD-OUT TEST RESULTS - FINAL ENSEMBLE (never used for fitting)")
    print("=" * 70)
    print(f"  Blend: {FINAL_WEIGHTS}")
    for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "average_precision", "fpr", "fnr"):
        print(f"  {k:20s} {metrics[k]:.4f}")
    print(f"\n  Confusion matrix [[TN FP] [FN TP]]: {metrics['confusion_matrix']}")
    print("\n" + classification_report(y_test, y_pred, target_names=["legitimate", "phishing"]))

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    model_path = os.path.join(ARTIFACT_DIR, "phishing_model.joblib")
    joblib.dump({
        "models": {name: {"pipeline": pipe, "columns": cols} for name, (pipe, cols) in final_models.items()},
        "weights": FINAL_WEIGHTS,
        "numeric_features": numeric_cols,
    }, model_path)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": os.path.relpath(CSV, ROOT).replace("\\", "/"),
        "rows": int(len(X)),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "test_fraction": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "cv_folds": CV_FOLDS,
        "final_model": "weighted_ensemble",
        "final_weights": FINAL_WEIGHTS,
        "cv_results": cv_rows,
        "test_metrics": metrics,
        "feature_source": "ml/features.extract(url) used identically at train and inference",
        "numeric_feature_count": len(numeric_cols),
        "artifact": os.path.relpath(model_path, ROOT).replace("\\", "/"),
        "known_limitations": [
            "UCI labels contain Google redirect URLs (google.com/url?...&url=...) as phishing; "
            "these are destination-based labels, which harms naive char models on accounts.google.com.",
            "No HTML/WHOIS features are used at inference, so page-content-based phishing signals "
            "are out of scope for the model itself (the scraper/LLM still provides them separately).",
        ],
    }
    meta_path = os.path.join(ARTIFACT_DIR, "metrics.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    print(f"\nSaved model: {metadata['artifact']}")
    print(f"Saved metrics: {os.path.relpath(meta_path, ROOT)}")


if __name__ == "__main__":
    main()
