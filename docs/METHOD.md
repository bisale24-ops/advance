# How the backtest was run, and where it is weak

**Question.** Given only a headliner, does a method put the support acts that promoters actually booked near the top of its list?

**Data.** 115 tours (2023–2025) from Wikipedia infoboxes, 634 named support acts; 2 tours skipped because Qloo cannot find the headliner, so 113 are scored; 619 of the openers exist in Qloo. Tours and names are in `data/tours.json`.

**Methods, each given only the headliner**
- Taste: Qloo Insights `artist` ranked by affinity to the headliner's audience, no popularity cap (so the cap cannot flatter it), top 100.
- LLM alone: Apertus 70B asked for 100 openers, no Qloo. Same model that plans Advance.
- Genre chart: the most popular artists in the headliner's leading genre tag, no taste signal.

**Result** (found in the top 10 / 25 / 100, of 619)

| | top 10 | top 25 | top 100 | median rank when found |
|---|---|---|---|---|
| Qloo taste | 26 | 48 | 109 | 31 |
| LLM alone | 21 | 32 | 37 | 9 |
| Genre chart | 1 | 4 | 17 | 56 |

Per tour (113 with at least one opener known to Qloo): taste finds at least one real opener in its top 100 in 61 tours, the LLM in 22, the genre chart in 11. Counting openers found per tour, taste beats the LLM in 49 tours, the LLM beats taste in 8, 56 tie (mostly both find none).

**What this does not show**
- Recall is low: 109 of 619 is 17.6%. Most real openers are not in the top 100 of any method, because tours are booked on routing, agents and availability, not only on taste.
- The LLM is better at the very top (median rank 9 against 31): when it knows the tour, it knows it. These tours are on Wikipedia, so any leakage favours the LLM, not Qloo.
- Qloo's candidate list is its own artist universe; the LLM's names were matched to openers by normalised name.
- It measures one thing, the support act. Venue, market and sponsor lines are not backtested, and venue capacity and availability are not in Qloo at all.

**Why 115 and 113.** 115 tours were collected; 2 had a headliner Qloo cannot find (listed in `docs/backtest.json` as skipped), so 113 are scored. Tours were fixed before any result was seen, and no method was tuned on this set: the opener cap, the market filter and the venue categories were changed afterwards for the brief, not for the backtest. There is no separate holdout set, so this is a retrospective test, not a prospective one.

**Reproduce, offline, no key**
```
QLOO_MODE=replay python3 tools/backtest.py data/tours.json docs/backtest.json
LLM_MODE=replay  python3 tools/backtest_llm.py data/tours.json docs/backtest.json
```
