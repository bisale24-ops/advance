"""Are the rooms Advance names real live-music venues? A small audit anyone can rerun (needs a Qloo key).

    python3 tools/venue_audit.py docs/VENUE_AUDIT.md

For each of 5 headliners x 3 cities, the top room of the brief is checked on three things, nothing invented:
  * city    - Qloo's address names the city asked for;
  * site    - the venue's own website answers (HTTP 200 after redirects);
  * events  - that page mentions shows (tickets / events / calendar / concert / live music / shows).
Capacity and availability are not checked: Qloo does not hold them and the page does not state them reliably.
"""
import re
import sys
import pathlib
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from advance import brief  # noqa: E402
from advance.qloo import Qloo  # noqa: E402

ARTISTS = ["Phoebe Bridgers", "Mitski", "Fontaines D.C.", "Chappell Roan", "Noah Kahan"]
CITIES = ["Chicago", "Denver", "Nashville"]
WORDS = re.compile(r"ticket|events?\b|calendar|concert|live music|shows?\b", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (advance venue audit)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(400000).decode("utf-8", "replace")
    except Exception as error:  # noqa: BLE001 - any failure is a finding
        return type(error).__name__, ""


def main(out):
    q = Qloo.from_env()
    rows, ok = [], 0
    for artist in ARTISTS:
        head = q.find(artist, "artist")
        for city in CITIES:
            section = brief.which_room(q, head, city)
            if not section.lines:
                rows.append((artist, city, "(none)", "-", "-", "-", section.missing))
                continue
            line = section.lines[0]
            addr = line.note.split(" · ")[0]
            in_city = city.casefold() in addr.casefold()
            status, body = fetch(line.link) if line.link else ("no website", "")
            events = bool(WORDS.search(body))
            good = in_city and status == 200 and events
            ok += good
            rows.append((artist, city, line.name, "yes" if in_city else "NO", str(status), "yes" if events else "NO", addr))
    lines = ["# Venue audit", "", "Top room of each brief, 5 headliners x 3 cities. Passes all three checks: %d of %d." % (ok, len(rows)), "",
             "| headliner | city | top room | city in address | site | mentions shows | address |", "|---|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    lines += ["", "A failure means the check could not confirm it (a site that blocks scripts also fails); it is listed, not removed.",
              "Not checked: capacity, availability, whether the room suits the headliner's draw."]
    pathlib.Path(out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/VENUE_AUDIT.md")
