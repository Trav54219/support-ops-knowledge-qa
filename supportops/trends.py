"""CSAT / first-response / resolution trends with robust anomaly flags."""
import statistics as st
from collections import defaultdict
from datetime import datetime


def daily(tickets):
    d = defaultdict(list)
    for t in tickets:
        d[t["created"][:10]].append(t)
    out = []
    for day in sorted(d):
        ts = d[day]
        cs = [t["csat"] for t in ts if t["csat"]]
        out.append(dict(day=day, volume=len(ts), frt=st.median(t["frt_min"] for t in ts),
                        res=st.median(t["res_hr"] for t in ts),
                        csat=(sum(cs) / len(cs)) if len(cs) >= 5 else None, csat_n=len(cs)))
    return out


def weekly(days):
    w = defaultdict(list)
    for r in days:
        iso = datetime.fromisoformat(r["day"]).isocalendar()
        w[(iso[0], iso[1])].append(r)
    out = []
    for k in sorted(w):
        rs = w[k]
        cs = [r["csat"] for r in rs if r["csat"] is not None]
        out.append(dict(week=f"{k[0]}-W{k[1]:02d}", volume=sum(r["volume"] for r in rs),
                        frt=st.median(r["frt"] for r in rs), res=st.median(r["res"] for r in rs),
                        csat=sum(cs) / len(cs) if cs else None))
    return out


def flag(series, key, window=14, z=3.5, same_dow=False):
    """Robust z-score vs trailing window (median/MAD). Returns list of (day, value, z)."""
    out = []
    for i in range(window, len(series)):
        v = series[i][key]
        if v is None:
            continue
        hist = [r[key] for r in series[max(0, i - window):i] if r[key] is not None]
        if len(hist) < window // 2:
            continue
        med = st.median(hist)
        mad = st.median(abs(x - med) for x in hist) * 1.4826 or 1e-9
        score = (v - med) / mad
        if abs(score) >= z:
            out.append((series[i]["day"], round(v, 2), round(score, 1)))
    return out


def anomalies(days):
    """Volume is compared by weekday type (weekends are structurally lower)."""
    res = {}
    wk = [r for r in days if datetime.fromisoformat(r["day"]).weekday() < 5]
    res["volume"] = flag(wk, "volume", window=10, z=3.5)
    res["frt"] = flag(days, "frt", z=3.5)
    res["csat"] = flag(days, "csat", z=3.5)
    res["res"] = flag(days, "res", z=3.5)
    return res
