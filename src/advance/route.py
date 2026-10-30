"""Order the markets of a brief into a tour: the shortest open path between them.

Straight-line distance, not a booking calendar: it answers "which cities sit together" so a promoter
does not route Boston -> Nashville -> Boston. Seven stops at most, so every order is checked.
"""
import itertools
import math

MAX_STOPS = 7
MIN_APART_KM = 60          # two stops this close are one market (Boston and Cambridge)
KM_PER_MILE = 1.609344


def km(a, b):
    (la1, lo1), (la2, lo2) = (math.radians(a["lat"]), math.radians(a["lon"])), (math.radians(b["lat"]), math.radians(b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def pick(stops, limit=MAX_STOPS):
    """Keep the first `limit` stops that are not within MIN_APART_KM of one already kept."""
    kept = []
    for s in stops:
        if all(km(s, k) >= MIN_APART_KM for k in kept):
            kept.append(s)
        if len(kept) == limit:
            break
    return kept


def shortest(stops):
    """The visiting order with the least total distance (no fixed start or end)."""
    if len(stops) < 3:
        return list(stops)
    best, best_len = None, math.inf
    for order in itertools.permutations(stops):
        if order[0]["name"] > order[-1]["name"]:      # a path and its reverse are the same tour
            continue
        total = sum(km(x, y) for x, y in zip(order, order[1:]))
        if total < best_len:
            best, best_len = order, total
    return list(best)


def plan(named, markets, unit="mi"):
    """`named`: the cities the promoter typed; `markets`: Qloo's destinations, best taste first.
    Every stop is {name, lat, lon}. Returns None when there are not two places to join."""
    stops = pick(list(named) + list(markets))
    if len(stops) < 2:
        return None
    order = shortest(stops)
    div = KM_PER_MILE if unit == "mi" else 1
    legs = [{"from": a["name"], "to": b["name"], "distance": round(km(a, b) / div)} for a, b in zip(order, order[1:])]
    return {"unit": unit, "stops": [{"name": s["name"], "lat": s["lat"], "lon": s["lon"],
                                     "typed": s["name"] in {n["name"] for n in named}} for s in order],
            "legs": legs, "total": sum(l["distance"] for l in legs)}
