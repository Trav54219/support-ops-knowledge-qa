"""QA scorecard engine: rubric -> per-agent scores -> calibration variance across reviewers."""
import statistics as st
from collections import defaultdict
from itertools import combinations

MAX_SCORE = 4
SD_FLAG = 0.6   # criterion SD across reviewers above this = rubric needs calibration


def score_review(scores, rubric):
    total_w = sum(rubric.values())
    return 100 * sum(rubric[c] * scores[c] / MAX_SCORE for c in rubric) / total_w


def agent_scores(qa):
    rubric = qa["rubric"]
    acc = defaultdict(list)
    crit = defaultdict(lambda: defaultdict(list))
    for r in qa["reviews"]:
        acc[r["agent"]].append(score_review(r["scores"], rubric))
        for c, v in r["scores"].items():
            crit[r["agent"]][c].append(v)
    rows = []
    for a, xs in acc.items():
        rows.append(dict(agent=a, reviews=len(xs), score=round(st.mean(xs), 1),
                         weakest=min(rubric, key=lambda c: st.mean(crit[a][c])),
                         **{c: round(st.mean(v), 2) for c, v in crit[a].items()}))
    rows.sort(key=lambda r: r["score"])
    return rows


def calibration(qa):
    rubric = qa["rubric"]
    by_t = defaultdict(list)
    for r in qa["reviews"]:
        if r["calibration"]:
            by_t[r["ticket"]].append(r)
    by_t = {k: v for k, v in by_t.items() if len(v) >= 2}
    crit_sd = {}
    for c in rubric:
        crit_sd[c] = round(st.mean(st.pstdev([r["scores"][c] for r in rs]) for rs in by_t.values()), 2)
    agree = {c: round(st.mean(
        1.0 if abs(a["scores"][c] - b["scores"][c]) <= 1 else 0.0
        for rs in by_t.values() for a, b in combinations(rs, 2)), 3) for c in rubric}
    bias = defaultdict(list)
    for rs in by_t.values():
        for r in rs:
            others = [score_review(o["scores"], rubric) for o in rs if o is not r]
            bias[r["reviewer"]].append(score_review(r["scores"], rubric) - st.mean(others))
    return dict(tickets=len(by_t), criterion_sd=crit_sd, within_one_point=agree,
                flagged=[c for c, s in crit_sd.items() if s > SD_FLAG],
                reviewer_bias={k: round(st.mean(v), 1) for k, v in bias.items()})
