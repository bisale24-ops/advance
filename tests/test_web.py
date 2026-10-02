"""The question endpoint end to end, on a stub graph and with no model: patterns plan, template advises."""
from advance import plan, web
from advance.qloo import Answer, Empty, Entity


class Stub:
    calls = 0

    def find(self, name, kind="artist"):
        if name == "Nobody":
            raise Empty("/search", {"query": name})
        return Entity("H", name, popularity=0.8)

    def insights(self, kind, entities=(), tags=(), **params):
        self.calls += 1
        return Answer(entities=(Entity(kind + "1", f"Top {kind}", affinity=0.9),), request={"filter.type": kind})


def test_ask_plans_builds_and_advises_and_says_which_step_ran(monkeypatch):
    monkeypatch.setattr(plan, "endpoint", lambda: None)
    r = web.ask("Mitski in Austin and Dallas, smaller opener", q=Stub())
    assert r["plan"] == {"headliner": "Mitski", "cities": ["Austin", "Dallas"], "opener_share": 0.6}
    assert r["plan_meta"]["planner"] == "patterns" and r["advice_meta"]["adviser"] == "template"
    assert [s["key"] for s in r["brief"]["sections"]] == ["cities", "openers", "after", "after", "brands"]
    assert r["qloo_calls"] == 5
    assert all(a["about"].startswith("Top ") for a in r["advice"])


def test_an_unknown_headliner_is_an_answer_not_a_crash(monkeypatch):
    monkeypatch.setattr(plan, "endpoint", lambda: None)
    r = web.ask("Nobody in Boston", q=Stub())
    assert "does not know an artist" in r["error"]
