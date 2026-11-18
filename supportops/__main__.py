import argparse
import os

from . import synth, report


def main():
    ap = argparse.ArgumentParser(prog="supportops")
    ap.add_argument("cmd", choices=["generate", "report", "all"])
    ap.add_argument("--data", default="data/synthetic.json")
    ap.add_argument("--out", default="report/index.html")
    ap.add_argument("--seed", type=int, default=synth.SEED)
    a = ap.parse_args()
    if a.cmd in ("generate", "all"):
        os.makedirs(os.path.dirname(a.data), exist_ok=True)
        d = synth.generate(a.seed)
        synth.save(a.data, d)
        print(f"wrote {a.data}: {len(d['tickets'])} tickets, {len(d['qa']['reviews'])} QA reviews")
    if a.cmd in ("report", "all"):
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w") as f:
            f.write(report.build(synth.load(a.data)))
        print(f"wrote {a.out}")


main()
