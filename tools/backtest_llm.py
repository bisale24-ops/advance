"""The LLM-only baseline: the same model that plans Advance, asked for openers without Qloo.

    python3 tools/backtest_llm.py data/tours.json docs/backtest.json   # adds "llm" to the backtest
    LLM_MODE=replay python3 tools/backtest_llm.py ...                   # from fixtures/llm, no key

For every tour the model (Apertus 70B via Public AI) gets only the headliner and lists 100 artists
that would open for them. Each real support act gets its rank in that list, scored exactly like the
taste list and the genre chart. The tours are from 2023-2025 and on Wikipedia, so a model trained on
the web may have read who opened — any bias here favours the LLM, not Qloo.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from advance import plan  # noqa: E402
import backtest  # noqa: E402

CACHE = ROOT / "fixtures" / "llm"
PROMPT = ("List 100 different artists who would be good opening acts for a {name} concert tour, best fit first. "
          "One artist name per line, numbered, no commentary.")


def ask(name):
    text = PROMPT.format(name=name)
    slot = CACHE / (hashlib.sha256(text.encode()).hexdigest()[:20] + ".json")
    if slot.exists():
        return json.loads(slot.read_text())["answer"]
    if os.environ.get("LLM_MODE") == "replay":
        raise RuntimeError(f"no recording for {name}")
    spec = next(s for s in plan.ENDPOINTS if s["name"] == "publicai")
    key = os.environ.get(spec["env"]) or (pathlib.Path.home() / ".config" / spec["file"]).read_text().strip()
    body = {"model": spec["model"], "temperature": 0, "max_tokens": 1600,
            "messages": [{"role": "user", "content": text}]}
    for attempt in range(5):
        try:
            req = urllib.request.Request(spec["url"], data=json.dumps(body).encode(), headers={
                "content-type": "application/json", "authorization": "Bearer " + key,
                "user-agent": "advance/0.1 (+https://github.com/bisale24-ops)"})
            with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 - fixed endpoint
                answer = json.load(r)["choices"][0]["message"]["content"]
            CACHE.mkdir(parents=True, exist_ok=True)
            slot.write_text(json.dumps({"model": spec["model"], "prompt": text, "answer": answer}, ensure_ascii=False))
            return answer
        except Exception:  # noqa: BLE001 - 429/504 from the free tier: back off and retry
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"model failed for {name}")


def names(answer):
    out = []
    for line in (answer or "").splitlines():
        m = re.match(r"^\s*(?:\d+[.)]|[-*])\s*(.+?)\s*$", line)
        if m:
            out.append(re.sub(r"\s+[–—-]\s.*$|\s*[(\[].*$", "", m.group(1).strip("*_ ")).strip("*_ "))
    return out


def main(tours_path, out_path):
    tours = json.loads(pathlib.Path(tours_path).read_text())
    result = json.loads(pathlib.Path(out_path).read_text())
    by_tour = {r["tour"]: r for r in result["tours"]}
    heads = sorted({t["headliner"] for t in tours})
    with cf.ThreadPoolExecutor(4) as pool:
        lists = dict(zip(heads, pool.map(lambda h: names(ask(h)), heads)))
    ranks = []
    for row in result["tours"]:
        if row["skipped"]:
            continue
        listed = [backtest.norm(n) for n in lists.get(row["headliner"], [])]
        for o in row["openers"]:
            if not o.get("found"):
                continue
            n = backtest.norm(o["name"])
            o["llm_rank"] = listed.index(n) + 1 if n in listed else None
            ranks.append(o["llm_rank"])
    found = [r for r in ranks if r]
    result["summary"]["llm"] = {f"top{c}": sum(1 for r in found if r <= c) for c in backtest.CUTS}
    result["summary"]["llm"]["median_rank"] = sorted(found)[len(found) // 2] if found else None
    result["summary"]["llm"]["names_per_list"] = round(sum(len(v) for v in lists.values()) / max(1, len(lists)), 1)
    result["summary"]["llm"]["model"] = plan.ENDPOINTS[1]["model"]
    pathlib.Path(out_path).write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(json.dumps(result["summary"], indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
