# Advance

**The tour advance, from your audience's taste.** Name a headliner and the cities (or the country); Advance asks
Qloo's taste graph the five questions a promoter answers by gut — where to play, who opens, which room, where fans
go after the show, and which brands share the crowd — and writes the brief, with the evidence behind every line.

Live: https://khlab-advance.onrender.com · Demo video (1:47): https://youtu.be/8nE2Gu9vSbc · Built for the Qloo Agentic Hackathon 2026 by KHLab.

## The problem

Before a show goes on sale, a promoter's advance team decides the routing, the support act, the room, the
after-party partners and the sponsors. Today those calls come from ticket history, a genre chart and whoever the
agent pitches. Ticket history only exists for markets you have already played; a genre chart ranks what is
popular, not what *this* audience loves. The taste of the actual fans is the missing input.

## What it does

| The question | What Advance asks Qloo | Example: Phoebe Bridgers in Chicago |
|---|---|---|
| Where to play | destinations over-indexing on the headliner's audience, inside one country when named | Portland, Salem, New Haven, Boston |
| Who opens | artists the same audience loves, capped below the headliner's popularity | Christian Lee Hutson, Matt Berninger, Tomberlin |
| Which room | concert halls, live music venues, arenas in the city, ranked by this audience | Rockefeller Memorial Chapel, The Chicago Theatre, Constellation |
| After the show | bars, cocktail bars and clubs in the city (hotels and campgrounds excluded) | WNDR Museum, Thalia Hall, Cerise Rooftop |
| Who sponsors | brands with audience affinity | Fender, Dr. Martens, Gibson |

The agent: a language model (Apertus 70B) turns the sentence into a plan — headliner, up to three cities, the
country, how small an opener may be — through a JSON schema; Qloo answers each question; the model then writes up
to three recommendations from a schema whose only allowed names are the ones Qloo returned, so it **cannot
recommend anything that is not in the brief**. If the model is down, a pattern planner and a template take over,
and the page says which step answered.

## Does Qloo's taste find the acts promoters actually booked?

We took **115 real tours (2023–2025)** with their support acts from Wikipedia (`data/tours.json`), gave Advance only
the headliner, and looked up where each real opener lands — against a genre chart: the most popular artists of the
headliner's own genre, which is what a booker without taste data would use.

| Of 619 real openers Qloo knows | Taste list (Advance) | Genre chart |
|---|---|---|
| in the top 10 | **26** | 1 |
| in the top 25 | **48** | 4 |
| in the top 100 | **109** | 17 |
| median rank when found | 31 | 56 |

Taste finds **6× more of the acts promoters really booked** than the genre chart. Examples it ranks first or second:
Sleeping with Sirens for Pierce the Veil, Modest Mouse for Weezer, Wild Rivers and Maisie Peters for Noah Kahan,
Isabel LaRosa for Nessa Barrett, Keyshia Cole for Brandy. It is not an oracle — 82% of real openers are outside its
top 100, because tours also book label-mates, friends and local acts — but it is the right list to start from.

```bash
QLOO_MODE=replay python3 tools/backtest.py data/tours.json docs/backtest.json   # same numbers, offline
```

## What it does not do

- It does not know ticket prices, venue capacity, availability or fees: it ranks by audience taste, and the
  promoter checks the room is free and the right size.
- Qloo's place data is global but uneven; in small cities a section can come back short, and the page says so
  instead of filling it.
- It does not contact anyone or book anything.

## Things we learnt about the Qloo API (each guarded by a test)

- `take` above 50 is a 400; Advance pages (`Qloo.top`).
- `/search` names a genre `urn:tag:genre:pop_rock`; `/v2/insights` only honours `urn:tag:genre:music:pop_rock`
  and answers the first with an empty 200.
- Place insights without a category filter return airports and skyscrapers; the `bar` category also tags hotel
  lobbies, so after-show excludes lodging with `filter.exclude.tags`.
- Unknown parameters are ignored silently, so the client refuses any parameter not on the per-type allow-list
  instead of sending it.

## Running it

```bash
./run.sh "Phoebe Bridgers in Chicago and Denver"     # the brief in a terminal
PYTHONPATH=src python3 -m advance.web                 # the page on http://127.0.0.1:8790
```

Needs `QLOO_API_KEY` (or `~/.config/qloo.key`); the planner uses `PUBLICAI_API_KEY` (Apertus via Public AI) or
`GEMINI_API_KEY` when set, and works without either. Python standard library only. `QLOO_MODE=replay` answers
from the recorded responses in `fixtures/qloo` with no key and no network.

## How it was checked

`./check.sh` runs 31 tests on Python 3.9 and 3.13 plus the recorded demo end to end; CI runs the same on every
push. The backtest replays from the recorded Qloo responses and reproduces the table above exactly.

## Licence

MIT. Built on Qloo's Taste AI™ API.
