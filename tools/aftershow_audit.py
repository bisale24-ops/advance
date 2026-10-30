"""Are the after-show places real bars near the room? Facts only, nothing about taste.

    python3 tools/aftershow_audit.py docs/AFTERSHOW_AUDIT.md        # needs a Qloo key

For 5 headliners x 2 cities, the top 3 after-show places of the brief are checked on:
  * near   - within 5 km of the city's most-booked room (Qloo's no-signal list, top 1);
  * site   - the place's own website answers (HTTP 200);
  * drinks - that page mentions drinks (bar / cocktail / beer / wine / drinks / happy hour / menu).
Whether a place suits the fans is not checked: that is a judgement, and the audit does not make it.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from advance import brief, route  # noqa: E402
from advance.qloo import Qloo  # noqa: E402
from venue_audit import fetch  # noqa: E402

ARTISTS = ["Phoebe Bridgers", "Mitski", "Fontaines D.C.", "Chappell Roan", "Noah Kahan"]
CITIES = ["Chicago", "Denver"]
DRINKS = re.compile(r"\bbar\b|cocktail|beer|wine|drinks|happy hour|menu", re.I)


def main(out):
    q = Qloo.from_env()
    rows, ok, total = [], 0, 0
    for artist in ARTISTS:
        head = q.find(artist, "artist")
        for city in CITIES:
            room = brief.booked_rooms(q, head, city).lines[0]
            for line in brief.after_show(q, head, city, near=room).lines[:3]:
                near = None
                if None not in (line.lat, line.lon, room.lat, room.lon):
                    near = route.km({"lat": line.lat, "lon": line.lon}, {"lat": room.lat, "lon": room.lon})
                status, body = fetch(line.link) if line.link else ("no website", "")
                drinks = bool(DRINKS.search(body))
                good = near is not None and near <= 5 and status == 200 and drinks
                ok += good
                total += 1
                rows.append((artist, city, line.name, "-" if near is None else "%.1f km" % near, str(status), "yes" if drinks else "NO", room.name))
    L = ["# After-show audit", "", "Top 3 after-show places of 10 briefs (5 headliners x 2 cities). Pass all three checks: %d of %d." % (ok, total), "",
         "| headliner | city | place | distance to most-booked room | site | mentions drinks | room used |", "|---|---|---|---|---|---|---|"]
    L += ["| " + " | ".join(r) + " |" for r in rows]
    L += ["", "A site that blocks scripts fails the site and drinks checks; failures stay in the table.",
          "Not checked: whether a place suits these fans (a judgement), and sponsors: the brand lines are Qloo's audience affinity, and public data that would let a third party verify that alignment was not found, so they are left unvalidated."]
    pathlib.Path(out).write_text("\n".join(L) + "\n")
    print("\n".join(L[:4]))
    print("\n".join(L[4:]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/AFTERSHOW_AUDIT.md")
