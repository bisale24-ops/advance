"""The brief in a terminal: python -m advance "Phoebe Bridgers in Chicago and Denver" """
import json
import sys

from . import web


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    as_json = "--json" in args
    text = " ".join(a for a in args if a != "--json").strip()
    if not text:
        print('usage: python -m advance "Headliner in City, City" [--json]', file=sys.stderr)
        return 2
    result = web.ask(text)
    if as_json or "error" in result:
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return 1 if "error" in result else 0
    
    b = result["brief"]
    print(f"ADVANCE — {b['headliner']['name']}" + (f" · {' · '.join(b['cities'])}" if b["cities"] else ""))
    for s in b["sections"]:
        print(f"\n{s['title'].upper()}  ({s['question']})")
        for line in s["lines"]:
            aff = f"{line['affinity']:.2f}" if line["affinity"] is not None else " n/a"
            print(f"  {aff}  {line['name']}")
        if not s["lines"]:
            print(f"  — {s['missing']}")
    for r in result.get("advice") or ():
        print(f"\n• {r['about']}: {r['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
