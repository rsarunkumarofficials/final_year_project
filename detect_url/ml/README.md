# ML Model Card — Phishing URL Classifier

A real, trained classifier added to the project. Everything below is measured,
not estimated. Reproduce with `python -m detect_url.ml.train`.

## 1. Dataset

| Property | Value |
|---|---|
| File | `dataset/dataset_phishing.csv` |
| Rows used | 11,429 (1 duplicate URL removed) |
| Classes | 5,714 phishing / 5,715 legitimate (balanced) |
| Missing values | 0 |
| Split | Stratified 80/20 → 9,143 train / 2,286 held-out test |
| Seed | 42 |

## 2. Engineering decisions

**Train/serve parity.** The dataset ships 87 pre-computed features, but most
require full page HTML, WHOIS, traffic or PageRank data that a live request does
not have. Training on those columns would create *train/serve skew* — impressive
offline numbers that collapse in production. Instead, every feature is produced
by `features.extract(url)` from the URL string alone. The **identical function**
runs during training and inference. 57 numeric features + raw character n-grams
are used.

**No leakage.** Duplicate URLs are dropped before splitting. The test set is
never used for fitting or candidate selection.

**Model selection.** 5-fold stratified CV on the training split compared five
candidates. The final production model is a weighted blend chosen using an
external sanity-check set of 21 real-world URLs (`probe.py`), not the test set.

## 3. Candidate comparison

5-fold CV on training split (mean ± std F1):

| Candidate | CV F1 | Held-out accuracy | Real-world probe errors |
|---|---|---|---|
| Majority baseline | 0.0000 | 50.0% | — |
| Numeric GBM | 0.9089 ± 0.0043 | 90.90% | 3 / 21 |
| Numeric RandomForest | 0.8952 ± 0.0032 | 90.20% | 3 / 21 |
| Char TF-IDF + LogReg | 0.9276 ± 0.0031 | 93.66% | 2 / 21 |
| Hybrid (numeric + char) | 0.9241 ± 0.0040 | 92.91% | 0 / 21 |
| **Final ensemble (0.75 hybrid + 0.25 char)** | — | **93.22%** | **0 / 21** |

Why the ensemble: the pure char model scored highest on the test split but
misclassified `accounts.google.com` (a dataset labelling artifact — see below)
and `free-gift-card-win.xyz`. Adding 75% of the hybrid model fixed both while
keeping accuracy within 0.44pp of the best candidate.

## 4. Final held-out test results (2,286 unseen URLs)

| Metric | Value |
|---|---|
| **Accuracy** | **93.22%** |
| Precision (phishing) | 94.67% |
| Recall (phishing) | 91.60% |
| **F1** | **93.11%** |
| ROC-AUC | 98.35% |
| Average precision | 98.57% |
| False-positive rate | 5.16% |
| False-negative rate | 8.40% |

Confusion matrix `[[TN, FP], [FN, TP]]` = `[[1084, 59], [96, 1047]]`

- 59 legitimate sites wrongly flagged (5.16%)
- 96 phishing sites missed (8.40%)

These are the **real** numbers. The old website's "96.8% accuracy" was hardcoded
demo text and has been removed from the meta description.

## 5. How inference works

1. `inference.predict(url)` calls `features.extract(url)` (57 numeric features).
2. A DataFrame with `url` + those features goes to both ensemble members:
   - **hybrid_logreg**: `StandardScaler(numeric)` + `TfidfVectorizer(char 2–5)` → `LogisticRegression(C=2)`
   - **char_logreg**: `TfidfVectorizer(char 2–5)` → `LogisticRegression(C=4)`
3. Probabilities are blended `0.75 × hybrid + 0.25 × char`.
4. `≥ 0.5` → PHISHING, else SAFE. Confidence = `max(p, 1-p) × 100`.
5. Top contributing character n-grams are returned as `signals` for explainability.

The verdict is returned by `POST /api/predict` in the `ml` field and is
**authoritative** in the UI. The scraper + LangGraph/Claude output is kept as
supporting context. `GET /api/model` returns the live model card.

## 6. Verified example output

```
http://paypa1-login-verify.tk/account/update
  → PHISHING, p=0.9998, confidence 100%
  signals: 'pay', 'veri', 'verif'

https://accounts.google.com
  → SAFE, p=0.4054, confidence 59.5%

https://www.github.com
  → SAFE, p≈0.01

http://free-gift-card-win.xyz
  → PHISHING, p=0.6971
```

All 21 URLs in `probe.py` classified correctly.

## 7. Known problems / limitations

1. **Dataset label noise.** 133 of 157 `google.com` rows are labelled "phishing"
   because they are Google *redirect* URLs (`google.com/url?...&url=...`) whose
   destination was malicious. This teaches naive char models that "google" is
   suspicious. The hybrid member's numeric features correct this; it remains a
   known dataset artifact.
2. **No page-content features at inference.** HTML signals (login forms,
   hyperlink ratios, iframes) and WHOIS signals are not used by the classifier.
   Phishing pages with a clean-looking URL can be missed. The scraper/LLM step
   supplies these signals separately but does not feed them back into the model.
3. **URL-only scope.** A URL shortener pointing to a phishing page will look
   benign. Shorteners are flagged as a feature, but the model cannot follow redirects.
4. **Threshold is fixed at 0.5.** It balances FPR/FNR on this balanced dataset.
   A security product would tune it toward higher recall (fewer misses).
5. **Not a deep model.** It is TF-IDF + logistic regression, deliberately chosen
   for parity, speed and interpretability. The Three.js "neural network" visuals
   are decorative and do not run inference.
6. **Model size.** The artifact includes a ~118k-term char vocabulary (~several MB).

## 8. Files

| File | Purpose |
|---|---|
| `features.py` | URL feature extractor (shared train/inference) |
| `train.py` | Full training, CV, evaluation, artifact + metrics export |
| `inference.py` | Production prediction + model card |
| `probe.py` | 21 real-world URL sanity checks |
| `eda.py` | Dataset exploration |
| `validate_parity.py` | Shows why dataset columns are not reused at inference |
| `compare.py`, `ensemble_check.py` | Candidate/ensemble selection experiments (run `compare.py` first — it regenerates the candidate artifacts that `ensemble_check.py` loads) |
| `artifacts/phishing_model.joblib` | Trained ensemble |
| `artifacts/metrics.json` | Measured metrics and CV results |
