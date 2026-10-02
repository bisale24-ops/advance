"""The backtest's arithmetic, on a stub graph: ranks, misses, skipped tours, the summary."""
import importlib.util
import pathlib

from advance.qloo import Answer, Empty, Entity

SPEC = importlib.util.spec_from_file_location("backtest", pathlib.Path(__file__).resolve().parent.parent / "tools" / "backtest.py")
backtest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backtest)

HEAD = Entity("H", "Olivia Rodrigo", raw={"tags": [{"id": "urn:tag:genre:music:pop", "type": "urn:tag:genre:music"}]})
ARTISTS = {n: Entity(n.lower(), n) for n in ("Chappell Roan", "The Breeders", "Remi Wolf", "Unknown Act")}


class Stub:
    def find(self, name, kind="artist"):
        if name == "Olivia Rodrigo":
            return HEAD
        if name in ARTISTS and name != "Unknown Act":
            return ARTISTS[name]
        raise Empty("/search", {"query": name})

    def insights(self, kind, entities=(), tags=(), **params):
        if "filter__tags" in params:      # baseline: genre chart
            return Answer(entities=tuple(Entity(f"p{i}", f"Pop {i}") for i in range(30)) + (ARTISTS["Chappell Roan"],))
        filler = tuple(Entity(f"t{i}", f"Taste {i}") for i in range(4))
        return Answer(entities=(ARTISTS["Chappell Roan"],) + filler + (ARTISTS["Remi Wolf"],))

    def top(self, kind, n, entities=(), tags=(), **params):
        return self.insights(kind, entities, tags, **params).entities[:n]


def test_ranks_misses_and_unknown_acts_are_reported_per_opener():
    row = backtest.one_tour(Stub(), {"tour": "Guts", "headliner": "Olivia Rodrigo",
                                     "support": ["Chappell Roan", "The Breeders", "Remi Wolf", "Unknown Act"]})
    by = {o["name"]: o for o in row["openers"]}
    assert by["Chappell Roan"] == {"name": "Chappell Roan", "found": True, "taste_rank": 1, "baseline_rank": 31}
    assert by["The Breeders"]["taste_rank"] is None
    assert by["Remi Wolf"]["taste_rank"] == 6
    assert by["Unknown Act"] == {"name": "Unknown Act", "found": False}


def test_a_headliner_qloo_cannot_find_is_counted_not_dropped():
    rows = [backtest.one_tour(Stub(), {"tour": "X", "headliner": "Nobody", "support": ["A"]})]
    summary = backtest.summarise(rows)
    assert summary["tours"] == 1 and summary["tours_skipped"] == 1


def test_the_summary_counts_hits_at_each_cut():
    row = backtest.one_tour(Stub(), {"tour": "Guts", "headliner": "Olivia Rodrigo",
                                     "support": ["Chappell Roan", "Remi Wolf", "The Breeders"]})
    s = backtest.summarise([row])
    assert s["taste"] == {"top10": 2, "top25": 2, "top100": 2, "median_rank": 3.5}
    assert s["baseline"] == {"top10": 0, "top25": 0, "top100": 1, "median_rank": 31}


def test_search_genre_tags_are_rewritten_to_the_form_insights_honours():
    head = Entity("h", "Olivia Rodrigo", raw={"tags": [
        {"tag_id": "urn:tag:audience:qloo:loyal", "type": "urn:tag:audience:qloo"},
        {"tag_id": "urn:tag:genre:pop_rock", "type": "urn:tag:genre"}]})
    assert backtest.genre_tag(head) == "urn:tag:genre:music:pop_rock"
    assert backtest.insights_tag("urn:tag:genre:music:rock") == "urn:tag:genre:music:rock"
