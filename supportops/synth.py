"""Seeded synthetic data generator. Everything here is invented; no real customers or companies."""
import json
import math
import random
from datetime import datetime, timedelta, date

START = datetime(2026, 8, 3)   # a Monday
DAYS = 84
AS_OF = date(2026, 10, 26)
SEED = 7

# topic -> vocabulary, templates, macro id, behaviour
TOPICS = {
    "password_reset": dict(w=14, macro="M01", csat=4.5, res=0.5, kw=["password", "reset", "locked", "link", "email"],
        t=["I forgot my password and the reset link never arrives in my email",
           "can't log in, my password reset link says it expired",
           "account locked after too many password attempts, need a reset"]),
    "billing_charge": dict(w=12, macro="M02", csat=3.2, res=6, kw=["charged", "twice", "billing", "charge", "card"],
        t=["I was charged twice this month on my card, please check the billing",
           "unexpected charge on my card after the plan renewal",
           "billing shows a duplicate charge, I only have one subscription"]),
    "refund_request": dict(w=9, macro="M03", csat=3.6, res=8, kw=["refund", "money", "return", "cancel", "order"],
        t=["I would like a refund for my order, it was not what I expected",
           "please refund the money, I want to return this order",
           "how do I get my money back for the order I returned"]),
    "shipping_delay": dict(w=13, macro="M04", csat=2.9, res=10, kw=["shipping", "delivery", "package", "tracking", "late"],
        t=["my package is late and the tracking has not updated in days",
           "delivery still not here, tracking says in transit since last week",
           "where is my shipping, the package is late"]),
    "address_change": dict(w=5, macro="M05", csat=4.0, res=2, kw=["address", "change", "shipping", "wrong", "moved"],
        t=["I entered the wrong address and need to change it before it ships",
           "we moved, can you update the delivery address on my order",
           "need to change my shipping address"]),
    "account_cancel": dict(w=6, macro="M06", csat=3.4, res=3, kw=["cancel", "subscription", "account", "stop", "close"],
        t=["I want to cancel my subscription and close my account",
           "how do I stop my plan, cancel the account please",
           "please close my account and stop all future payments"]),
    "login_2fa": dict(w=7, macro="M07", csat=3.5, res=4, kw=["code", "authentication", "verification", "phone", "login"],
        t=["I lost my phone and cannot get the verification code to login",
           "two factor authentication code never arrives on my phone",
           "stuck on verification step, the authentication code is not accepted"]),
    "app_crash": dict(w=10, macro="M08", csat=3.0, res=12, kw=["crash", "app", "freezes", "update", "error"],
        t=["the app crashes every time I open it after the update",
           "app freezes on startup and shows an error message",
           "keeps crashing since the last update, error on launch"]),
    "invoice_download": dict(w=8, macro="M09", csat=4.2, res=1.5, kw=["invoice", "receipt", "download", "pdf", "tax"],
        t=["where can I download an invoice or receipt for my tax records",
           "need a pdf invoice for last month, cannot find the download",
           "can you send a receipt, I need the invoice for taxes"]),
    "product_howto": dict(w=9, macro="M10", csat=3.9, res=3, kw=["setup", "integration", "connect", "configure", "how"],
        t=["how do I set up the integration and connect my other tools",
           "trying to configure the dashboard, where is the setup option",
           "need help to connect the integration, how to configure it"]),
}
VAGUE = ["it does not work, please help", "need help with my account", "something is wrong, can someone look",
         "hi I have a problem", "not working again, very frustrating"]
FILLER = ["this is the second time", "it is urgent", "I have been waiting", "I am a long time customer",
          "I tried the help center", "thanks in advance", "please advise"]

MACROS = [
    ("M01", "Password reset steps", "Reset password: use the Forgot password link, check the email spam folder for the reset link, links expire quickly. If your account is locked wait before trying again."),
    ("M02", "Duplicate charge", "Billing charge check: we will review the card charge, a duplicate or twice charge pending authorization usually drops off. We will refund a confirmed duplicate."),
    ("M03", "Refund process", "Refund request: return the order, once received the money is refunded to the original payment method."),
    ("M04", "Delayed shipping", "Shipping delay: the package tracking shows delivery status; late deliveries are traced with the carrier and we will follow up."),
    ("M05", "Address change", "Address change: update the delivery address before the order ships; wrong or moved address can be changed on the order page."),
    ("M06", "Cancellation", "Cancel subscription: close the account from settings, the plan stops at the end of the billing period."),
    ("M07", "2FA recovery", "Verification code help: authentication code sent to your phone; lost phone requires identity verification to login."),
    ("M08", "App crash triage", "App crash: update to the latest version, error on launch freezes are fixed by reinstalling. Send us the error details."),
    ("M09", "Invoice download", "Invoice and receipt: download the pdf invoice from billing settings; tax receipts are available for every charge."),
    ("M10", "Integration setup", "Setup guide: connect the integration under settings, configure the dashboard options step by step."),
]

# (topic, title, body, updated_days_before_as_of). Some topics deliberately have no article.
ARTICLES = [
    ("password_reset", "Reset your password", "Forgot your password? Use the reset link sent to your email. If the link expired or your account is locked, request a new reset.", 40),
    ("billing_charge", "Understanding charges on your card", "Why you see a pending or duplicate charge on your card, billing cycles and plan renewal explained.", 410),
    ("refund_request", "How refunds and returns work", "Request a refund or return an order. Money goes back to the original payment method once the return arrives.", 95),
    ("shipping_delay", "Track your package", "Check delivery tracking and shipping status, what to do when a package is late.", 60),
    ("login_2fa", "Two-factor authentication codes", "Set up two factor authentication, what to do if the verification code does not arrive on your phone.", 520),
    ("invoice_download", "Download invoices and receipts", "Find and download a pdf invoice or receipt for tax records in billing settings.", 120),
    ("app_crash", "Speed up your device", "Free storage space, close background tasks and keep handsets cool for smoother operation of mobile software.", 75),
]


