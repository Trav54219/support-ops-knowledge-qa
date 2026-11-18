"""SLA staffing (Erlang C) and backlog forecast from weekday x hour arrival patterns."""
import math
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta

SLA_TARGET = 0.80       # share answered within the threshold
SLA_MINUTES = 30.0
SHRINKAGE = 0.30        # breaks, training, meetings
OCCUPANCY_CAP = 0.85


def erlang_c(traffic, agents):
    """Probability a contact has to wait. traffic in Erlangs."""
    if agents <= traffic:
        return 1.0
    s, term = 0.0, 1.0
    for k in range(agents):
        if k:
            term *= traffic / k
        s += term
    top = term * traffic / agents * agents / (agents - traffic)
    return top / (s + top)


def service_level(traffic, agents, aht_min, thr_min=SLA_MINUTES):
    if agents <= traffic:
        return 0.0
    return 1 - erlang_c(traffic, agents) * math.exp(-(agents - traffic) * thr_min / aht_min)


def agents_needed(per_hour, aht_min, target=SLA_TARGET, thr_min=SLA_MINUTES, occ=OCCUPANCY_CAP):
    if per_hour <= 0:
        return 0
    a = per_hour * aht_min / 60
    n = max(1, math.ceil(a))
    while service_level(a, n, aht_min, thr_min) < target or a / n > occ:
        n += 1
    return n


def arrival_profile(tickets):
    """Mean arrivals per (weekday, hour) over the weeks observed."""
    days = defaultdict(int)
    counts = defaultdict(int)
    seen = set()
    for t in tickets:
        dt = datetime.fromisoformat(t["created"])
        counts[(dt.weekday(), dt.hour)] += 1
        seen.add(dt.date())
    n_dow = defaultdict(int)
    for d in seen:
        n_dow[d.weekday()] += 1
    return {(d, h): counts[(d, h)] / n_dow[d] for d in range(7) for h in range(24) if n_dow[d]}


def staffing(tickets, shrink=SHRINKAGE):
    prof = arrival_profile(tickets)
    aht = st.mean(t["handle_min"] for t in tickets)
    need = {k: agents_needed(v, aht) for k, v in prof.items()}
    daily = {}
    for d in range(7):
        hrs = sum(need[(d, h)] for h in range(24))
        daily[d] = dict(agent_hours=hrs, scheduled_hours=round(hrs / (1 - shrink), 1),
                        peak=max(need[(d, h)] for h in range(24)),
                        peak_hour=max(range(24), key=lambda h: (need[(d, h)], prof[(d, h)])))
    return dict(profile=prof, need=need, aht=round(aht, 2), daily=daily, shrink=shrink)


def default_roster():
    """A plausible fixed roster to test against: 8 agents 8-18 weekdays, 3 agents 9-17 weekends."""
    r = {}
    for d in range(7):
        for h in range(24):
            r[(d, h)] = (8 if 8 <= h < 18 else 0) if d < 5 else (3 if 9 <= h < 17 else 0)
    return r


def backlog(profile, roster, aht, shrink=SHRINKAGE, weeks=1, occ=OCCUPANCY_CAP):
    """Deterministic hourly fluid model of expected backlog (tickets waiting) over a week."""
    q, out = 0.0, []
    for w in range(weeks):
        for d in range(7):
            for h in range(24):
                cap = roster[(d, h)] * (1 - shrink) * occ * 60 / aht
                q = max(0.0, q + profile[(d, h)] - cap)
                out.append(dict(day=d, hour=h, arrivals=round(profile[(d, h)], 2), capacity=round(cap, 2), backlog=round(q, 1)))
    return out
