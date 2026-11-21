"""Check that our URL feature extractor reproduces the dataset columns.

This is the critical train/serve parity check. Any feature with poor agreement
must not be used by the production model.
"""
import os

import pandas as pd

from .features import FEATURE_NAMES, extract

HERE = os.path.dirname(__file__)
CSV = os.path.abspath(os.path.join(HERE, "..", "..", "dataset", "dataset_phishing.csv"))


def main():
    df = pd.read_csv(CSV)
    rows = df["url"].astype(str).map(extract).tolist()
    calc = pd.DataFrame(rows)

    shared = [c for c in FEATURE_NAMES if c in df.columns and c != "label"]
    print(f"Comparing {len(shared)} shared features on {len(df)} URLs\n")
    results = []
    for c in shared:
        a = pd.to_numeric(df[c], errors="coerce")
        b = pd.to_numeric(calc[c], errors="coerce")
        valid = a.notna() & b.notna()
        exact = ((a[valid] == b[valid]).mean() * 100)
        corr = a[valid].corr(b[valid])
        results.append((c, exact, corr))

    results.sort(key=lambda x: x[1])
    print(f"{'feature':28s} {'exact%':>8s} {'corr':>8s}")
    print("-" * 48)
    for c, exact, corr in results:
        flag = "  <-- LOW" if exact < 90 else ""
        cv = "n/a" if corr != corr else f"{corr:.3f}"
        print(f"{c:28s} {exact:8.2f} {cv:>8s}{flag}")

    good = [c for c, e, r in results if e >= 90]
    print(f"\nFeatures with >=90% exact parity: {len(good)}/{len(shared)}")
    print(good)


if __name__ == "__main__":
    main()
