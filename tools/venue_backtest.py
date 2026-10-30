"""Do the rooms Advance shortlists include the rooms real tours played? Measured on tour dates from Wikipedia.

    python3 tools/venue_backtest.py data/tours.json docs/venue_backtest.json docs/VENUE_BACKTEST.md   # needs a Qloo key

For each tour page, every US date row gives (city, venue) from the "Tour dates" table. Up to 4 distinct US cities per
tour are used. For each (headliner, city) two shortlists of concert rooms are built from Qloo:
  * taste    - the brief's "which room": rooms ranked by affinity to the headliner's audience;
  * popular  - the same rooms and city with no artist signal: Qloo's most popular concert rooms there,
               what any booker would list for any act.
A case is a hit if the room the tour actually played is in the first 8 (and the first 25) of the list.
Rows that are not US, have no linked venue, or whose venue Qloo does not tag as a concert room are counted, not dropped.
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from advance import brief  # noqa: E402
from advance.qloo import Empty, Qloo, QlooError  # noqa: E402

API = "https://en.wikipedia.org/w/api.php"
UA = "khlab-advance-backtest/1.0 (https://github.com/bisale24-ops)"
PER_TOUR = 4
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def wikitext(title):
    url = API + "?" + urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext", "format": "json", "formatversion": "2", "redirects": "1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)["parse"]["wikitext"]
        except Exception:  # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    return ""


def clean(cell):
    """The cell text without its attribute prefix ('rowspan="3" | x' -> 'x')."""
    m = re.match(r"^\s*([a-z-]+\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)\s*)+\|(?!\|)(.*)$", cell, re.S)
    return (m.group(3) if m else cell).strip()


def span(cell):
    m = re.search(r"rowspan\s*=\s*\"?(\d+)", cell.split("|")[0] if "|" in cell else cell)
    return int(m.group(1)) if m else 1


def link(cell):
    m = LINK.search(cell)
    return (m.group(1).strip(), (m.group(2) or m.group(1)).strip()) if m else None


def tables(text):
    for m in re.finditer(r"\{\|.*?\n\|\}", text, re.S):
        yield m.group(0)


def rows(text):
    """(city target, venue target, venue label) for US dates, from every wikitable that has City and Venue columns.
    Columns are found from the header; rowspans are carried down in every column."""
    out = []
    for table in tables(text):
        parts = re.split(r"\n\|-[^\n]*", table)
        start, header = 0, []
        for n, part in enumerate(parts[:3]):
            found = [re.sub(r"<.*?>|\[\[.*?\]\]|\(.*?\)", "", clean(c).casefold()).strip() for c in re.findall(r"^!(.*?)(?=\n|$)", part, re.M)]
            if any(h.startswith("city") for h in found) and any(h.startswith("venue") for h in found):
                start, header = n, found
                break
        parts = [None] + parts[start + 1:] if header else parts
        try:
            ci = next(i for i, h in enumerate(header) if h.startswith("city"))
            vi = next(i for i, h in enumerate(header) if h.startswith("venue"))
        except StopIteration:
            continue
        co = next((i for i, h in enumerate(header) if h.startswith("country")), None)
        width = len(header)
        carry = {}                       # column -> (cell text, rows still to cover)
        for row in parts[1:]:
            raw = []
            for line in row.strip().split("\n"):
                if line.startswith(("|", "!")) and not line.startswith(("|}", "|+")):
                    raw += [c for c in line[1:].split("||")] if line.startswith("|") else [line[1:]]
            if not raw:
                continue
            cells, k = [], 0
            for col in range(width):
                if col in carry and carry[col][1] > 0:
                    cells.append(carry[col][0])
                    carry[col] = (carry[col][0], carry[col][1] - 1)
                elif k < len(raw):
                    cell = raw[k]
                    k += 1
                    cells.append(clean(cell))
                    if span(cell) > 1:
                        carry[col] = (clean(cell), span(cell) - 1)
                else:
                    cells.append("")
            city, venue = link(cells[ci]), link(cells[vi])
            country = cells[co] if co is not None else "United States"
            if city and venue and "United States" in country + cells[ci]:
                out.append((city[0], venue[0], venue[1]))
            elif city and venue and co is None and re.search(r",\s*(" + US_STATES + r")\b", city[0]):
                out.append((city[0], venue[0], venue[1]))
    return out


US_STATES = ("Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|"
             "Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|"
             "Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|"
             "Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming")


def norm(s):
    s = re.sub(r"\(.*?\)", " ", s.casefold())
    s = re.sub(r"\b(the|at|of|amphitheatre|amphitheater|arena|center|centre|theatre|theater|stadium|field|hall)\b", " ", s)
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def same(a, b):
    a, b = norm(a), norm(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def city_query(target):
    return target if "," in target else target


def hit(played, names, k):
    return any(any(same(p, n) for p in played) for n in names[:k])


def main(tours_path, out_json, out_md):
    tours = json.load(open(tours_path))
    q = Qloo.from_env()
    cases, skipped = [], {"no_us_dates": 0, "headliner_missing": 0, "city_empty": 0}
    for t in tours:
        text = wikitext(t["tour"])
        seen, picked = set(), []
        for city, venue, label in rows(text):
            if city not in seen and len(picked) < PER_TOUR:
                seen.add(city)
                picked.append((city, venue, label))
        if not picked:
            skipped["no_us_dates"] += 1
            continue
        try:
            head = q.find(t["headliner"], "artist")
        except (Empty, QlooError):
            skipped["headliner_missing"] += 1
            continue
        for city, venue, label in picked:
            played = {venue, label} | {v for c, v, l in rows(text) if c == city} | {l for c, v, l in rows(text) if c == city}
            try:
                taste = [e.name for e in q.insights("place", entities=[head.id], take=50, filter__location__query=city,
                                                    filter__tags=brief.VENUE_TAGS, filter__exclude__tags=brief.NOT_VENUE).entities]
                popular = [e.name for e in q.insights("place", take=25, filter__location__query=city,
                                                      filter__tags=brief.VENUE_TAGS, filter__exclude__tags=brief.NOT_VENUE).entities]
            except (Empty, QlooError):
                skipped["city_empty"] += 1
                continue
            # hybrid: the city's popular rooms (what tours book), ordered by this audience's taste
            rank = {n: i for i, n in enumerate(taste)}
            hybrid = sorted(popular, key=lambda n: rank.get(n, 999))
            cases.append({"hybrid8": hit(played, hybrid, 8), "hybrid25": hit(played, hybrid, 25), "tour": t["tour"], "headliner": t["headliner"], "city": city, "played": sorted(played)[:3],
                          "taste": taste, "popular": popular,
                          "taste8": hit(played, taste, 8), "taste25": hit(played, taste, 25), "taste50": hit(played, taste, 50),
                          "pop8": hit(played, popular, 8), "pop25": hit(played, popular, 25)})
        print(len(cases), t["tour"], flush=True)
    json.dump({"skipped": skipped, "cases": cases}, open(out_json, "w"), indent=1)
    n = len(cases)
    c = lambda k: sum(x[k] for x in cases)
    both = sum(x["taste8"] and x["pop8"] for x in cases)
    only_t = sum(x["taste8"] and not x["pop8"] for x in cases)
    only_p = sum(x["pop8"] and not x["taste8"] for x in cases)
    md = ["# Venue backtest", "", f"{n} (headliner, US city) cases from {len({x['tour'] for x in cases})} real tours (dates tables on Wikipedia, 2023-2025). "
          f"Skipped and counted, not hidden: {skipped}.", "",
          "A case is a hit when the room the tour actually played in that city is in the first 8 (or 25) rooms of the list.", "",
          "| list | hit in first 8 | hit in first 25 |", "|---|---|---|",
          f"| Qloo taste for the headliner | {c('taste8')}/{n} ({c('taste8')/n:.0%}) | {c('taste25')}/{n} ({c('taste25')/n:.0%}) |",
          f"| Qloo popular rooms, no artist signal | {c('pop8')}/{n} ({c('pop8')/n:.0%}) | {c('pop25')}/{n} ({c('pop25')/n:.0%}) |",
          f"| Popular rooms, ordered by this audience's taste | {c('hybrid8')}/{n} ({c('hybrid8')/n:.0%}) | {c('hybrid25')}/{n} ({c('hybrid25')/n:.0%}) |", "",
          f"Taste list, first 50: {c('taste50')}/{n} ({c('taste50')/n:.0%}).", "",
          f"In the first 8: both hit {both}, only taste {only_t}, only the popularity list {only_p}.", ""]
    pathlib.Path(out_md).write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:4])
