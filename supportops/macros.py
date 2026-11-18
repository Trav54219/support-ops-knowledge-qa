"""Macro suggester: rank canned responses for a ticket by TF-IDF cosine."""
from .text import Tfidf


class Suggester:
    def __init__(self, macros):
        self.macros = macros
        self.idx = Tfidf([m["name"] + " " + m["body"] for m in macros])

    def suggest(self, text, k=3, min_score=0.25):
        s = self.idx.scores(text)
        order = sorted(range(len(s)), key=lambda i: -s[i])[:k]
        return [(self.macros[i]["id"], self.macros[i]["name"], round(s[i], 3)) for i in order if s[i] >= min_score]


def evaluate(suggester, tickets, truth):
    """Top-1 / top-3 hit rate vs the generator's intended macro. Tickets with no real topic are counted as abstain-correct if no suggestion."""
    n = hit1 = hit3 = abstain_ok = vague = 0
    for t in tickets:
        sug = suggester.suggest(t["text"])
        if t["true_topic"] == "vague":
            vague += 1
            abstain_ok += not sug
            continue
        n += 1
        want = truth[t["true_topic"]]
        ids = [s[0] for s in sug]
        hit1 += bool(ids) and ids[0] == want
        hit3 += want in ids
    return dict(tickets=n, top1=round(hit1 / n, 3), top3=round(hit3 / n, 3),
                vague=vague, vague_abstained=round(abstain_ok / vague, 3) if vague else None)