def _poisson(rng, lam):
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def _hour_weight(h):
    return {8: .5, 9: 1.1, 10: 1.5, 11: 1.6, 12: 1.2, 13: 1.3, 14: 1.5, 15: 1.4, 16: 1.1, 17: .8, 18: .5, 19: .4, 20: .35, 21: .3}.get(h, .12)


def generate(seed=SEED, days=DAYS):
    rng = random.Random(seed)
    topics = list(TOPICS)
    weights = [TOPICS[t]["w"] for t in topics]
    agents = [f"agent_{i:02d}" for i in range(1, 13)]
    skill = {a: rng.gauss(0, 0.35) for a in agents}
    wh = sum(_hour_weight(h) for h in range(24))
    # injected events (documented in README, used by tests as ground truth)
    events = {"billing_incident_day": 60, "staffing_gap_day": 40}
    tickets, tid = [], 1000
    for d in range(days):
        day = START + timedelta(days=d)
        dow = day.weekday()
        base = 62 * (0.38 if dow >= 5 else 1.0) * (1.08 if dow == 0 else 1.0)
        if d == events["billing_incident_day"]:
            base *= 1.9
        for h in range(24):
            lam = base * _hour_weight(h) / wh * 2.2
            for _ in range(_poisson(rng, lam)):
                topic = rng.choices(topics, weights)[0]
                if d == events["billing_incident_day"] and rng.random() < 0.45:
                    topic = "billing_charge"
                cfg = TOPICS[topic]
                created = day + timedelta(hours=h, minutes=rng.randrange(60), seconds=rng.randrange(60))
                r = rng.random()
                if r < 0.10:
                    text = rng.choice(VAGUE)
                elif r < 0.16:  # mixed keywords from another topic
                    other = TOPICS[rng.choice(topics)]
                    text = rng.choice(cfg["t"]) + " and also " + rng.choice(other["t"])
                else:
                    text = rng.choice(cfg["t"])
                if rng.random() < 0.4:
                    text += ". " + rng.choice(FILLER)
                agent = rng.choice(agents)
                frt = rng.lognormvariate(math.log(22 if 8 <= h < 20 else 60), 0.6)
                if d == events["staffing_gap_day"]:
                    frt *= 3.2
                if d == events["billing_incident_day"]:
                    frt *= 1.8
                res = rng.lognormvariate(math.log(cfg["res"]), 0.5) * (1.6 if dow >= 5 else 1.0)
                c = cfg["csat"] + skill[agent] - min(frt / 120, 1.0) * 0.8 + rng.gauss(0, 0.9)
                if d == events["billing_incident_day"] and topic == "billing_charge":
                    c -= 1.3
                csat = int(min(5, max(1, round(c)))) if rng.random() < 0.38 else None
                tickets.append(dict(id=f"T{tid}", created=created.isoformat(timespec="minutes"),
                    channel=rng.choices(["email", "chat", "web"], [5, 3, 2])[0], true_topic=topic if r >= 0.10 else "vague",
                    text=text, agent=agent, frt_min=round(frt, 1), res_hr=round(res, 2),
                    handle_min=round(rng.lognormvariate(math.log(9), 0.4), 1), csat=csat))
                tid += 1
    return dict(meta=dict(seed=seed, days=days, as_of=AS_OF.isoformat(), synthetic=True, events=events),
        tickets=tickets,
        articles=[dict(id=f"A{i+1:02d}", topic=t, title=ti, body=b, updated=(AS_OF - timedelta(days=age)).isoformat())
                  for i, (t, ti, b, age) in enumerate(ARTICLES)],
        macros=[dict(id=i, name=n, body=b) for i, n, b in MACROS],
        macro_truth={t: c["macro"] for t, c in TOPICS.items()},
        agents=agents, qa=generate_qa(rng, tickets, agents, skill))


RUBRIC = {  # criterion -> weight (sum 100)
    "accuracy": 30, "resolution": 25, "policy": 15, "tone": 15, "empathy": 15,
}
REVIEWERS = {"rev_a": -0.35, "rev_b": 0.0, "rev_c": 0.45}  # severity bias, invented
NOISE = {"accuracy": 0.35, "resolution": 0.4, "policy": 0.35, "tone": 0.5, "empathy": 1.1}


def generate_qa(rng, tickets, agents, skill):
    sample = rng.sample(tickets, 420)
    reviews = []
    for i, t in enumerate(sample):
        calibration = i < 90
        revs = list(REVIEWERS) if calibration else [rng.choice(list(REVIEWERS))]
        true = {c: 2.9 + skill[t["agent"]] * 1.2 + rng.gauss(0, 0.5) for c in RUBRIC}
        for r in revs:
            scores = {c: int(min(4, max(0, round(true[c] + REVIEWERS[r] + rng.gauss(0, NOISE[c]))))) for c in RUBRIC}
            reviews.append(dict(ticket=t["id"], agent=t["agent"], reviewer=r, calibration=calibration, scores=scores))
    return dict(rubric=RUBRIC, reviews=reviews)


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))


def load(path):
    with open(path) as f:
        return json.load(f)
