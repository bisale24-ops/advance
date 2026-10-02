"""The agent's two schema-constrained steps and their fallbacks, without a network."""
import io
import json

from advance import plan

BRIEF = {"sections": [
    {"key": "openers", "title": "Who opens", "lines": [{"name": "Julien Baker", "affinity": 0.95}]},
    {"key": "brands", "title": "Who sponsors", "lines": [{"name": "Patagonia", "affinity": 0.8}]},
    {"key": "after", "title": "After the show", "lines": []},
]}


def fake_model(content):
    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

    def transport(request, timeout):
        transport.body = json.loads(request.data)
        return Response(json.dumps({"choices": [{"message": {"content": json.dumps(content)}}]}).encode())
    return transport


def test_patterns_read_headliner_cities_and_a_smaller_opener():
    got = plan.plan_with_patterns("Phoebe Bridgers in Chicago and Denver, smaller opener please")
    assert got["headliner"] == "Phoebe Bridgers"
    assert got["cities"] == ["Chicago", "Denver"]
    assert got["opener_share"] == 0.6


def test_the_advice_schema_lists_only_names_from_the_brief():
    schema = plan.advice_schema(["Julien Baker", "Patagonia"])
    assert schema["properties"]["recommendations"]["items"]["properties"]["about"]["enum"] == ["Julien Baker", "Patagonia"]


def test_a_name_the_brief_does_not_contain_is_dropped_even_if_a_provider_ignores_the_schema(monkeypatch):
    monkeypatch.setattr(plan, "endpoint", lambda: {"url": "https://x.test", "model": "m", "key": "k"})
    transport = fake_model({"recommendations": [{"about": "Taylor Swift", "why": "invented"},
                                                {"about": "Julien Baker", "why": "affinity 0.95"}]})
    recs, meta = plan.advise(BRIEF, transport=transport)
    assert [r["about"] for r in recs] == ["Julien Baker"] and meta["adviser"] == "model"
    assert transport.body["response_format"]["json_schema"]["strict"] is True


def test_without_a_model_the_template_advises_and_says_so(monkeypatch):
    monkeypatch.setattr(plan, "endpoint", lambda: None)
    recs, meta = plan.advise(BRIEF)
    assert meta["adviser"] == "template"
    assert recs[0] == {"about": "Julien Baker", "why": "Top of 'Who opens' (affinity 0.95)."}


def test_the_model_plan_is_trimmed_to_three_cities(monkeypatch):
    monkeypatch.setattr(plan, "endpoint", lambda: {"url": "https://x.test", "model": "m", "key": "k"})
    got, meta = plan.plan("x", transport=fake_model({"headliner": "Mitski", "cities": ["A", " ", "B", "C", "D"], "opener_share": 0.9}))
    assert got["cities"] == ["A", "B", "C"] and meta["planner"] == "model"
