"""The tour-advance brief: five decisions a promoter makes, each answered from Qloo's taste graph.

    brief = build(Qloo.from_env(), "Phoebe Bridgers", city="Chicago")
    print(render_text(brief))

Every line carries its evidence: the entity, Qloo's affinity for it, and the request that
produced it, so a reader can re-run any single claim. A section Qloo could not answer says so
and keeps the request — an empty taste signal is information, not a reason to guess.
"""
import dataclasses
import typing

from . import route
from .qloo import Empty, Entity, QlooError

OPENER_POPULARITY_SHARE = 0.92   # an opener draws less than the headliner: cap at this share of its popularity
TAKE = 8
MARKET_POPULARITY_FLOOR = 0.75   # a tour books markets that draw a room: skip towns Qloo scores as tiny
MARKET_POOL = 6                  # ask for this many times TAKE, then keep the bookable ones
# Qloo place categories (comma = any of). Without them "where fans go" returns airports and skyscrapers.
VENUE_TAGS = ("urn:tag:category:place:live_music_venue", "urn:tag:category:place:concert_hall",
              "urn:tag:category:place:arena", "urn:tag:category:place:stadium")
AFTER_TAGS = ("urn:tag:category:place:bar", "urn:tag:category:place:cocktail_bar",
              "urn:tag:category:place:night_club")
# a hotel lobby bar or a campground snack bar carries the bar tag too (checked live, 3 Oct 2026)
NOT_AFTER = ("urn:tag:category:place:hotel", "urn:tag:category:place:bed_breakfast",
             "urn:tag:category:place:campground", "urn:tag:category:place:motel", "urn:tag:category:place:hostel",
             # a gallery or a landmark that also pours drinks is not where a touring crew goes (checked live, 31 Oct 2026)
             "urn:tag:category:place:art_museum", "urn:tag:category:place:tourist_attraction")
# a chapel or a church hall tagged as a performing-arts theatre is not a room a promoter can book
NOT_VENUE = ("urn:tag:category:place:chapel",)


@dataclasses.dataclass(frozen=True)
class Line:
    name: str
    affinity: typing.Optional[float]
    popularity: typing.Optional[float]
    entity_id: str
    note: str = ""
    lat: typing.Optional[float] = None
    lon: typing.Optional[float] = None


@dataclasses.dataclass(frozen=True)
class Section:
    key: str
    title: str
    question: str
    lines: typing.Tuple[Line, ...] = ()
    request: typing.Optional[dict] = None
    missing: str = ""        # why there are no lines, when there are none


@dataclasses.dataclass(frozen=True)
class Brief:
    headliner: Entity
    city: typing.Optional[str]
    sections: typing.Tuple[Section, ...]
    route: typing.Optional[dict] = None     # the cities ordered into a tour, see route.py

    def section(self, key):
        return next(s for s in self.sections if s.key == key)

    def to_dict(self):
        return {
            "headliner": {"name": self.headliner.name, "id": self.headliner.id,
                          "popularity": self.headliner.popularity},
            "cities": [c for c in (self.city or "").split(" · ") if c],
            "sections": [{"key": s.key, "title": s.title, "question": s.question, "missing": s.missing,
                          "request": s.request,
                          "lines": [dataclasses.asdict(line) for line in s.lines]} for s in self.sections],
            "route": self.route,
        }


def _lines(entities, note=lambda e: ""):
    def r(x):
        return round(x, 3) if x is not None else None
    def at(e, key):
        return (e.location or {}).get(key)
    return tuple(Line(e.name, r(e.affinity), r(e.popularity), e.id, note(e), at(e, "lat"), at(e, "lon")) for e in entities)


def _with_region(e):
    """'Portland' alone is Maine or Oregon: name the state or region Qloo returns with the destination."""
    geo = ((e.raw or {}).get("properties") or {}).get("geocode") or {}
    region = geo.get("admin1_region")
    if region and region != e.name:
        return dataclasses.replace(e, name=f"{e.name}, {region}")
    return e


def _ask(key, title, question, call):
    """Run one Qloo call; turn a refusal or an empty answer into a section that says what happened."""
    try:
        answer = call()
    except Empty as empty:
        return Section(key, title, question, request=empty.params,
                       missing="Qloo has no taste signal for this request.")
    except QlooError as error:
        return Section(key, title, question, missing=f"Qloo could not answer: {error}")
    return key, title, question, answer


def where_to_play(q, headliner, take=TAKE, market=None):
    """Destinations whose audience over-indexes on the headliner; `market` (ISO country code) keeps the
    routing inside one country, which is how tours are booked."""
    where = f" in {market}" if market else ""
    extra = {"filter__geocode__country_code": market} if market else {}
    got = _ask("cities", "Where to play" + (f" · {market}" if market else ""),
               f"Which places{where} over-index on {headliner.name}'s audience?",
               lambda: q.insights("destination", entities=[headliner.id], take=take * MARKET_POOL, **extra))
    if isinstance(got, Section):
        return got
    key, title, question, answer = got
    big = [e for e in answer.entities if (e.popularity or 0) >= MARKET_POPULARITY_FLOOR]
    picks = (big if len(big) >= take else list(answer.entities))[:take]
    return Section(key, title, question, _lines([_with_region(e) for e in picks]), answer.request)


