"""Tiny shared text utilities (no third-party deps)."""
import math
import re
from collections import Counter

STOP = set("""a an and are as at be but by can could do does for from had has have how i if in into is it its
just me my no not of on or our so than that the their them then there these they this to up us was we were what
when which who will with would you your am been get got hi hello thanks thank please im ive dont cant""".split())

_tok = re.compile(r"[a-z][a-z']+")


def tokens(text, keep_stop=False):
    out = [t.strip("'") for t in _tok.findall(text.lower())]
    return out if keep_stop else [t for t in out if t not in STOP and len(t) > 2]


def stem(t):
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def stems(text):
    return [stem(t) for t in tokens(text)]


class Tfidf:
    """Minimal TF-IDF + cosine over a fixed document set."""

    def __init__(self, docs):
        self.docs = [Counter(stems(d)) for d in docs]
        n = len(self.docs)
        df = Counter(t for d in self.docs for t in d)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vecs = [self._norm(d) for d in self.docs]

    def _norm(self, counter):
        v = {t: (1 + math.log(c)) * self.idf.get(t, 0) for t, c in counter.items() if t in self.idf}
        n = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / n for t, x in v.items()}

    def scores(self, text):
        q = self._norm(Counter(stems(text)))
        return [sum(w * d.get(t, 0) for t, w in q.items()) for d in self.vecs]

    def best(self, text):
        s = self.scores(text)
        i = max(range(len(s)), key=s.__getitem__)
        return i, s[i]
