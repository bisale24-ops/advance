"""Shrink recorded Qloo responses to the fields Advance reads, so the recordings can live in git.

    python3 tools/slim_fixtures.py fixtures/qloo

A raw insights answer carries descriptions, images, hours and hundreds of tags per entity (about
260 KB a call). Entity.of reads the id, name, type, popularity, affinity, tags and location; the
backtest reads the genre tags. Everything else is dropped. Run it again at any time: it is idempotent.
"""
import json
import pathlib
import sys

KEEP_TAG = ("tag_id", "id", "type", "name")


def slim_entity(e):
    out = {k: e[k] for k in ("entity_id", "id", "name", "subtype", "types", "popularity", "location") if k in e}
    if isinstance(e.get("query"), dict) and "affinity" in e["query"]:
        out["query"] = {"affinity": e["query"]["affinity"]}
    geo = (e.get("properties") or {}).get("geocode")
    if geo:
        out["properties"] = {"geocode": geo}
    tags = [t for t in e.get("tags") or () if isinstance(t, dict)]
    if tags:
        keep = [t for t in tags if str(t.get("type", "")).startswith(("urn:tag:genre", "urn:tag:category"))] or tags[:5]
        out["tags"] = [{k: t[k] for k in KEEP_TAG if k in t} for t in keep[:12]]
    return out


def slim(response):
    if not isinstance(response, dict):
        return response
    results = response.get("results")
    if isinstance(results, list):                       # /search
        response = dict(response, results=[slim_entity(e) for e in results])
    elif isinstance(results, dict) and "entities" in results:
        response = dict(response, results=dict(results, entities=[slim_entity(e) for e in results["entities"]]))
    return response


def main(folder):
    before = after = 0
    for path in sorted(pathlib.Path(folder).glob("*.json")):
        raw = path.read_text()
        record = json.loads(raw)
        record["response"] = slim(record["response"])
        new = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        before, after = before + len(raw), after + len(new)
        path.write_text(new)
    print(f"{before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fixtures/qloo")
