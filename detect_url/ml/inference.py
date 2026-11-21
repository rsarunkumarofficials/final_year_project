"""Production inference wrapper for the trained ensemble classifier.

The exact same features.extract() used during training runs here, giving
zero train/serve skew.
"""
import json
import os
import threading
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from .features import extract

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ARTIFACT_DIR = os.path.join(HERE, "artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "phishing_model.joblib")
METRICS_PATH = os.path.join(ARTIFACT_DIR, "metrics.json")

_lock = threading.Lock()
_cache = {}


def load_model():
    with _lock:
        if "bundle" not in _cache:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(
                    f"Model artifact not found at {MODEL_PATH}. "
                    "Run: python -m detect_url.ml.train"
                )
            # sklearn pickles are version-sensitive: loading a 1.2.2 artifact
            # under 1.7.2 silently changes probabilities (verified: 93.22% ->
            # 89.85% accuracy). Fail loudly with a clear remedy instead.
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                try:
                    bundle = joblib.load(MODEL_PATH)
                except InconsistentVersionWarning as exc:
                    raise RuntimeError(
                        "The saved model was trained with a different "
                        "scikit-learn version than the one installed "
                        f"({sklearn.__version__}). Re-train with "
                        "'python -m detect_url.ml.train' using the pinned "
                        "requirements.txt, or install the matching version."
                    ) from exc
            trained_with = bundle.get("sklearn_version")
            if trained_with and trained_with != sklearn.__version__:
                raise RuntimeError(
                    f"Model artifact was saved with scikit-learn {trained_with}, "
                    f"but {sklearn.__version__} is installed. Re-train with "
                    "'python -m detect_url.ml.train' using the pinned "
                    "requirements.txt."
                )
            _cache["bundle"] = bundle
        return _cache["bundle"]


def load_metrics():
    with _lock:
        if "metrics" not in _cache:
            with open(METRICS_PATH, "r", encoding="utf-8") as fh:
                _cache["metrics"] = json.load(fh)
        return _cache["metrics"]


def _blended_probability(bundle, X):
    total = np.zeros(len(X), dtype=float)
    for name, weight in bundle["weights"].items():
        entry = bundle["models"][name]
        total += weight * entry["pipeline"].predict_proba(X[entry["columns"]])[:, 1]
    return float(total[0])


def _top_signals(bundle, url, limit=3):
    """Highest-impact character n-grams from the hybrid member of the ensemble."""
    entry = bundle["models"].get("hybrid_logreg")
    if not entry:
        return []
    try:
        pipe = entry["pipeline"]
        prep = pipe.named_steps.get("prep")
        clf = pipe.named_steps.get("clf")
        vec = prep.named_transformers_.get("char")
        x = vec.transform([url])
        # The classifier sees [numeric features | char n-grams]; slice off the
        # numeric block so the coefficient vector aligns with the vectorizer.
        n_numeric = len(bundle["numeric_features"])
        coef = clf.coef_[0][n_numeric:]
        contrib = x.multiply(coef).tocsr()
        pairs = []
        for idx in contrib.indices:
            term = vec.get_feature_names_out()[idx]
            if term.strip():
                pairs.append((term, float(contrib[0, idx])))
        pairs.sort(key=lambda p: p[1])
        risky = [f"'{t}' (+{v:.2f})" for t, v in reversed(pairs) if v > 0][:limit]
        safe = [f"'{t}' ({v:.2f})" for t, v in pairs if v < 0][:limit]
        return risky + safe
    except Exception:
        return []


def predict(url: str, threshold: float = 0.5) -> dict:
    """Classify one URL. Returns a JSON-serialisable dict."""
    bundle = load_model()
    row = extract(url)
    row["url"] = url
    X = pd.DataFrame([row])
    proba = _blended_probability(bundle, X)
    is_phishing = proba >= threshold
    return {
        "verdict": "PHISHING" if is_phishing else "SAFE",
        "is_phishing": bool(is_phishing),
        "phishing_probability": round(proba, 4),
        "confidence": round(max(proba, 1 - proba) * 100, 1),
        "threshold": threshold,
        "signals": _top_signals(bundle, url),
        "features_used": len(bundle["numeric_features"]) + 1,
        "ensemble_weights": bundle["weights"],
    }


def model_info() -> dict:
    m = load_metrics()
    t = m["test_metrics"]
    return {
        "model": m["final_model"],
        "weights": m["final_weights"],
        "trained_at": m["created_at"],
        "training_rows": m["rows"],
        "test_rows": m["test_size"],
        "accuracy": round(t["accuracy"] * 100, 2),
        "precision": round(t["precision"] * 100, 2),
        "recall": round(t["recall"] * 100, 2),
        "f1": round(t["f1"] * 100, 2),
        "roc_auc": round(t["roc_auc"] * 100, 2),
        "false_positive_rate": round(t["fpr"] * 100, 2),
        "false_negative_rate": round(t["fnr"] * 100, 2),
        "confusion_matrix": t["confusion_matrix"],
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(model_info(), indent=2))
    for u in (sys.argv[1:] or [
        "http://paypa1-login-verify.tk/account/update?redirect=%2F",
        "https://accounts.google.com",
        "https://www.github.com",
    ]):
        print("\n", u)
        print(json.dumps(predict(u), indent=2))
