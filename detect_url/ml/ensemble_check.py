"""Check whether averaging the two best pipelines improves both held-out and probe results."""
import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from .features import extract
from .probe import URLS
from .train import RANDOM_STATE, TEST_SIZE, load_data

X, y, numeric_cols = load_data()
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
probe = __import__("pandas").DataFrame([{**extract(u), "url": u} for u in URLS])
expected = [0]*15 + [1]*6

models = {}
for n in ("char_logreg", "hybrid_logreg"):
    pipe, cols = joblib.load(f"detect_url/ml/artifacts/candidate_{n}.joblib")
    models[n] = (pipe, cols, pipe.predict_proba(Xte[cols])[:,1], pipe.predict_proba(probe[cols])[:,1])

for w in (0.25, 0.5, 0.75):
    p = w*models["char_logreg"][2] + (1-w)*models["hybrid_logreg"][2]
    pp = w*models["char_logreg"][3] + (1-w)*models["hybrid_logreg"][3]
    pred, ppred = (p>=0.5).astype(int), (pp>=0.5).astype(int)
    errs=[URLS[i] for i in range(len(URLS)) if ppred[i]!=expected[i]]
    print(f"w_char={w:.2f} acc={accuracy_score(yte,pred):.4f} f1={f1_score(yte,pred):.4f} "
          f"auc={roc_auc_score(yte,p):.4f} probe_err={len(errs)} {errs}")
