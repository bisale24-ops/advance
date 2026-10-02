"""Qloo's taste graph over the standard library: search, insights, heatmaps — and the one trap that matters.

The hackathon key works only against https://hackathon.api.qloo.com and goes in an `X-Api-Key`
header. The trap: a parameter Qloo does not accept for the requested entity type is ignored
silently, and the answer is `200 OK` with an empty list — indistinguishable from "no taste data".
So every call here is checked against the parameters the docs list per type before it leaves,
and an empty answer comes back as `Empty`, carrying the request that produced it, never as `[]`.

    q = Qloo.from_env()
    artist = q.find("Phoebe Bridgers", "artist")
    for e in q.insights("artist", entities=[artist.id], take=10).entities:
        print(e.name, e.affinity)

Calls are cached on disk by request, so a demo replays without the network (`QLOO_MODE=replay`).
"""
import dataclasses
import hashlib
import json
import os
import pathlib
import time
import typing
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("QLOO_BASE_URL", "https://hackathon.api.qloo.com")
CACHE = pathlib.Path(os.environ.get("QLOO_CACHE", pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "qloo"))
MODES = ("live", "cache", "replay")

TYPES = {
    "artist": "urn:entity:artist",
    "place": "urn:entity:place",
    "brand": "urn:entity:brand",
    "destination": "urn:entity:destination",
    "locality": "urn:entity:locality",
    "heatmap": "urn:heatmap",
}

# Parameters Qloo honours per filter.type (docs: "Entity Type Parameter Guide"). Anything else is
# dropped silently by the API, so it is refused here instead.
COMMON = {"signal.interests.entities", "signal.interests.tags", "signal.demographics.age",
          "signal.demographics.gender", "signal.demographics.audiences", "filter.popularity.min",
          "filter.popularity.max", "filter.tags", "filter.exclude.tags", "bias.trends", "take", "offset",
          "page", "feature.explainability"}
LOCATION = {"filter.location", "filter.location.query", "filter.location.radius", "filter.geocode.name",
            "filter.geocode.admin1_region", "filter.geocode.admin2_region", "filter.geocode.country_code",
            "signal.location", "signal.location.query", "signal.location.radius"}
ALLOWED = {
    "artist": COMMON | {"filter.exclude.entities"},
    "brand": COMMON | {"filter.exclude.entities"},
    "place": COMMON | LOCATION | {"filter.price_level.min", "filter.price_level.max", "bias.quality", "sort_by",
                                  "filter.exclude.entities"},
    "destination": COMMON | LOCATION,
    "locality": {"signal.interests.entities", "take", "offset", "page"},
    "heatmap": {"signal.interests.entities", "signal.interests.tags", "signal.demographics.age",
                "signal.demographics.gender", "signal.demographics.audiences", "bias.trends",
                "filter.location", "filter.location.query", "output.heatmap.boundary"},
}
REQUIRED = {"destination": "signal.interests.entities",
            "heatmap": ("filter.location", "filter.location.query")}


class QlooError(RuntimeError):
    """A call that failed: no key, a refused parameter, an HTTP error after retries."""


class Empty(QlooError):
    """Qloo answered 200 with nothing. Carries the request, because that is where the cause is."""

    def __init__(self, path, params):
        self.path, self.params = path, dict(params)
        super().__init__(f"Qloo returned no results for {path} {json.dumps(self.params, sort_keys=True)}")


@dataclasses.dataclass(frozen=True)
class Entity:
    id: str
    name: str
    subtype: str = ""
    popularity: typing.Optional[float] = None
    affinity: typing.Optional[float] = None
    tags: typing.Tuple[str, ...] = ()
    location: typing.Optional[dict] = None
    raw: typing.Optional[dict] = dataclasses.field(default=None, compare=False, repr=False)

    @classmethod
    def of(cls, item):
        query = item.get("query") or {}
        props = item.get("properties") or {}
        return cls(
            id=item.get("entity_id") or item.get("id") or "",
            name=item.get("name") or "",
            subtype=item.get("subtype") or "",
            popularity=item.get("popularity"),
            affinity=query.get("affinity"),
            tags=tuple(str(t.get("name") or t.get("id")) for t in item.get("tags") or () if isinstance(t, dict)),
            location=item.get("location") or props.get("geocode"),
            raw=item,
        )


@dataclasses.dataclass(frozen=True)
class Answer:
    entities: typing.Tuple[Entity, ...] = ()
    heatmap: typing.Tuple[dict, ...] = ()
    request: typing.Optional[dict] = None
    cached: bool = False