def who_opens(q, headliner, take=TAKE, share=OPENER_POPULARITY_SHARE):
    """Artists the same audience likes, who draw less than the headliner — that is what an opener is."""
    cap = None
    if headliner.popularity is not None:
        cap = round(max(0.0, min(1.0, headliner.popularity * share)), 4)
    got = _ask("openers", "Who opens", f"Who does {headliner.name}'s audience also love, a step smaller?",
               lambda: q.insights("artist", entities=[headliner.id], take=take + 2,
                                  filter__popularity__max=cap,
                                  filter__exclude__entities=[headliner.id]))
    if isinstance(got, Section):
        return got
    key, title, question, answer = got
    picks = [e for e in answer.entities if e.id != headliner.id][:take]
    return Section(key, title, question, _lines(picks), answer.request)


def after_show(q, headliner, city, take=TAKE):
    if not city:
        return Section("after", "After the show", "Where do the same fans go afterwards?",
                       missing="Pick a city to see places near the venue.")
    got = _ask("after", f"After the show · {city}", f"Where do {headliner.name}'s fans go in {city}?",
               lambda: q.insights("place", entities=[headliner.id], take=take, filter__location__query=city,
                                  filter__tags=AFTER_TAGS, filter__exclude__tags=NOT_AFTER))
    if isinstance(got, Section):
        return got
    key, title, question, answer = got
    return Section(key, title, question, _lines(answer.entities), answer.request)


def which_room(q, headliner, city, take=TAKE):
    """Concert rooms in the city ranked by the headliner's audience: the venue shortlist."""
    if not city:
        return Section("venue", "Which room", "Which venues does this audience favour?",
                       missing="Pick a city to see its venues.")
    got = _ask("venue", f"Which room · {city}", f"Which {city} venues do {headliner.name}'s fans favour?",
               lambda: q.insights("place", entities=[headliner.id], take=take, filter__location__query=city,
                                  filter__tags=VENUE_TAGS, filter__exclude__tags=NOT_VENUE))
    if isinstance(got, Section):
        return got
    key, title, question, answer = got
    return Section(key, title, question, _lines(answer.entities), answer.request)


def who_sponsors(q, headliner, take=TAKE):
    got = _ask("brands", "Who sponsors", f"Which brands share {headliner.name}'s audience?",
               lambda: q.insights("brand", entities=[headliner.id], take=take))
    if isinstance(got, Section):
        return got
    key, title, question, answer = got
    return Section(key, title, question, _lines(answer.entities), answer.request)


def build(q, headliner_name, city=None, take=TAKE, cities=None, share=OPENER_POPULARITY_SHARE, market=None):
    """The five questions. `cities` asks the venue and after-show questions once per city (`city` is one)."""
    headliner = q.find(headliner_name, "artist")
    cities = [c for c in (cities if cities is not None else [city]) if c]
    afters = [s for c in cities for s in (which_room(q, headliner, c, take), after_show(q, headliner, c, take))] \
        or [after_show(q, headliner, None, take)]
    where = where_to_play(q, headliner, take, market)
    return Brief(headliner, " · ".join(cities) or None, (
        where,
        who_opens(q, headliner, take, share),
        *afters,
        who_sponsors(q, headliner, take),
    ), tour_route(q, cities, where, market))


def tour_route(q, cities, where, market):
    """The typed cities first, then Qloo's best markets, joined into the shortest path."""
    named = []
    for c in cities:
        try:
            hit = q.find(c, "destination")
        except (Empty, QlooError):
            continue
        loc = hit.location or {}
        if loc.get("lat") is not None and loc.get("lon") is not None:
            named.append({"name": c, "lat": loc["lat"], "lon": loc["lon"]})
    markets = [{"name": l.name, "lat": l.lat, "lon": l.lon} for l in where.lines if l.lat is not None and l.lon is not None]
    return route.plan(named, markets, unit="mi" if market in (None, "", "US") else "km")


def render_text(brief):
    out = [f"ADVANCE — {brief.headliner.name}" + (f" · {brief.city}" if brief.city else ""), ""]
    for s in brief.sections:
        out.append(f"{s.title.upper()}  ({s.question})")
        if not s.lines:
            out.append(f"  — {s.missing}")
        for line in s.lines:
            aff = f"{line.affinity:.2f}" if line.affinity is not None else " n/a"
            out.append(f"  {aff}  {line.name}")
        out.append("")
    return "\n".join(out)
