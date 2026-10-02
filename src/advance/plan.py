"""The agent: a promoter's sentence in, a plan of Qloo calls out, and a recommendation that cannot invent.

Two model calls, both schema-constrained, so neither can drift:
  1. `plan`   — the sentence becomes {headliner, cities, opener_share}. Cities are free text (Qloo
                resolves them); nothing else is accepted.
  2. `advise` — after the brief is built from Qloo, the model writes three recommendations. Each
                must name an entity *from the brief*: the schema enumerates the allowed names, so
                an artist or venue that Qloo did not return is unrepresentable, not just discouraged.
Without a model, a pattern planner and a template adviser answer, and the result says which ran.
"""
import json
import os
import pathlib
import re
import time
import urllib.request

ENDPOINTS = (
    {"name": "gemini", "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
     "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"), "env": "GEMINI_API_KEY", "file": "gemini.key"},
    {"name": "publicai", "url": "https://api.publicai.co/v1/chat/completions",
     "model": os.environ.get("PUBLICAI_MODEL", "swiss-ai/apertus-v1.5-70b"), "env": "PUBLICAI_API_KEY",
     "file": "publicai.key"},
)
TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "25"))
MAX_CITIES = 3


def endpoint():
    for spec in ENDPOINTS:
        key = os.environ.get(spec["env"], "").strip()
        if not key:
            try:
                key = (pathlib.Path.home() / ".config" / spec["file"]).read_text().strip()
            except OSError:
                key = ""
        if key:
            return dict(spec, key=key)
    return None


def _structured(system, user, schema, name, transport=None):
    """One schema-guided completion. Raises on any failure so the caller can fall back."""
    spec = endpoint()
    if spec is None:
        raise RuntimeError("no model key")
    body = {"model": spec["model"], "temperature": 0, "max_tokens": 600,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}}}
    request = urllib.request.Request(  # noqa: S310 - fixed https endpoints
        spec["url"], data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "authorization": "Bearer " + spec["key"],
                 # Cloudflare in front of Public AI refuses urllib's default User-Agent (403, code 1010)
                 "user-agent": "advance/0.1 (+https://github.com/bisale24-ops)"})
    started = time.perf_counter()
    open_ = transport or urllib.request.urlopen
    with open_(request, timeout=TIMEOUT) as response:
        data = json.load(response)
    answer = json.loads(data["choices"][0]["message"].get("content") or "")
    return answer, {"model": spec["model"].split("/")[-1], "ms": round((time.perf_counter() - started) * 1000)}


# ---- 1. the plan ------------------------------------------------------------------------------

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "headliner": {"type": "string"},
        "cities": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_CITIES},
        "opener_share": {"type": "number", "minimum": 0.3, "maximum": 1.0},
    },
    "required": ["headliner", "cities", "opener_share"],
    "additionalProperties": False,
}

PLAN_SYSTEM = """You turn a concert promoter's request into a plan for a tour-advance tool.
headliner: the one artist being booked, exactly as named. cities: the cities the promoter names, at most three, empty if none.
opener_share: how big the opening act may be relative to the headliner's popularity — 0.92 by default,
lower (e.g. 0.6) if they ask for a smaller or emerging opener, 1.0 if they want a co-headliner.
Never invent a city or an artist the request does not name."""


def plan_with_patterns(sentence):
    text = sentence.strip()
    m = re.search(r"^(?:book|advance|plan|tour)?\s*(?:for\s+)?(.+?)(?:\s+(?:in|at|for)\s+(.+?))?[.!?]?$", text, re.I)
    headliner = (m.group(1) if m else text).strip(" ,")
    cities = [c.strip() for c in re.split(r",|\band\b", m.group(2))] if m and m.group(2) else []
    share = 0.6 if re.search(r"smaller|emerging|up-and-coming|newer|local", text, re.I) else 0.92
    # a city is named with a capital; "smaller opener please" after a comma is not one
    cities = [c for c in cities if c and c[0].isupper()]
    return {"headliner": headliner, "cities": cities[:MAX_CITIES], "opener_share": share}


def plan(sentence, transport=None):
    try:
        answer, meta = _structured(PLAN_SYSTEM, sentence, PLAN_SCHEMA, "plan", transport)
        answer["cities"] = [c.strip() for c in answer.get("cities", []) if c.strip()][:MAX_CITIES]
        return answer, dict(meta, planner="model")
    except Exception as error:  # any failure: the patterns answer, and the result says so
        return plan_with_patterns(sentence), {"planner": "patterns", "why": type(error).__name__}


# ---- 2. the advice -----------------------------------------------------------------------------

def advice_schema(names):
    return {
        "type": "object",
        "properties": {"recommendations": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
            "type": "object",
            "properties": {"about": {"type": "string", "enum": sorted(set(names))},
                           "why": {"type": "string", "maxLength": 240}},
            "required": ["about", "why"], "additionalProperties": False}}},
        "required": ["recommendations"],
        "additionalProperties": False,
    }


ADVISE_SYSTEM = """You are a tour-advance assistant writing for a promoter. You are given a brief built from Qloo's
taste graph: places, openers, after-show spots and brands, each with an affinity score. Write up to three
recommendations, each about one entity from the brief, saying in one sentence why, using only the brief's
facts (affinity, which section it is in). Do not mention anything that is not in the brief."""


def advise(brief_dict, transport=None):
    names = [line["name"] for s in brief_dict["sections"] for line in s["lines"]]
    if not names:
        return [], {"adviser": "none", "why": "empty brief"}
    try:
        answer, meta = _structured(ADVISE_SYSTEM, json.dumps(brief_dict), advice_schema(names), "advice", transport)
        recs = [r for r in answer.get("recommendations", []) if r.get("about") in names][:3]
        return recs, dict(meta, adviser="model")
    except Exception as error:
        return template_advice(brief_dict), {"adviser": "template", "why": type(error).__name__}


def template_advice(brief_dict):
    out = []
    for s in brief_dict["sections"]:
        if s["lines"]:
            top = s["lines"][0]
            aff = f" (affinity {top['affinity']:.2f})" if top.get("affinity") is not None else ""
            out.append({"about": top["name"], "why": f"Top of '{s['title']}'{aff}."})
    return out[:3]
