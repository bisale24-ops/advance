from advance import route


def stop(name, lat, lon):
    return {"name": name, "lat": lat, "lon": lon}


BOS, CHI, DEN, NYC = stop("Boston", 42.36, -71.06), stop("Chicago", 41.88, -87.63), stop("Denver", 39.74, -104.98), stop("New York", 40.71, -74.0)


def test_the_route_does_not_double_back():
    # typed order Boston, Denver, New York, Chicago zig-zags; the shortest path is monotone east to west
    got = route.plan([BOS, DEN], [NYC, CHI])
    names = [s["name"] for s in got["stops"]]
    assert names in (["Boston", "New York", "Chicago", "Denver"], ["Denver", "Chicago", "New York", "Boston"])
    assert got["total"] == sum(l["distance"] for l in got["legs"])


def test_the_shortest_path_beats_every_other_order():
    import itertools
    stops = [BOS, CHI, DEN, NYC]
    best = route.plan([], stops)["total"]
    km = lambda o: sum(route.km(a, b) for a, b in zip(o, o[1:])) / route.KM_PER_MILE
    assert best <= round(min(km(o) for o in itertools.permutations(stops))) + 4   # rounding of four legs


def test_one_market_is_not_two_stops():
    cambridge = stop("Cambridge", 42.37, -71.11)
    assert [s["name"] for s in route.plan([BOS], [cambridge, CHI])["stops"]].count("Cambridge") == 0


def test_a_single_place_is_no_route():
    assert route.plan([BOS], [stop("Cambridge", 42.37, -71.11)]) is None


def test_roads_attach_to_every_leg_and_a_failed_lookup_stays_none():
    tour = route.plan([BOS, DEN], [NYC, CHI])
    calls = []

    def lookup(a, b):
        calls.append((a["name"], b["name"]))
        return None if b["name"] == "Chicago" else {"km": 100, "hours": 1.5}

    got = route.with_roads(tour, lookup)
    assert len(calls) == len(got["legs"]) == 3
    assert [l["road"] is None for l in got["legs"]].count(True) == 1
    assert route.with_roads(None, lookup) is None


def test_the_order_follows_road_time_when_a_matrix_is_known():
    # on a map Boston-Chicago-Denver looks like the shortest line, but here the roads say Chicago is the far end
    stops = [BOS, CHI, DEN]
    seconds = [[0, 90, 10], [90, 0, 10], [10, 10, 0]]       # Boston-Denver and Chicago-Denver are quick, Boston-Chicago is not
    got = route.plan([], stops, matrix=lambda s: seconds)
    names = [x["name"] for x in got["stops"]]
    assert names[1] == "Denver" and got["ordered_by"] == "road time (OSRM)"
    assert route.plan([], stops)["ordered_by"] == "straight-line distance"
    assert route.plan([], stops, matrix=lambda s: None)["ordered_by"] == "straight-line distance"
