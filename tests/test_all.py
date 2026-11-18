import math
from datetime import date, datetime, timedelta

from supportops import synth, kb, trends, qa, macros, forecast, voc, report, text


def test_generator_is_deterministic_and_synthetic(data):
    again = synth.generate()
    assert again["tickets"][:50] == data["tickets"][:50] and len(again["tickets"]) == len(data["tickets"])
    assert data["meta"]["synthetic"] is True
    assert all("@" not in t["text"] for t in data["tickets"])  # no emails/personal data


def test_kb_gaps_found(data):
    k = {r["topic"]: r for r in kb.analyze(data["tickets"], data["articles"], date.fromisoformat(data["meta"]["as_of"]))["rows"]}
    for t in ("address_change", "account_cancel", "product_howto"):
        assert k[t]["status"] == "no_article"
        assert k[t]["potential_if_fixed"] > 0
    assert k["billing_charge"]["status"] == "stale" and k["login_2fa"]["status"] == "stale"
    assert k["app_crash"]["status"] == "article_not_matching"
    assert k["password_reset"]["status"] == "covered"
    assert k["unclassified"]["deflectable"] == 0


def test_kb_stale_threshold_is_respected(data):
    rows = kb.analyze(data["tickets"], data["articles"], date.fromisoformat(data["meta"]["as_of"]), stale_days=600)["rows"]
    assert not [r for r in rows if r["status"] == "stale"]


def test_anomalies_catch_injected_days(data):
    days = trends.daily(data["tickets"])
    an = trends.anomalies(days)
    start = synth.START.date()
    gap = (start + timedelta(days=data["meta"]["events"]["staffing_gap_day"])).isoformat()
    inc = (start + timedelta(days=data["meta"]["events"]["billing_incident_day"])).isoformat()
    assert gap in [d for d, _, _ in an["frt"]]
    assert inc in [d for d, _, _ in an["csat"]] and inc in [d for d, _, _ in an["volume"]]


def test_flag_quiet_series_has_no_flags():
    s = [dict(day=f"d{i}", v=10 + (i % 3) * 0.1) for i in range(40)]
    assert trends.flag(s, "v") == []


def test_qa_weights_and_scoring(data):
    assert sum(data["qa"]["rubric"].values()) == 100
    assert qa.score_review({c: 4 for c in data["qa"]["rubric"]}, data["qa"]["rubric"]) == 100
    assert qa.score_review({c: 0 for c in data["qa"]["rubric"]}, data["qa"]["rubric"]) == 0
    rows = qa.agent_scores(data["qa"])
    assert len(rows) == 12 and all(0 <= r["score"] <= 100 for r in rows)
    assert rows == sorted(rows, key=lambda r: r["score"])


def test_calibration_sees_reviewer_bias_and_noisy_criterion(data):
    c = qa.calibration(data["qa"])
    assert c["reviewer_bias"]["rev_a"] < -5 < 5 < c["reviewer_bias"]["rev_c"]
    assert c["criterion_sd"]["empathy"] == max(c["criterion_sd"].values())
    assert "empathy" in c["flagged"]


def test_macro_suggester(data):
    sg = macros.Suggester(data["macros"])
    top = sg.suggest("my package is late and tracking has not updated")
    assert top and top[0][0] == "M04"
    assert sg.suggest("hi I have a problem") == []
    ev = macros.evaluate(sg, data["tickets"], data["macro_truth"])
    assert ev["top1"] > 0.9 and ev["top3"] >= ev["top1"]


def test_erlang_c_known_values():
    assert math.isclose(forecast.erlang_c(0.5, 1), 0.5)       # M/M/1: P(wait) = rho
    assert forecast.erlang_c(5, 5) == 1.0
    assert forecast.erlang_c(10, 11) > forecast.erlang_c(10, 14)
    assert forecast.service_level(10, 14, 10) > forecast.service_level(10, 11, 10)


def test_agents_needed_monotonic_and_meets_sla():
    prev = 0
    for rate in (0, 5, 20, 60, 120):
        n = forecast.agents_needed(rate, 10)
        assert n >= prev
        prev = n
        if rate:
            a = rate * 10 / 60
            assert forecast.service_level(a, n, 10) >= forecast.SLA_TARGET and a / n <= forecast.OCCUPANCY_CAP
    assert forecast.agents_needed(0, 10) == 0


def test_staffing_follows_arrival_pattern(data):
    fc = forecast.staffing(data["tickets"])
    assert fc["daily"][1]["agent_hours"] > fc["daily"][5]["agent_hours"]      # weekday > Saturday
    assert 8 <= fc["daily"][1]["peak_hour"] <= 16
    assert fc["need"][(1, 3)] <= fc["need"][(1, 11)]


def test_backlog_drains_when_capacity_exceeds_arrivals():
    prof = {(d, h): 5.0 for d in range(7) for h in range(24)}
    big = {k: 50 for k in prof}
    assert max(r["backlog"] for r in forecast.backlog(prof, big, 10)) == 0
    none = {k: 0 for k in prof}
    assert forecast.backlog(prof, none, 10)[-1]["backlog"] == 5.0 * 168


def test_voc_themes_and_terms(data):
    th = {t["theme"]: t for t in voc.themes(data["tickets"])}
    assert th["Delivery and shipping"]["csat"] < th["Access and login"]["csat"]
    assert voc.distinguishing(data["tickets"])
    assert text.tokens("The package is LATE!") == ["package", "late"]


def test_report_html(data, tmp_path):
    h = report.build(data)
    assert h.startswith("<!doctype html>") and "Synthetic data" in h
    assert "Zendesk" in h and "<script" not in h
    for sec in ("Knowledge-base gaps", "QA scorecards", "Macro suggester", "SLA and backlog", "Voice of customer"):
        assert sec in h
