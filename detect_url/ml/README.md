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

| Candidate | CV F1 | CV accuracy | Real-world probe errors |
|---|---|---|---|
| Majority baseline | 0.0000 | 50.01% | — |
| Numeric GBM | 0.9089 ± 0.0043 | 90.88% ± 0.46% | — |
| Numeric RandomForest | 0.8952 ± 0.0032 | 89.52% ± 0.29% | — |
| Char TF-IDF + LogReg | 0.9278 ± 0.0044 | 92.87% ± 0.40% | — |
| Hybrid (numeric + char) | 0.9243 ± 0.0041 | 92.53% ± 0.39% | — |
| **Final ensemble (0.75 hybrid + 0.25 char)** | — | **93.13% held-out** | **0 / 21** |

Why the ensemble: the pure char model scored highest on the training CV but
misclassifies `accounts.google.com` (a dataset labelling artifact — see below)
in isolation. Adding 75% of the hybrid model fixes that while keeping held-out
accuracy essentially unchanged.

## 4. Final held-out test results (2,286 unseen URLs)

| Metric | Value |
|---|---|
| **Accuracy** | **93.13%** |
| Precision (phishing) | 94.58% |
| Recall (phishing) | 91.51% |
| **F1** | **93.02%** |
| ROC-AUC | 98.35% |
| Average precision | 98.57% |
| False-positive rate | 5.25% |
| False-negative rate | 8.49% |

Confusion matrix `[[TN, FP], [FN, TP]]` = `[[1083, 60], [97, 1046]]`

- 60 legitimate sites wrongly flagged (5.25%)
- 97 phishing sites missed (8.49%)

These are the **real** numbers, reproduced under the pinned scikit-learn 1.7.2
environment. The old website's "96.8% accuracy" was hardcoded demo text and has
been removed from the meta description.

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
   for parity, speed and interpretability. No neural network runs inference.
6. **Model size.** The artifact includes a ~118k-term char vocabulary (~several MB).

## 8. Files

| File | Purpose |
|---|---|
| `features.py` | URL feature extractor (shared train/inference) |
| `train.py` | Full training, CV, evaluation, artifact + metrics export |
| `inference.py` | Production prediction + model card |
| `probe.py` | 21 real-world URL sanity checks |
| `verify.py` | Re-measures the saved artifact against the held-out split |
| `artifacts/phishing_model.joblib` | Trained ensemble |
| `artifacts/metrics.json` | Measured metrics and CV results |
