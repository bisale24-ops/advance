"""Build the backtest set: real concert tours and the acts that opened for them, from Wikipedia.

    python3 tools/fetch_tours.py data/tours.json

Reads the infobox of every page in the 2023-2025 concert-tour categories and keeps tours whose infobox names the
headliner and at least one support act. Opening acts are what a promoter actually booked, so they are the ground truth
the "who opens" step is scored against. Standard library only.
"""
import json, re, sys, time, urllib.parse, urllib.request

API = "https://en.wikipedia.org/w/api.php"
UA = "khlab-advance-backtest/1.0 (https://github.com/bisale24-ops)"
CATEGORIES = ["Category:2023 concert tours", "Category:2024 concert tours", "Category:2025 concert tours"]


def get(params):
    params = {**params, "format": "json", "formatversion": "2"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("wikipedia unreachable")


def members(cat):
    out, cont = [], {}
    while True:
        d = get({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "500", "cmnamespace": "0", **cont})
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return out
        cont = d["continue"]


def field(box, name):
    m = re.search(r"\|\s*" + name + r"\s*=(.*?)(?=\n\s*\|\s*[a-z_]+\s*=|\n\}\})", box, re.S)
    return m.group(1) if m else ""


def links(text):
    text = re.sub(r"<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->", "", text, flags=re.S)
    return [re.sub(r"\s*\(.*?\)$", "", l.split("|")[-1]).strip() for l in re.findall(r"\[\[([^\]]+)\]\]", text)]


def parse(title, wikitext):
    i = wikitext.lower().find("{{infobox concert")
    if i < 0:
        return None
    box = wikitext[i:i + 12000]
    artists = links(field(box, "artist"))
    support = [a for a in links(field(box, "support_acts") or field(box, "support")) if a not in artists]
    if not artists or not support:
        return None
    year = re.search(r"\{\{Start date\|(\d{4})", box)
    return {"tour": title, "headliner": artists[0], "co_headliners": artists[1:], "support": support,
            "year": int(year.group(1)) if year else None}


def main(out):
    titles = sorted({t for c in CATEGORIES for t in members(c)})
    tours = []
    for k in range(0, len(titles), 40):
        batch = titles[k:k + 40]
        d = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": "|".join(batch)})
        for p in d["query"]["pages"]:
            if "revisions" in p:
                t = parse(p["title"], p["revisions"][0]["slots"]["main"]["content"])
                if t:
                    tours.append(t)
        time.sleep(0.5)
    json.dump(sorted(tours, key=lambda t: t["tour"]), open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(titles)} tour pages, {len(tours)} with a headliner and support acts")


if __name__ == "__main__":
    main(sys.argv[1])
