"""Voice of customer: keyword themes and distinguishing terms for unhappy customers. No LLM."""
from collections import Counter

from .text import tokens

THEMES = {
    "Delivery and shipping": ["package", "delivery", "tracking", "shipping", "late", "transit"],
    "Billing and money": ["charge", "charged", "billing", "refund", "money", "invoice", "receipt", "card"],
    "Access and login": ["password", "login", "locked", "code", "verification", "authentication", "reset"],
    "App reliability": ["crash", "crashes", "freezes", "error", "update", "launch"],
    "Account and plan": ["cancel", "subscription", "account", "close", "plan"],
    "Setup and how-to": ["setup", "integration", "configure", "connect", "dashboard"],
}
EMOTION = ["frustrating", "urgent", "again", "waiting", "second", "still", "never"]


def themes(tickets):
    rows = []
    for name, ws in THEMES.items():
        hit = [t for t in tickets if any(w in tokens(t["text"]) for w in ws)]
        cs = [t["csat"] for t in hit if t["csat"]]
        low = [c for c in cs if c <= 2]
        rows.append(dict(theme=name, tickets=len(hit), share=len(hit) / len(tickets),
                         csat=(sum(cs) / len(cs)) if len(cs) >= 10 else None, csat_n=len(cs),
                         low_share=(len(low) / len(cs)) if len(cs) >= 10 else None))
    rows.sort(key=lambda r: -r["tickets"])
    return rows


def bigrams(text):
    ts = tokens(text)
    return [f"{a} {b}" for a, b in zip(ts, ts[1:])]


def distinguishing(tickets, min_count=15, top=8):
    """Terms over-represented in low-CSAT (<=2) responses vs high (>=4). Lift with add-one smoothing."""
    low = Counter(w for t in tickets if t["csat"] and t["csat"] <= 2 for w in set(tokens(t["text"])))
    high = Counter(w for t in tickets if t["csat"] and t["csat"] >= 4 for w in set(tokens(t["text"])))
    nl = sum(1 for t in tickets if t["csat"] and t["csat"] <= 2) or 1
    nh = sum(1 for t in tickets if t["csat"] and t["csat"] >= 4) or 1
    out = [dict(term=w, low=c, high=high[w], lift=round(((c + 1) / nl) / ((high[w] + 1) / nh), 2))
           for w, c in low.items() if c >= min_count]
    out.sort(key=lambda r: -r["lift"])
    return out[:top]


def top_phrases(tickets, n=8):
    c = Counter(b for t in tickets for b in set(bigrams(t["text"])))
    return c.most_common(n)
