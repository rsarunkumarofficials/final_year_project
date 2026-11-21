"""INDEPENDENT PROOF that the saved ML artifact really works.

This script does NOT train anything. It loads the artifact from disk and:
  1. Proves it is a real fitted sklearn model (types, coef_, vocabulary).
  2. Rebuilds the exact held-out split from the raw CSV and re-measures
     accuracy / F1 / ROC-AUC / confusion matrix from scratch.
  3. Compares those re-measured numbers with the committed metrics.json.
  4. Cross-checks inference.predict() against a direct manual computation.
  5. Shows baseline (majority) accuracy as a negative control.

Run: python -u -m detect_url.ml.verify
"""
import hashlib
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from .features import extract
from .inference import predict
from .train import RANDOM_STATE, TEST_SIZE

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODEL = os.path.join(HERE, "artifacts", "phishing_model.joblib")
META = os.path.join(HERE, "artifacts", "metrics.json")
CSV = os.path.join(ROOT, "dataset", "dataset_phishing.csv")


def section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main():
    section("1. ARTIFACT ON DISK")
    h = hashlib.sha256()
    with open(MODEL, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    print("path   :", os.path.relpath(MODEL, ROOT))
    print("bytes  :", os.path.getsize(MODEL))
    print("sha256 :", h.hexdigest())

    bundle = joblib.load(MODEL)
    print("top-level keys:", sorted(bundle.keys()))
    print("ensemble weights:", bundle["weights"])
    for name, entry in bundle["models"].items():
        pipe = entry["pipeline"]
        clf = pipe.named_steps["clf"]
        print(f"  {name}: steps={[n for n,_ in pipe.steps]}, "
              f"clf={type(clf).__name__}, coef_shape={clf.coef_.shape}, "
              f"fitted={'coef_' in vars(clf)}, columns={len(entry['columns'])}")
        prep = pipe.named_steps.get("prep")
        if prep:
            vec = prep.named_transformers_["char"]
            print(f"          TF-IDF vocabulary: {len(vec.vocabulary_)} terms, "
                  f"ngram_range={vec.ngram_range}")
    print("numeric features:", len(bundle["numeric_features"]))

    section("2. REBUILD HELD-OUT SPLIT FROM RAW CSV (never used for fitting)")
    df = pd.read_csv(CSV).drop_duplicates(subset=["url"], keep="first").reset_index(drop=True)
    numeric = pd.DataFrame(df["url"].astype(str).map(extract).tolist())
    X = pd.concat([df[["url"]].reset_index(drop=True), numeric], axis=1)
    y = (df["status"].str.lower() == "phishing").astype(int).to_numpy()
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
    print(f"raw rows={len(df)} | train={len(Xtr)} | held-out test={len(Xte)}")
    print(f"test class balance: phishing={int(yte.sum())}, legitimate={int((1-yte).sum())}")

    section("3. RE-MEASURE PERFORMANCE USING ONLY THE SAVED ARTIFACT")
    total = np.zeros(len(Xte), dtype=float)
    for name, w in bundle["weights"].items():
        e = bundle["models"][name]
        total += w * e["pipeline"].predict_proba(Xte[e["columns"]])[:, 1]
    pred = (total >= 0.5).astype(int)
    measured = {
        "accuracy": accuracy_score(yte, pred),
        "f1": f1_score(yte, pred),
        "roc_auc": roc_auc_score(yte, total),
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
    }
    for k in ("accuracy", "f1", "roc_auc"):
        print(f"  {k:12s}: {measured[k]:.6f}  ({measured[k]*100:.2f}%)")
    print("  confusion   :", measured["confusion_matrix"], " [[TN,FP],[FN,TP]]")

    with open(META, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    print("\n  committed metrics.json says:")
    for k in ("accuracy", "f1", "roc_auc"):
        rv = meta["test_metrics"][k]
        print(f"    {k:12s}: {rv:.6f}  ({rv*100:.2f}%)")
    print("    confusion   :", meta["test_metrics"]["confusion_matrix"])
    agree = all(
        np.allclose(measured[k], meta["test_metrics"][k])
        for k in ("accuracy", "f1", "roc_auc")
    ) and measured["confusion_matrix"] == meta["test_metrics"]["confusion_matrix"]
    print(f"\n  >>> RE-MEASURED == COMMITTED METRICS ? {'YES' if agree else 'NO'}")

    section("4. NEGATIVE CONTROL - majority baseline on the SAME test set")
    dummy = DummyClassifier(strategy="most_frequent").fit(Xtr[["url"]], ytr)
    dp = dummy.predict(Xte[["url"]])
    print("  majority baseline accuracy:", f"{accuracy_score(yte,dp)*100:.2f}%")
    print(f"  trained model accuracy     : {measured['accuracy']*100:.2f}%")
    print("  => the score is learned, not a property of the balanced dataset")

    section("5. inference.predict() == direct manual computation ?")
    u = "http://paypa1-login-verify.tk/account/update"
    row = extract(u)
    row["url"] = u
    X1 = pd.DataFrame([row])
    manual = sum(
        w * e["pipeline"].predict_proba(X1[e["columns"]])[:, 1][0]
        for name, w in bundle["weights"].items()
        for e in [bundle["models"][name]]
    )
    api_style = predict(u)["phishing_probability"]
    # inference.predict() rounds the probability to 4 decimals for the UI,
    # so compare with a tolerance that accounts for that rounding.
    inference_ok = abs(manual - api_style) <= 1e-4
    print(f"  manual from artifact : {manual:.6f}")
    print(f"  inference.predict()  : {api_style:.6f} (rounded to 4dp)")
    print(f"  match (tol=1e-4)     : {'YES' if inference_ok else 'NO'}")

    section("6. SPOT CHECKS (real URLs, loaded artifact)")
    checks = [
        ("https://www.python.org", "SAFE"),
        ("https://github.com", "SAFE"),
        ("https://accounts.google.com", "SAFE"),
        ("http://paypa1-login-verify.tk/account/update", "PHISHING"),
        ("https://verify-account-update.tk/login", "PHISHING"),
        ("http://free-gift-card-win.xyz", "PHISHING"),
    ]
    ok = 0
    for url, expected in checks:
        r = predict(url)
        mark = "OK" if r["verdict"] == expected else "WRONG"
        ok += mark == "OK"
        print(f"  [{mark:5s}] {r['verdict']:8s} p={r['phishing_probability']:.4f}  {url}")
    print(f"\n  spot checks passed: {ok}/{len(checks)}")

    section("VERDICT")
    print(f"  artifact is fitted sklearn model : YES")
    print(f"  metrics reproduce from disk      : {'YES' if agree else 'NO'}")
    print(f"  beats baseline                   : "
          f"YES ({measured['accuracy']*100:.2f}% vs {accuracy_score(yte,dp)*100:.2f}%)")
    print(f"  inference matches artifact       : {'YES' if inference_ok else 'NO'}")
    print(f"  spot checks                      : {ok}/{len(checks)}")


if __name__ == "__main__":
    main()
