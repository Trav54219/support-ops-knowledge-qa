"""Knowledge-base gap analysis: ticket topics with no or stale article, and deflection potential."""
from collections import Counter, defaultdict
from datetime import date

from .text import Tfidf, stems

# Tagging rules a support team would maintain. Deliberately separate from the generator.
TAXONOMY = {
    "password_reset": ["password", "reset", "locked"],
    "billing_charge": ["charged", "charge", "billing", "duplicate"],
    "refund_request": ["refund", "money back", "return"],
    "shipping_delay": ["package", "tracking", "delivery", "late"],
    "address_change": ["address"],
    "account_cancel": ["cancel", "close my account", "stop my plan"],
    "login_2fa": ["verification", "authentication", "two factor", "code"],
    "app_crash": ["crash", "freezes", "freezing"],
    "invoice_download": ["invoice", "receipt"],
    "product_howto": ["integration", "configure", "set up", "setup"],
}

STALE_DAYS = 180
MATCH_MIN = 0.18        # tf-idf cosine needed to count an article as answering a ticket
DEFLECT_RATE = 0.25     # ASSUMPTION: share of matched tickets a good article would deflect. Tune per org.


def classify(text):
    t = text.lower()
    hits = {k: sum(1 for w in ws if w in t) for k, ws in TAXONOMY.items()}
    best = max(hits, key=hits.get)
    return best if hits[best] else "unclassified"


def analyze(tickets, articles, as_of, stale_days=STALE_DAYS, match_min=MATCH_MIN, deflect_rate=DEFLECT_RATE):
    idx = Tfidf([a["title"] + " " + a["body"] for a in articles])
    by_topic = defaultdict(list)
    for t in tickets:
        by_topic[classify(t["text"])].append(t)
    art_topic = defaultdict(list)
    for i, a in enumerate(articles):
        art_topic[a["topic"]].append(i)
    rows = []
    for topic, ts in by_topic.items():
        own = art_topic.get(topic, [])
        if topic == "unclassified":
            rows.append(dict(topic=topic, tickets=len(ts), match_rate=0.0, article=None, article_age_days=None,
                             status="unclassified", deflectable=0, potential_if_fixed=0))
            continue
        # a ticket counts as answered only by an article written for its own topic
        matched, best = 0, Counter()
        for t in ts:
            sc = idx.scores(t["text"])
            cand = [(sc[i], i) for i in own]
            if cand and max(cand)[0] >= match_min:
                matched += 1
                best[max(cand)[1]] += 1
        rate = matched / len(ts)
        aid = best.most_common(1)[0][0] if best else (own[0] if own else None)
        art = articles[aid] if aid is not None else None
        age = (as_of - date.fromisoformat(art["updated"])).days if art else None
        if not own:
            status = "no_article"
        elif rate < 0.5:
            status = "article_not_matching"
        elif age > stale_days:
            status = "stale"
        else:
            status = "covered"
        rows.append(dict(topic=topic, tickets=len(ts), match_rate=rate, article=art["id"] if art else None,
                         article_age_days=age, status=status,
                         deflectable=round(matched * deflect_rate) if status in ("covered", "stale") else 0,
                         potential_if_fixed=round(len(ts) * deflect_rate) if status != "covered" else 0))
    rows.sort(key=lambda r: -r["tickets"])
    return dict(rows=rows, total=len(tickets), assumption=f"deflect rate {deflect_rate:.0%} of matched tickets (assumption, not measured)")
