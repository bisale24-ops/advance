"""The tour-advance brief: four decisions a promoter makes, each answered from Qloo's taste graph.

    brief = build(Qloo.from_env(), "Phoebe Bridgers", city="Chicago")
    print(render_text(brief))

Every line carries its evidence: the entity, Qloo's affinity for it, and the request that
produced it, so a reader can re-run any single claim. A section Qloo could not answer says so
and keeps the request — an empty taste signal is information, not a reason to guess.
"""
import dataclasses
import typing

from .qloo import Empty, Entity, QlooError

OPENER_POPULARITY_SHARE = 0.92   # an opener draws less than the headliner: cap at this share of its popularity
TAKE = 8


@dataclasses.dataclass(frozen=True)
class Line:
    name: str
    affinity: typing.Optional[float]
    popularity: typing.Optional[float]
    entity_id: str
    note: str = ""


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
        }


def _lines(entities, note=lambda e: ""):
    return tuple(Line(e.name, e.affinity, e.popularity, e.id, note(e)) for e in entities)


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


def where_to_play(q, headliner, take=TAKE):
    got = _ask("cities", "Where to play", f"Which places over-index on {headliner.name}'s audience?",
               lambda: q.insights("destination", entities=[headliner.id], take=take))
    if isinstance(got, Section):
        return got
    key, title, question, answer = got
    return Section(key, title, question, _lines(answer.entities), answer.request)


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
               lambda: q.insights("place", entities=[headliner.id], take=take, filter__location__query=city))
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


def build(q, headliner_name, city=None, take=TAKE, cities=None, share=OPENER_POPULARITY_SHARE):
    """The four questions. `cities` asks the after-show question once per city (`city` is one)."""
    headliner = q.find(headliner_name, "artist")
    cities = [c for c in (cities if cities is not None else [city]) if c]
    afters = [after_show(q, headliner, c, take) for c in cities] or [after_show(q, headliner, None, take)]
    return Brief(headliner, " · ".join(cities) or None, (
        where_to_play(q, headliner, take),
        who_opens(q, headliner, take, share),
        *afters,
        who_sponsors(q, headliner, take),
    ))


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
