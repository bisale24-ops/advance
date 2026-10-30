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
    assert stub.asked[0][2] == {"take": brief.TAKE, "filter__location__query": "Chicago",
                                "filter__tags": brief.AFTER_TAGS, "filter__exclude__tags": brief.NOT_AFTER}
    assert section.lines[0].name == "Empty Bottle"


def test_venues_are_concert_rooms_inside_the_city():
    stub = Stub({"place": [e("Metro", 0.9)]})
    section = brief.which_room(stub, HEAD, city="Chicago")
    assert stub.asked[0][2] == {"take": brief.TAKE, "filter__location__query": "Chicago",
                                "filter__tags": brief.VENUE_TAGS,
                                    "filter__exclude__tags": brief.NOT_VENUE}
    assert section.title == "Which room · Chicago" and section.lines[0].name == "Metro"
    assert brief.which_room(Stub({}), HEAD, city=None).missing.startswith("Pick a city")


def test_the_whole_brief_has_five_sections_and_renders():
    stub = Stub({"destination": [e("Chicago", 0.9)], "artist": [e("Julien Baker", 0.95)],
                 "place": [e("Empty Bottle", 0.9)], "brand": [e("Patagonia", 0.8)]})
    built = brief.build(stub, "Phoebe Bridgers", city="Chicago")
    assert [s.key for s in built.sections] == ["cities", "openers", "venue", "booked", "after", "brands"]
    text = brief.render_text(built)
    assert "ADVANCE — Phoebe Bridgers · Chicago" in text and "0.95  Julien Baker" in text


def test_a_place_line_carries_its_address_website_and_room_feel():
    from advance.qloo import Entity
    raw = {"properties": {"address": "3317 E Colfax Ave Denver, CO", "website": "http://bluebirdtheater.net", "phone": "+13033771666",
                          "keywords": [{"name": "parking", "count": 90}, {"name": "intimate venue", "count": 102}]}}
    line = brief._lines([Entity("b", "Bluebird Theater", raw=raw)], brief.place_note)[0]
    assert line.link == "http://bluebirdtheater.net" and line.phone == "+13033771666"
    assert line.note == "3317 E Colfax Ave Denver, CO · intimate venue"


def test_rooms_that_stand_out_for_this_act_come_before_rooms_every_act_likes():
    generic, special = e("Good Hall", 0.90), e("Indie Club", 0.88)
    generic = type(generic)(id="g", name="Good Hall", affinity=0.90)
    special = type(generic)(id="s", name="Indie Club", affinity=0.88)
    panel = [{"g": 0.90, "s": 0.60}, {"g": 0.88, "s": 0.55}]
    ranked, lift = brief.stands_out([generic, special], panel, 2)
    assert [r.name for r in ranked] == ["Indie Club", "Good Hall"]
    assert round(lift["s"], 3) == 0.305 and round(lift["g"], 3) == 0.01
    # Qloo's own score is untouched and no panel means no change
    assert ranked[0].affinity == 0.88
    assert [r.name for r in brief.stands_out([generic, special], [], 2)[0]] == ["Good Hall", "Indie Club"]


def test_most_booked_rooms_are_asked_for_with_no_artist_signal():
    stub = Stub({"place": [e("United Center", 0.0)]})
    section = brief.booked_rooms(stub, HEAD, "Chicago")
    kind, entities, params = stub.asked[0]
    assert kind == "place" and entities == () and params["filter__location__query"] == "Chicago"
    assert section.key == "booked" and section.title == "Most-booked rooms · Chicago"
    assert brief.booked_rooms(stub, HEAD, None) is None
