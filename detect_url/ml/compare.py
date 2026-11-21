"""Compare candidate models on held-out test AND real-world probe URLs."""
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from .features import extract
from .probe import URLS
from .train import RANDOM_STATE, TEST_SIZE, build_candidates, load_data

X, y, numeric_cols = load_data()
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)

probe_rows = pd.DataFrame([{**extract(u), "url": u} for u in URLS])
expected = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]

print(f"{'model':18s} {'acc':>7s} {'f1':>7s} {'auc':>7s} {'probe_err':>10s}  errors")
print("-" * 95)
for name, (pipe, cols) in build_candidates(numeric_cols).items():
    if name == "baseline_majority":
        continue
    pipe.fit(Xtr[cols], ytr)
    p = pipe.predict_proba(Xte[cols])[:, 1]
    pred = (p >= 0.5).astype(int)
    pp = pipe.predict_proba(probe_rows[cols])[:, 1]
    ppred = (pp >= 0.5).astype(int)
    errs = [URLS[i] for i in range(len(URLS)) if ppred[i] != expected[i]]
    print(f"{name:18s} {accuracy_score(yte,pred):7.4f} {f1_score(yte,pred):7.4f} "
          f"{roc_auc_score(yte,p):7.4f} {len(errs):10d}  {errs}")
    joblib.dump((pipe, cols), f"detect_url/ml/artifacts/candidate_{name}.joblib")
