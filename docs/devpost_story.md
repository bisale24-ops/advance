## Inspiration

Before a show goes on sale, a promoter's advance team makes five calls: where to play, who opens, which room, where the after-party is, and who sponsors. Today those come from ticket history (which only exists where you have already played) and a genre chart (which ranks what is popular, not what *this* audience loves). The taste of the actual fans is the missing input — and that is exactly what Qloo's graph holds.

## What it does

Type one sentence — *"Phoebe Bridgers in Chicago and Denver"*, *"Metallica in Berlin and Munich, Germany"*. Advance returns a booking brief:

- **Where to play** — destinations whose audience over-indexes on the headliner, kept inside one country when you name it;
- **Who opens** — artists the same audience loves, capped below the headliner's popularity;
- **Which room** — concert halls, live music venues and arenas in each city, ranked by this audience;
- **After the show** — bars, cocktail bars and clubs the fans pick (hotel lobbies excluded);
- **Who sponsors** — brands with audience affinity.

Every line shows Qloo's affinity score and the exact request behind it, and three "advance notes" summarise the brief.

## How we built it

An agent with three steps, each labelled on the page:

1. **Plan** — Apertus 70B (Swiss open model via Public AI) fills a JSON schema: headliner, up to three cities, country, how small an opener may be.
2. **Ask Qloo** — one `/v2/insights` call per question, through a client that refuses any parameter not on a per-entity-type allow-list (Qloo ignores unknown parameters silently, and a silently ignored filter is a wrong answer that looks right).
3. **Advise** — the model writes up to three recommendations from a schema whose `enum` contains only names Qloo returned, so **it cannot recommend anything that is not in the brief**.

If the model is unavailable, a pattern planner and a template take over and the page says so. Python standard library only; deployed on Render.

## Does taste beat an LLM? We measured it

We took **115 real tours (2023–2025)** with their support acts from Wikipedia, gave each method only the headliner, and checked where each of the **619 real openers** lands in a 100-long list:

| Real openers found | Qloo taste (Advance) | LLM alone (Apertus 70B) | Genre chart |
|---|---|---|---|
| in the top 10 | **26** | 21 | 1 |
| in the top 25 | **48** | 32 | 4 |
| in the top 100 | **109** | 37 | 17 |

The LLM has *read about* these tours — they are on Wikipedia — so the comparison favours it, and it is good at the very top. Past the obvious names it runs out; taste keeps finding them: **3× the LLM and 6× the genre chart** in the top 100. Taste ranks Sleeping with Sirens first for Pierce the Veil, Modest Mouse first for Weezer, Wild Rivers first for Noah Kahan. Every Qloo and model response is recorded, so the whole backtest replays offline from the repo.

## Challenges we ran into

Four places where the API fails silently, each now guarded by a test:

- `take` above 50 is a 400 → Advance pages with `page`.
- `/search` names a genre `urn:tag:genre:pop_rock`, but `/v2/insights` only honours `urn:tag:genre:music:pop_rock` — the first returns an empty 200 (our genre baseline scored zero until we found it).
- Place insights without a category return airports and skyscrapers → venue and bar categories.
- The `bar` category also tags hotel lobbies and campgrounds → `filter.exclude.tags`.

## Accomplishments that we're proud of

A number we did not choose: the backtest could have shown taste losing to the LLM. It doesn't — and the method, data and recorded responses are public so anyone can check.

## What we learned

Taste data is strongest exactly where general knowledge runs out: the 20th to 100th name, the mid-size room, the bar three streets from the venue.

## What's next

Venue capacity and availability (Qloo does not hold them), a routing view that orders the cities into a tour, and evaluating "which room" against real tour itineraries the way we did for openers.
