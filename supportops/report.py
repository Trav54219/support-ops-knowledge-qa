"""Static HTML report. One file, inline CSS and SVG, no JS, no network."""
import html
import statistics as st
from datetime import date

from . import kb, trends, qa, macros, forecast, voc

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
e = html.escape


def table(headers, rows, num=()):
    h = "".join(f"<th>{e(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f'<td class="{"n" if i in num else ""}">{e(str(c))}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def spark(vals, flags=(), w=520, h=70):
    pts = [v for v in vals if v is not None]
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1
    xy = [(i * (w - 8) / (len(vals) - 1) + 4, h - 6 - (v - lo) / span * (h - 12)) for i, v in enumerate(vals) if v is not None]
    idx = [i for i, v in enumerate(vals) if v is not None]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    dots = "".join(f'<circle cx="{xy[idx.index(i)][0]:.1f}" cy="{xy[idx.index(i)][1]:.1f}" r="3.5" class="flag"/>' for i in flags if i in idx)
    return f'<svg viewBox="0 0 {w} {h}" role="img"><polyline points="{line}" class="ln"/>{dots}</svg>'


CSS = """body{font:15px/1.5 system-ui,sans-serif;margin:0;background:#fafafa;color:#1a1a1a}
main{max-width:980px;margin:0 auto;padding:24px 16px}h1{margin:.2em 0}h2{margin-top:2em;border-bottom:1px solid #ddd;padding-bottom:4px}
.note{background:#fff7e0;border:1px solid #e6cf8a;padding:10px 14px;border-radius:6px}
table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0;font-size:14px}th,td{border:1px solid #e2e2e2;padding:4px 8px;text-align:left}
th{background:#f0f0f0}td.n{text-align:right;font-variant-numeric:tabular-nums}svg{width:100%;height:auto;background:#fff;border:1px solid #e2e2e2}
.ln{fill:none;stroke:#2b6cb0;stroke-width:1.6}.flag{fill:#c53030}small,.muted{color:#666}.pill{padding:1px 7px;border-radius:9px;background:#eee;font-size:12px}
.bad{background:#fde8e8}.warn{background:#fff3d6}"""


def build(data):
    tk, as_of = data["tickets"], date.fromisoformat(data["meta"]["as_of"])
    s = []
    s.append(f"<h1>Support operations report</h1><p class='note'><b>Synthetic data.</b> Every ticket, article, macro and QA review here was generated "
             f"by a seeded script (seed {data['meta']['seed']}). Nothing is connected to Zendesk, Intercom or any helpdesk, and no real customers or companies appear. "
             f"{len(tk):,} tickets over {data['meta']['days']} days.</p>")
    # KB
    k = kb.analyze(tk, data["articles"], as_of)
    s.append("<h2>1. Knowledge-base gaps</h2>")
    s.append(table(["Topic", "Tickets", "Article match %", "Article", "Age (days)", "Status", "Deflectable now", "If fixed"],
        [(r["topic"], r["tickets"], f"{r['match_rate']:.0%}", r["article"] or "-", r["article_age_days"] if r["article_age_days"] is not None else "-",
          r["status"], r["deflectable"], r["potential_if_fixed"]) for r in k["rows"]], num=(1, 4, 6, 7)))
    s.append(f"<p class='muted'>Stale = older than {kb.STALE_DAYS} days. {e(k['assumption'])}. Topics come from keyword rules in <code>kb.py</code>.</p>")
    # trends
    days = trends.daily(tk)
    an = trends.anomalies(days)
    s.append("<h2>2. CSAT, first response, resolution</h2>")
    ws = trends.weekly(days)
    s.append(table(["Week", "Tickets", "Median first response (min)", "Median resolution (h)", "Avg CSAT"],
        [(w["week"], w["volume"], f"{w['frt']:.1f}", f"{w['res']:.1f}", f"{w['csat']:.2f}" if w["csat"] else "-") for w in ws], num=(1, 2, 3, 4)))
    for key, label in (("volume", "Daily volume"), ("frt", "Daily median first response (min)"), ("csat", "Daily avg CSAT")):
        fl = {d for d, _, _ in an[key]}
        s.append(f"<h3>{label}</h3>" + spark([r[key] for r in days], [i for i, r in enumerate(days) if r["day"] in fl]) + "<small>red dots = flagged days</small>")
    s.append("<h3>Anomaly flags (robust z, trailing window, |z| &ge; 3.5)</h3>")
    s.append(table(["Metric", "Day", "Value", "z"], [(m, d, v, z) for m, xs in an.items() for d, v, z in xs] or [("none", "", "", "")], num=(2, 3)))
    # QA
    s.append("<h2>3. QA scorecards</h2>")
    rub = data["qa"]["rubric"]
    s.append("<p>Rubric (weight): " + ", ".join(f"{c} {w}" for c, w in rub.items()) + ". Each criterion scored 0-4; agent score is the weighted percentage.</p>")
    ag = qa.agent_scores(data["qa"])
    s.append(table(["Agent", "Reviews", "Score /100", "Weakest criterion"] + list(rub), [(a["agent"], a["reviews"], a["score"], a["weakest"]) + tuple(a[c] for c in rub) for a in ag], num=(1, 2, 4, 5, 6, 7, 8)))
    cal = qa.calibration(data["qa"])
    s.append(f"<h3>Calibration ({cal['tickets']} tickets scored by all reviewers)</h3>")
    s.append(table(["Criterion", "Mean SD across reviewers", "Within 1 point", "Flag"],
        [(c, cal["criterion_sd"][c], f"{cal['within_one_point'][c]:.0%}", "recalibrate" if c in cal["flagged"] else "") for c in rub], num=(1, 2)))
    s.append(table(["Reviewer", "Bias vs others (score points)"], sorted(cal["reviewer_bias"].items()), num=(1,)))
    # macros
    sg = macros.Suggester(data["macros"])
    ev = macros.evaluate(sg, tk, data["macro_truth"])
    s.append("<h2>4. Macro suggester</h2>")
    s.append(f"<p>Against the generator's intended macro: top-1 <b>{ev['top1']:.1%}</b>, top-3 <b>{ev['top3']:.1%}</b> over {ev['tickets']:,} tickets; "
             f"abstained on {ev['vague_abstained']:.0%} of {ev['vague']} vague tickets. <small>On synthetic text written from the same vocabulary, so this overstates real-world accuracy.</small></p>")
    ex = [t for t in tk[:400] if t["true_topic"] != "vague"][::80][:5]
    s.append(table(["Ticket text", "Suggestions"], [(t["text"], "; ".join(f"{i} {n} ({sc})" for i, n, sc in sg.suggest(t["text"]))) for t in ex]))
    # forecast
    fc = forecast.staffing(tk)
    ros = forecast.default_roster()
    bl = forecast.backlog(fc["profile"], ros, fc["aht"])
    s.append("<h2>5. SLA and backlog forecast</h2>")
    s.append(f"<p>SLA: {forecast.SLA_TARGET:.0%} first response within {forecast.SLA_MINUTES:.0f} min, Erlang C, occupancy cap {forecast.OCCUPANCY_CAP:.0%}, "
             f"shrinkage {fc['shrink']:.0%}, mean handle time {fc['aht']} min (from the data).</p>")
    s.append(table(["Day", "Agent-hours needed", "Hours to schedule", "Peak agents", "Peak hour"],
        [(DOW[d], v["agent_hours"], v["scheduled_hours"], v["peak"], f"{v['peak_hour']:02d}:00") for d, v in fc["daily"].items()], num=(1, 2, 3)))
    sh = [fc["need"][(1, h)] for h in range(24)]
    ros_h = [ros[(1, h)] for h in range(24)]
    s.append("<h3>Tuesday by hour: needed vs rostered (8 weekday / 3 weekend agents, an invented roster)</h3>")
    s.append(table(["Hour"] + [f"{h:02d}" for h in range(7, 22)], [["Needed (net of shrinkage)"] + [math_ceil(sh[h] / (1 - fc["shrink"])) for h in range(7, 22)], ["Rostered"] + [ros_h[h] for h in range(7, 22)]]))
    peak = max(bl, key=lambda r: r["backlog"])
    s.append(f"<p>Expected backlog under this roster peaks at <b>{peak['backlog']}</b> tickets ({DOW[peak['day']]} {peak['hour']:02d}:00). "
             f"Forecast is the weekday-hour mean of history, so it ignores trend and incidents.</p>")
    # VOC
    s.append("<h2>6. Voice of customer</h2>")
    th = voc.themes(tk)
    s.append(table(["Theme", "Tickets", "Share", "Avg CSAT", "CSAT responses", "Share rating 1-2"],
        [(t["theme"], t["tickets"], f"{t['share']:.0%}", f"{t['csat']:.2f}" if t["csat"] else "-", t["csat_n"], f"{t['low_share']:.0%}" if t["low_share"] is not None else "-") for t in th], num=(1, 2, 3, 4, 5)))
    s.append("<h3>Terms over-represented in 1-2 star responses</h3>")
    s.append(table(["Term", "Low count", "High count", "Lift"], [(d["term"], d["low"], d["high"], d["lift"]) for d in voc.distinguishing(tk)], num=(1, 2, 3)))
    s.append("<h3>Most common phrases</h3><p>" + ", ".join(f"{e(p)} ({n})" for p, n in voc.top_phrases(tk)) + "</p>")
    return f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Support ops report (synthetic)</title><style>{CSS}</style><body><main>{''.join(s)}</main></body></html>"


def math_ceil(x):
    import math
    return math.ceil(x)
