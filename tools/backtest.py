"""Does Qloo's taste graph find the acts promoters actually booked? Measured on real tours.

    python3 tools/backtest.py data/tours.json docs/backtest.json     # needs a Qloo key (or QLOO_MODE=replay)

For every tour in data/tours.json (headliner + the support acts named in its Wikipedia infobox):
  * taste    — Qloo artists ranked by affinity to the headliner's audience (the brief's "who opens"
               without the popularity cap, so the cap cannot flatter the score);
  * baseline — the most popular artists sharing the headliner's leading genre tag, no taste signal:
               what a booker with a genre chart would pick.
Each real opener gets its rank in both lists (or none within the first TAKE). Reported: how many
openers each list finds in its top 10 / 25 / 100, and the median rank among those found.
Tours whose headliner Qloo cannot find are counted and listed, not dropped silently.
"""
import json
import statistics
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from advance.qloo import Empty, Qloo, QlooError  # noqa: E402

TAKE = 100
CUTS = (10, 25, 100)


def norm(name):
    return " ".join(name.casefold().replace("&", "and").split())


def rank_of(target, entities):
    """1-based rank of an entity by id, falling back to the name; None when absent."""
    for i, e in enumerate(entities, start=1):
        if e.id == target.id or norm(e.name) == norm(target.name):
            return i
    return None


def genre_tag(entity):
    raw = entity.raw or {}
    for tag in raw.get("tags") or ():
        if isinstance(tag, dict) and str(tag.get("type", "")).startswith("urn:tag:genre"):
            return tag.get("id")
    return None


def one_tour(q, tour):
    out = {"tour": tour["tour"], "headliner": tour["headliner"], "openers": [], "skipped": None}
    try:
        head = q.find(tour["headliner"], "artist")
    except (Empty, QlooError) as error:
        out["skipped"] = f"headliner not found: {type(error).__name__}"
        return out
    try:
        taste = q.insights("artist", entities=[head.id], take=TAKE, filter__exclude__entities=[head.id]).entities
    except (Empty, QlooError) as error:
        out["skipped"] = f"no taste list: {type(error).__name__}"
        return out
    tag = genre_tag(head)
    baseline = ()
    if tag:
        try:
            baseline = q.insights("artist", filter__tags=tag, take=TAKE, filter__exclude__entities=[head.id]).entities
        except (Empty, QlooError):
            baseline = ()
    out["genre_tag"] = tag
    for name in tour["support"]:
        try:
            act = q.find(name, "artist")
        except (Empty, QlooError):
            out["openers"].append({"name": name, "found": False})
            continue
        out["openers"].append({"name": name, "found": True, "taste_rank": rank_of(act, taste),
                               "baseline_rank": rank_of(act, baseline) if baseline else None})
    return out


def summarise(rows):
    found = [o for r in rows for o in r["openers"] if o.get("found")]
    def at(key, cut):
        return sum(1 for o in found if o.get(key) and o[key] <= cut)
    def med(key):
        ranks = [o[key] for o in found if o.get(key)]
        return statistics.median(ranks) if ranks else None
    return {
        "tours": len(rows),
        "tours_skipped": sum(1 for r in rows if r["skipped"]),
        "openers_named": sum(len(r["openers"]) for r in rows),
        "openers_found_in_qloo": len(found),
        "taste": {f"top{c}": at("taste_rank", c) for c in CUTS} | {"median_rank": med("taste_rank")},
        "baseline": {f"top{c}": at("baseline_rank", c) for c in CUTS} | {"median_rank": med("baseline_rank")},
    }


def main(src, dst, limit=None):
    tours = json.loads(pathlib.Path(src).read_text())[: limit or None]
    q = Qloo.from_env()
    rows = []
    for i, tour in enumerate(tours, 1):
        rows.append(one_tour(q, tour))
        if i % 10 == 0:
            print(f"{i}/{len(tours)}  calls so far {q.calls}", flush=True)
    result = {"summary": summarise(rows), "tours": rows}
    pathlib.Path(dst).write_text(json.dumps(result, indent=1))
    print(json.dumps(result["summary"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
