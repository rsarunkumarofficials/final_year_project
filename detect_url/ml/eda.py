"""Exploratory analysis of the phishing dataset.

Run: python detect_url/ml/eda.py
"""
import os
from urllib.parse import urlparse

import pandas as pd

HERE = os.path.dirname(__file__)
CSV = os.path.abspath(os.path.join(HERE, "..", "..", "dataset", "dataset_phishing.csv"))


def main():
    df = pd.read_csv(CSV)
    print("shape:", df.shape)
    print("columns:", len(df.columns))
    print("\nlabel distribution:")
    print(df["status"].value_counts(dropna=False))
    print("\nmissing values (non-zero):")
    print(df.isna().sum()[df.isna().sum() > 0].to_string() or "  none")
    print("\ndtypes summary:")
    print(df.dtypes.value_counts().to_string())

    print("\nduplicate full rows:", int(df.duplicated().sum()))
    print("duplicate URLs:", int(df["url"].duplicated().sum()))

    # A URL that appears with two different labels is a hard leakage / noise case.
    g = df.groupby("url")["status"].nunique()
    print("URLs with conflicting labels:", int((g > 1).sum()))

    # Constant / near-constant features carry no signal.
    numeric = df.select_dtypes(include="number")
    nunique = numeric.nunique()
    print("\nconstant numeric features:", list(nunique[nunique <= 1].index))
    print("near-constant (>99% one value):")
    for c in numeric.columns:
        vc = numeric[c].value_counts(normalize=True, dropna=False)
        if len(vc) and vc.iloc[0] > 0.99:
            print(f"  {c}: {vc.index[0]} ({vc.iloc[0]*100:.2f}%)")

    # Train/serve parity: can URL-derived columns be reproduced from the URL string?
    print("\n--- URL parity checks (recomputed vs dataset column) ---")
    checks = {
        "length_url": lambda u: len(u),
        "length_hostname": lambda u: len(urlparse(u).hostname or ""),
        "nb_dots": lambda u: u.count("."),
        "nb_hyphens": lambda u: u.count("-"),
        "nb_at": lambda u: u.count("@"),
        "nb_qm": lambda u: u.count("?"),
        "nb_and": lambda u: u.count("&"),
        "nb_slash": lambda u: u.count("/"),
        "nb_www": lambda u: u.count("www"),
        "nb_com": lambda u: u.count("com"),
    }
    for col, fn in checks.items():
        try:
            calc = df["url"].astype(str).map(fn)
            match = (calc == df[col]).mean()
            print(f"  {col:20s} exact match: {match*100:6.2f}%")
        except Exception as exc:
            print(f"  {col:20s} ERROR {exc}")


if __name__ == "__main__":
    main()
