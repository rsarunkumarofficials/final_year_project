// Every number here is copied from detect_url/ml/artifacts/metrics.json.
// Do not replace these with estimates or marketing figures.
export const MODEL_FACTS = {
  model: 'weighted_ensemble',
  weights: '0.75 hybrid_logreg + 0.25 char_logreg',
  trainingRows: 11429,
  testRows: 2286,
  features: 57,
  accuracy: 93.13,
  precision: 94.58,
  recall: 91.51,
  f1: 93.02,
  rocAuc: 98.35,
};

export const QUICK_TESTS = [
  { label: 'google.com', hint: 'likely safe', url: 'https://www.google.com', tone: 'safe' },
  {
    label: 'paypa1-login.tk',
    hint: 'likely threat',
    url: 'http://paypa1-login-verify.tk/account/update?redirect=%2F',
    tone: 'phishing',
  },
  {
    label: '192.168.1.1',
    hint: 'likely threat',
    url: 'http://192.168.1.1/secure-banking-login.php',
    tone: 'phishing',
  },
];
