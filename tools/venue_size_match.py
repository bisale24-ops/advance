"""Does matching the kind of room to the headliner's size predict real tour rooms better than taste or plain popularity?

    python3 tools/venue_size_match.py data/tours.json docs/VENUE_SIZE_MATCH.md     # needs a Qloo key

Same cases as venue_backtest.py (US dates tables from Wikipedia). Three lists per (headliner, US city), hit = the room the
tour played is in the first 8:
  * popular   - Qloo's most popular concert rooms in the city, any size, no artist signal;
  * sized     - the same but only the room kinds that fit the headliner's popularity (arena and stadium above CUT,
                concert hall and live-music venue below);
  * sized+taste - the sized list ordered by this audience's taste (rooms without a taste score keep popularity order).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import venue_backtest as vb  # noqa: E402
from advance import brief  # noqa: E402
from advance.qloo import Empty, Qloo, QlooError  # noqa: E402

BIG = ("urn:tag:category:place:arena", "urn:tag:category:place:stadium")
SMALL = ("urn:tag:category:place:live_music_venue", "urn:tag:category:place:concert_hall")


def main(tours_path, out_md, cut):
    q = Qloo.from_env()
    tally = {"n": 0, "popular": 0, "sized": 0, "sized+taste": 0, "taste": 0}
    for t in json.load(open(tours_path)):
        text = vb.wikitext(t["tour"])
        allrows = vb.rows(text)
        seen, picked = set(), []
        for city, venue, label in allrows:
            if city not in seen and len(picked) < vb.PER_TOUR:
                seen.add(city)
                picked.append(city)
        if not picked:
            continue
        try:
            head = q.find(t["headliner"], "artist")
        except (Empty, QlooError):
            continue
        tags = BIG if (head.popularity or 0) >= cut else SMALL
        for city in picked:
            played = {v for c, v, l in allrows if c == city} | {l for c, v, l in allrows if c == city}
            try:
                taste = [e.name for e in q.insights("place", entities=[head.id], take=50, filter__location__query=city,
                                                    filter__tags=brief.VENUE_TAGS, filter__exclude__tags=brief.NOT_VENUE).entities]
                popular = [e.name for e in q.insights("place", take=25, filter__location__query=city, filter__tags=brief.VENUE_TAGS,
                                                      filter__exclude__tags=brief.NOT_VENUE).entities]
                sized = [e.name for e in q.insights("place", take=25, filter__location__query=city, filter__tags=tags,
                                                    filter__exclude__tags=brief.NOT_VENUE).entities]
            except (Empty, QlooError):
                continue
            rank = {n: i for i, n in enumerate(taste)}
            tally["n"] += 1
            tally["popular"] += vb.hit(played, popular, 8)
            tally["sized"] += vb.hit(played, sized, 8)
            tally["sized+taste"] += vb.hit(played, sorted(sized, key=lambda n: rank.get(n, 999)), 8)
            tally["taste"] += vb.hit(played, taste, 8)
        print(tally, flush=True)
    n = tally["n"]
    md = [f"# Size-matched rooms (headliner popularity cut {cut})", "", f"{n} cases, same source as docs/VENUE_BACKTEST.md. Hit = the room the tour played is in the first 8.", "",
          "| list | hit in first 8 |", "|---|---|"]
    md += [f"| {k} | {tally[k]}/{n} ({tally[k]/n:.0%}) |" for k in ("taste", "popular", "sized", "sized+taste")]
    pathlib.Path(out_md).write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.9)