def read_key():
    key = os.environ.get("QLOO_API_KEY", "").strip()
    if key:
        return key
    path = pathlib.Path.home() / ".config" / "qloo.key"
    try:
        key = path.read_text().strip()
    except OSError:
        raise QlooError(f"no Qloo key: set QLOO_API_KEY or write it to {path}") from None
    if not key:
        raise QlooError(f"{path} is empty")
    return key


def _get(url, headers, timeout):
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https base
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except urllib.error.URLError as error:
        return 0, str(error.reason).encode()


class Qloo:
    def __init__(self, key=None, mode=None, cache=None, transport=None, sleep=time.sleep, timeout=30):
        self.key = key
        self.mode = mode or os.environ.get("QLOO_MODE", "cache")
        if self.mode not in MODES:
            raise QlooError(f"unknown QLOO_MODE {self.mode!r}, expected one of {', '.join(MODES)}")
        self.cache = pathlib.Path(cache) if cache is not None else CACHE
        self.transport = transport or _get
        self.sleep = sleep
        self.timeout = timeout
        self.calls = 0  # requests that actually left the machine

    @classmethod
    def from_env(cls, **kwargs):
        mode = kwargs.get("mode") or os.environ.get("QLOO_MODE", "cache")
        if mode != "replay":
            kwargs.setdefault("key", read_key())
        return cls(**kwargs)

    # ---- transport, cache ----

    def _slot(self, path, params):
        stamp = json.dumps([path, sorted(params.items())], sort_keys=True)
        return self.cache / (hashlib.sha256(stamp.encode()).hexdigest()[:20] + ".json")

    def get(self, path, params, attempts=4):
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        slot = self._slot(path, params)
        if self.mode in ("cache", "replay") and slot.exists():
            return json.loads(slot.read_text())["response"], True
        if self.mode == "replay":
            raise QlooError(f"replay mode and no recording for {path} {params}")
        if not self.key:
            raise QlooError("no Qloo key")
        url = BASE + path + "?" + urllib.parse.urlencode(params, doseq=False)
        headers = {"X-Api-Key": self.key, "Accept": "application/json",
                   "User-Agent": "advance/0.1 (+https://github.com/bisale24-ops)"}
        last = ""
        for attempt in range(attempts):
            status, body = self.transport(url, headers, self.timeout)
            self.calls += 1
            if status == 200:
                data = json.loads(body)
                if self.mode == "cache":
                    slot.parent.mkdir(parents=True, exist_ok=True)
                    slot.write_text(json.dumps({"path": path, "params": params, "response": data}, indent=1))
                return data, False
            last = f"{status} {body[:200]!r}"
            if status in (400, 401, 403, 404):
                break  # the request is wrong, not the moment
            self.sleep(min(8, 0.5 * 2 ** attempt))
        raise QlooError(f"Qloo {path} failed: {last}")

    # ---- the endpoints ----

    def search(self, query, kind="artist", take=5):
        data, _cached = self.get("/search", {"query": query, "types": TYPES[kind], "take": take})
        items = data.get("results") or []
        return tuple(Entity.of(item) for item in items)

    def find(self, name, kind="artist"):
        """The best match for a name, preferring an exact (case-folded) name over the first hit."""
        hits = self.search(name, kind, take=5)
        if not hits:
            raise Empty("/search", {"query": name, "types": TYPES[kind]})
        exact = [h for h in hits if h.name.casefold() == name.casefold()]
        return (exact or list(hits))[0]

    def insights(self, kind, entities=(), tags=(), **params):
        """GET /v2/insights for one filter.type, with parameters checked against what Qloo honours."""
        if kind not in ALLOWED:
            raise QlooError(f"unsupported type {kind!r}")
        query = {"filter.type": TYPES[kind]}
        if entities:
            query["signal.interests.entities"] = ",".join(entities)
        if tags:
            query["signal.interests.tags"] = ",".join(tags)
        for name, value in params.items():
            key = name.replace("__", ".")
            if key not in ALLOWED[kind]:
                raise QlooError(f"{key} is not a parameter Qloo honours for {kind}; it would be ignored silently")
            query[key] = ",".join(value) if isinstance(value, (list, tuple)) else value
        need = REQUIRED.get(kind)
        if need and not any(n in query for n in ((need,) if isinstance(need, str) else need)):
            raise QlooError(f"{kind} insights need {need}")
        data, cached = self.get("/v2/insights", query)
        results = data.get("results") or {}
        answer = Answer(
            entities=tuple(Entity.of(e) for e in results.get("entities") or ()),
            heatmap=tuple(results.get("heatmap") or ()),
            request=query,
            cached=cached,
        )
        if not answer.entities and not answer.heatmap:
            raise Empty("/v2/insights", query)
        return answer
