# Venue backtest

417 (headliner, US city) cases from 107 real tours (dates tables on Wikipedia, 2023-2025). Skipped and counted, not hidden: {'no_us_dates': 8, 'headliner_missing': 0, 'city_empty': 10}.

A case is a hit when the room the tour actually played in that city is in the first 8 (or 25) rooms of the list.

| list | hit in first 8 | hit in first 25 |
|---|---|---|
| Qloo taste for the headliner | 156/417 (37%) | 234/417 (56%) |
| Qloo popular rooms, no artist signal | 207/417 (50%) | 283/417 (68%) |
| Popular rooms, ordered by this audience's taste | 176/417 (42%) | 283/417 (68%) |

Taste list, first 50: 276/417 (66%).

In the first 8: both hit 149, only taste 7, only the popularity list 58.


## What this says, plainly

- For guessing which room a real tour played in a city, **the city's popular rooms beat the taste list**: 50% against 37% in the first 8. The taste list adds 7 hits the popular list misses and loses 58 that it has. Tours book big, familiar rooms, and Qloo's taste ordering pulls toward rooms this audience likes, which are not always the ones a tour can fill.
- Ordering the popular rooms by taste (the hybrid) lands in between, 42%. Matching the kind of room to the headliner's size does not rescue taste: arena/stadium vs hall/club by popularity gives 52% for the sized list and 50% once taste orders it (`docs/VENUE_SIZE_MATCH.md`, cut 0.99).
- So Advance shows both lists for every city: **Most-booked rooms** (no taste signal, the better predictor of where tours play) and **Which room** (what this audience favours, the answer to "which room fits these fans" and the part that varies by act).
- The test measures one thing: whether the room the tour played shows up. It does not say the room was the best choice, and Wikipedia date tables cover tours with US dates only (107 of 115; 8 had none).
