"""Order the markets of a brief into a tour: the shortest open path between them.

Straight-line distance, not a booking calendar: it answers "which cities sit together" so a promoter
does not route Boston -> Nashville -> Boston. Seven stops at most, so every order is checked.
"""
import itertools
import json
import math
import urllib.request

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


def shortest(stops, cost=None):
    """The visiting order with the least total cost (no fixed start or end). `cost(a, b)` defaults to
    straight-line km; pass road seconds when a matrix is known."""
    cost = cost or km
    if len(stops) < 3:
        return list(stops)
    best, best_len = None, math.inf
    for order in itertools.permutations(stops):
        if order[0]["name"] > order[-1]["name"] and cost is km:   # a path and its reverse are the same tour
            continue
        total = sum(cost(x, y) for x, y in zip(order, order[1:]))
        if total < best_len:
            best, best_len = order, total
    return list(best)


def plan(named, markets, unit="mi", matrix=None):
    """`named`: the cities the promoter typed; `markets`: Qloo's destinations, best taste first.
    Every stop is {name, lat, lon}. Returns None when there are not two places to join."""
    stops = pick(list(named) + list(markets))
    if len(stops) < 2:
        return None
    seconds = matrix(stops) if matrix else None          # road time between every pair, or None
    index = {s["name"]: i for i, s in enumerate(stops)}
    order = shortest(stops, (lambda a, b: seconds[index[a["name"]]][index[b["name"]]]) if seconds else None)
    div = KM_PER_MILE if unit == "mi" else 1
    legs = [{"from": a["name"], "to": b["name"], "distance": round(km(a, b) / div)} for a, b in zip(order, order[1:])]
    return {"unit": unit, "stops": [{"name": s["name"], "lat": s["lat"], "lon": s["lon"],
                                     "typed": s["name"] in {n["name"] for n in named}} for s in order],
            "legs": legs, "total": sum(l["distance"] for l in legs),
            "ordered_by": "road time (OSRM)" if seconds else "straight-line distance"}


OSRM = "https://router.project-osrm.org/route/v1/driving/{a};{b}?overview=false"


def road(a, b, timeout=4):
    """Road distance (km) and driving hours between two stops from OSRM (OpenStreetMap data).
    None when the service does not answer: the page then says it is an estimate."""
    url = OSRM.format(a="%s,%s" % (a["lon"], a["lat"]), b="%s,%s" % (b["lon"], b["lat"]))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "advance/0.1"}), timeout=timeout) as r:
            data = json.load(r)
        leg = data["routes"][0]
        return {"km": round(leg["distance"] / 1000), "hours": round(leg["duration"] / 3600, 1)}
    except Exception:  # noqa: BLE001 - any failure means no road figure, never a made-up one
        return None


def with_roads(tour, lookup=road):
    """Attach a `road` figure to every leg of a plan (None where the lookup failed)."""
    if not tour:
        return tour
    import concurrent.futures
    stops = {s["name"]: s for s in tour["stops"]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        found = list(pool.map(lambda leg: lookup(stops[leg["from"]], stops[leg["to"]]), tour["legs"]))
    for leg, figure in zip(tour["legs"], found):
        leg["road"] = figure
    return tour


OSRM_TABLE = "https://router.project-osrm.org/table/v1/driving/{points}?annotations=duration"


def road_matrix(stops, timeout=6):
    """Driving seconds between every pair of stops from one OSRM table call, or None."""
    points = ";".join("%s,%s" % (s["lon"], s["lat"]) for s in stops)
    try:
        with urllib.request.urlopen(urllib.request.Request(OSRM_TABLE.format(points=points),
                                                           headers={"User-Agent": "advance/0.1"}), timeout=timeout) as r:
            data = json.load(r)
        rows = data["durations"]
        if data.get("code") != "Ok" or any(v is None for row in rows for v in row):
            return None
        return rows
    except Exception:  # noqa: BLE001 - no matrix means the order falls back to straight lines, and says so
        return None
