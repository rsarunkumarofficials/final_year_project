# Product — URL CHECKER

## What it is

A single-purpose React web application. Give it one URL; it returns a measured
verdict — safe or phishing — with the model's probability, confidence, decision
threshold, the address facts it can observe, and the signals that moved the
score. No account, no login, and no page fetch is required for the verdict
itself.

The product name is **URL CHECKER** across the page title, navigation and
header. The logo is a black rounded square with a white `//`. The classifier
and API are unchanged.

## Who it is for

- Students and researchers checking a suspicious link before opening it.
- Developers who want a small, auditable, URL-only classifier they can inspect.
- Reviewers who need to see *how* a verdict was reached, not just a score.

## The honest facts

Source of truth: `detect_url/ml/artifacts/metrics.json` and `GET /api/model`.

- Model: **weighted ensemble** — `0.75 × hybrid_logreg + 0.25 × char_logreg`.
- **Not deep learning.** No TensorFlow, no Keras, no neural network.
- Inputs: **57 numeric URL features** from `ml/features.extract(url)` plus
  character n-grams. HTML, WHOIS and traffic columns are deliberately unused.
  Live prediction may report `features_used: 58`; the report renders the
  response value when present.
- Data: **11,429** unique URLs → **9,143 train / 2,286 held-out test**.
- Held-out: accuracy **93.13%**, precision **94.58%**, recall **91.51%**,
  F1 **93.02%**, ROC-AUC **98.35%**, average precision **98.57%**.
- Confusion matrix `[[1083, 60], [97, 1046]]` → FPR **5.25%**, FNR **8.49%**.
- Majority-class baseline: **50.00%**.
- Verification: `verify.py` reproduces metrics from disk and matches inference
  within `1e-4`; `probe.py` passed 21/21 real-world URL checks.

## Interface scope

- Hero: headline and two actions only — no badge, explanatory paragraph or stats.
- Method: three one-word steps — Paste, Scan, Verify.
- Checker: only the URL field, Check button and three sample links.
- Report: verdict, probability, confidence, threshold, risk bar, address
  structure, domain features, heuristics, character signals, collapsible
  supporting context and provenance.
- No section number indicators anywhere.
- No Known Limitations section in the UI.
- Footer credit: **Developer RS ARUNKUMAR**. No tech-stack badges.

The ML verdict is authoritative. Scraper / language-model text is supporting
context and is labelled as not authoritative in the report.

Address facts shown in the report are computed from the submitted URL; the UI
explicitly notes that certificate validity and live redirects are not verified.

## Product principles

1. The measured number wins. Never show a nicer number than the artifact produces.
2. The ML verdict is authoritative; scraped / LLM text is supporting context.
3. Show the method. Every number on the site maps to `metrics.json` or the model card.
4. Fast and quiet. One URL in, one answer out. No dark patterns.
5. The backend is frozen for this redesign. Only frontend structure, styling,
   motion, branding and content change.

## Done criteria

- `npm run build` succeeds and stale hashed assets are removed.
- Zero horizontal overflow at 1440 / 1024 / 820 / 768 / 390 / 320; zero console errors.
- Live scan returns the authoritative ML verdict; both sample classes render fully.
- Backend files and `/api/predict` request contract are untouched.
- No commit or push is made as part of this redesign.
