"""The brief, built on a stub taste graph: what each section asks Qloo, and what it does with silence."""
from advance import brief
from advance.qloo import Empty, Entity, Answer

HEAD = Entity("H", "Phoebe Bridgers", "urn:entity:artist", popularity=0.9)


class Stub:
    def __init__(self, by_kind):
        self.by_kind, self.asked = by_kind, []

    def find(self, name, kind="artist"):
        return HEAD

    def insights(self, kind, entities=(), tags=(), **params):
        self.asked.append((kind, tuple(entities), params))
        got = self.by_kind.get(kind)
        if got is None:
            raise Empty("/v2/insights", {"filter.type": kind})
        return Answer(entities=tuple(got), request={"filter.type": kind, **params})


def e(name, aff, pop=0.5):
    return Entity(name.lower(), name, popularity=pop, affinity=aff)


def test_openers_are_capped_below_the_headliner_and_exclude_it():
    stub = Stub({"artist": [HEAD, e("Julien Baker", 0.95, 0.6), e("Lucy Dacus", 0.94, 0.62)]})
    section = brief.who_opens(stub, HEAD, take=5)
    kind, _, params = stub.asked[0]
    assert kind == "artist"
    assert params["filter__popularity__max"] == round(0.9 * brief.OPENER_POPULARITY_SHARE, 4)
    assert params["filter__exclude__entities"] == ["H"]
    assert [line.name for line in section.lines] == ["Julien Baker", "Lucy Dacus"]


def test_silence_from_qloo_becomes_a_stated_gap_with_its_request():
    section = brief.who_sponsors(Stub({}), HEAD)
    assert section.lines == ()
    assert "no taste signal" in section.missing
    assert section.request == {"filter.type": "brand"}


def test_no_city_means_no_places_rather_than_invented_ones():
    stub = Stub({"place": [e("Empty Bottle", 0.9)]})
    section = brief.after_show(stub, HEAD, city=None)
    assert section.lines == () and "Pick a city" in section.missing
    assert stub.asked == []


def test_places_are_asked_for_inside_the_city():
    stub = Stub({"place": [e("Empty Bottle", 0.9)]})
    section = brief.after_show(stub, HEAD, city="Chicago")
    assert stub.asked[0][2] == {"take": brief.TAKE, "filter__location__query": "Chicago"}
    assert section.lines[0].name == "Empty Bottle"


def test_the_whole_brief_has_four_sections_and_renders():
    stub = Stub({"destination": [e("Chicago", 0.9)], "artist": [e("Julien Baker", 0.95)],
                 "place": [e("Empty Bottle", 0.9)], "brand": [e("Patagonia", 0.8)]})
    built = brief.build(stub, "Phoebe Bridgers", city="Chicago")
    assert [s.key for s in built.sections] == ["cities", "openers", "after", "brands"]
    text = brief.render_text(built)
    assert "ADVANCE — Phoebe Bridgers · Chicago" in text and "0.95  Julien Baker" in text
