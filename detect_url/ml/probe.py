"""Quick behavioural probe of the trained model on known URLs."""
from .inference import predict

URLS = [
    # well-known legitimate
    "https://accounts.google.com", "https://www.google.com", "https://github.com",
    "https://www.microsoft.com", "https://support.microsoft.com", "https://www.python.org",
    "https://en.wikipedia.org", "https://stackoverflow.com", "https://www.amazon.com",
    "https://www.apple.com", "https://www.mozilla.org", "https://www.paypal.com",
    "https://openai.com", "https://www.bbc.com", "https://www.wikipedia.org",
    # obvious phishing
    "http://paypa1-login-verify.tk/account/update", "http://secure-banking-login.php",
    "https://verify-account-update.tk/login", "http://192.168.1.1/login",
    "http://free-gift-card-win.xyz", "https://login-appleid.support-center.tk/verify",
]

if __name__ == "__main__":
    print(f"{'verdict':9s} {'prob':>7s}  url")
    print("-" * 90)
    for u in URLS:
        r = predict(u)
        print(f"{r['verdict']:9s} {r['phishing_probability']:7.4f}  {u}")
