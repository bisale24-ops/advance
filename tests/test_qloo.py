"""The Qloo client, tested on a fake transport: no key, no network."""
import json

import pytest

from advance import qloo


def entity(name, eid, popularity=0.5, affinity=None):
    item = {"name": name, "entity_id": eid, "subtype": "urn:entity:artist", "popularity": popularity}
    if affinity is not None:
        item["query"] = {"affinity": affinity}
    return item


class Wire:
    """Answers by path; records every URL it was asked for."""

    def __init__(self, answers):
        self.answers, self.urls = answers, []

    def __call__(self, url, headers, timeout):
        self.urls.append(url)
        assert headers["X-Api-Key"] == "k"
        for path, (status, body) in self.answers.items():
            if path in url:
                return status, json.dumps(body).encode()
        return 404, b"{}"


@pytest.fixture
def client(tmp_path):
    def make(answers, mode="cache"):
        wire = Wire(answers)
        return qloo.Qloo(key="k", mode=mode, cache=tmp_path, transport=wire, sleep=lambda s: None), wire
    return make


def test_a_parameter_qloo_would_ignore_is_refused_before_it_leaves(client):
    q, wire = client({})
    with pytest.raises(qloo.QlooError, match="ignored silently"):
        q.insights("artist", entities=["A"], filter__location__query="Chicago")
    assert wire.urls == []


def test_an_empty_answer_is_an_error_that_carries_the_request(client):
    q, _ = client({"/v2/insights": (200, {"success": True, "results": {"entities": []}})})
    with pytest.raises(qloo.Empty) as raised:
        q.insights("artist", entities=["A"], take=5)
    assert raised.value.params["filter.type"] == "urn:entity:artist"
    assert raised.value.params["signal.interests.entities"] == "A"


def test_insights_read_affinity_and_popularity(client):
    body = {"success": True, "results": {"entities": [entity("Boygenius", "B", 0.8, 0.97), entity("Julien Baker", "J", 0.6, 0.93)]}}
    q, wire = client({"/v2/insights": (200, body)})
    answer = q.insights("artist", entities=["P"], take=2, filter__popularity__max=0.9)
    assert [(e.name, e.affinity, e.popularity) for e in answer.entities] == [("Boygenius", 0.97, 0.8), ("Julien Baker", 0.93, 0.6)]
    assert "filter.popularity.max=0.9" in wire.urls[0] and "filter.type=urn%3Aentity%3Aartist" in wire.urls[0]


def test_a_second_identical_call_comes_from_the_cache_and_replays_offline(client, tmp_path):
    body = {"success": True, "results": {"entities": [entity("X", "X")]}}
    q, wire = client({"/v2/insights": (200, body)})
    q.insights("brand", entities=["P"])
    q.insights("brand", entities=["P"])
    assert len(wire.urls) == 1 and q.calls == 1
    offline = qloo.Qloo(mode="replay", cache=tmp_path, transport=lambda *a: pytest.fail("network in replay"))
    assert offline.insights("brand", entities=["P"]).entities[0].name == "X"


def test_replay_without_a_recording_says_so(tmp_path):
    offline = qloo.Qloo(mode="replay", cache=tmp_path)
    with pytest.raises(qloo.QlooError, match="no recording"):
        offline.search("Nobody")


def test_find_prefers_the_exact_name(client):
    hits = {"success": True, "results": [entity("Phoebe Bridgers Tribute", "T"), entity("Phoebe Bridgers", "P")]}
    q, _ = client({"/search": (200, hits)})
    assert q.find("phoebe bridgers").id == "P"


def test_destinations_need_an_entity_signal_and_heatmaps_a_location(client):
    q, wire = client({})
    with pytest.raises(qloo.QlooError, match="need"):
        q.insights("destination", tags=["urn:tag:genre:music:indie"])
    with pytest.raises(qloo.QlooError, match="need"):
        q.insights("heatmap", entities=["P"])
    assert wire.urls == []


def test_a_wrong_key_is_not_retried(client):
    q, wire = client({"/search": (401, {"message": "No API key found"})})
    with pytest.raises(qloo.QlooError, match="401"):
        q.search("anyone")
    assert len(wire.urls) == 1


def test_a_server_error_is_retried(client):
    calls = []

    def flaky(url, headers, timeout):
        calls.append(url)
        if len(calls) < 3:
            return 503, b"busy"
        return 200, json.dumps({"results": [entity("A", "A")]}).encode()

    q = qloo.Qloo(key="k", mode="live", transport=flaky, sleep=lambda s: None)
    assert q.search("A")[0].id == "A" and len(calls) == 3


def test_take_over_fifty_is_refused_before_qloo_answers_400():
    q = qloo.Qloo(key="k", mode="live", transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError("no call")))
    with pytest.raises(qloo.QlooError, match="take must be"):
        q.insights("artist", entities=["x"], take=100)


def test_top_pages_through_fifty_at_a_time_and_stops_on_a_short_page():
    pages = []

    class Paged(qloo.Qloo):
        def insights(self, kind, entities=(), tags=(), **params):
            pages.append(params["page"])
            start = (params["page"] - 1) * 50
            size = 50 if params["page"] == 1 else 20
            return qloo.Answer(entities=tuple(qloo.Entity(f"e{start + i}", f"E{start + i}") for i in range(size)))

    got = Paged(key="k", mode="live").top("artist", 120, entities=["x"])
    assert pages == [1, 2] and len(got) == 70 and got[-1].id == "e69"
