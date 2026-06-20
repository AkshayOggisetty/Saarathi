"""
Saarthi — Phase 4: diversion routing (G3).

Two modes:
  * OSM mode  : if osmnx + Overpass are reachable, compute a real shortest-path
                detour around the blocked road segment.
  * Local mode: a self-contained geometric detour (no network) so the demo
                never breaks. Generates a plausible bypass via an offset
                waypoint perpendicular to travel direction.

The frontend calls plan_diversion(); it transparently uses OSM if available,
otherwise the local engine.
"""
import math

EARTH_KM = 6371.0


def _haversine(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    p = math.pi / 180
    h = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * EARTH_KM * math.asin(math.sqrt(h))


def _offset(lat, lon, dx_km, dy_km):
    dlat = dy_km / 110.574
    dlon = dx_km / (111.320 * math.cos(math.radians(lat)))
    return (lat + dlat, lon + dlon)


def _local_diversion(lat, lon, end, radius_km=0.6):
    """Geometric bypass: route around the blocked point via a side waypoint."""
    if end is None or end == (0, 0):
        # no destination given: synthesise a short through-segment along +lon
        end = _offset(lat, lon, radius_km * 2, 0)
    # bearing of travel
    brng = math.atan2(end[1] - lon, end[0] - lat)
    # perpendicular offset waypoints (left bypass)
    perp = brng + math.pi / 2
    dx = radius_km * math.sin(perp)
    dy = radius_km * math.cos(perp)
    mid_lat = (lat + end[0]) / 2
    mid_lon = (lon + end[1]) / 2
    w1 = _offset(lat, lon, dx, dy)
    w2 = _offset(mid_lat, mid_lon, dx * 1.4, dy * 1.4)
    w3 = _offset(end[0], end[1], dx, dy)
    route = [(lat, lon), w1, w2, w3, (end[0], end[1])]

    direct = _haversine((lat, lon), (end[0], end[1])) or radius_km
    detour = sum(_haversine(route[i], route[i + 1]) for i in range(len(route) - 1))
    extra = max(detour - direct, 0)
    return {
        "mode": "local-heuristic",
        "route": [[round(la, 6), round(lo, 6)] for la, lo in route],
        "direct_km": round(direct, 2),
        "detour_km": round(detour, 2),
        "extra_km": round(extra, 2),
        "extra_min_est": round(extra / 25 * 60, 1),  # ~25 km/h urban
    }


def _osm_diversion(lat, lon, end, radius_m=900):
    """Real OSM detour. Only used if osmnx + Overpass available."""
    import osmnx as ox
    import networkx as nx
    G = ox.graph_from_point((lat, lon), dist=radius_m, network_type="drive")
    if end is None or end == (0, 0):
        nodes = list(G.nodes)
        orig = ox.distance.nearest_nodes(G, lon, lat)
        dest = nodes[len(nodes) // 2]
    else:
        orig = ox.distance.nearest_nodes(G, lon, lat)
        dest = ox.distance.nearest_nodes(G, end[1], end[0])
    # remove edges nearest the blocked point to force a detour
    blk = ox.distance.nearest_edges(G, lon, lat)
    if G.has_edge(*blk[:2]):
        G.remove_edge(*blk[:2])
    path = nx.shortest_path(G, orig, dest, weight="length")
    coords = [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in path]
    detour = sum(_haversine(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
    return {"mode": "osm-real", "route": coords,
            "detour_km": round(detour, 2), "extra_km": None, "extra_min_est": None}


def plan_diversion(lat, lon, endlat=0, endlon=0, prefer_osm=False):
    end = (endlat, endlon) if endlat and endlon else None
    if prefer_osm:
        try:
            return _osm_diversion(lat, lon, end)
        except Exception:
            pass  # fall through to local
    return _local_diversion(lat, lon, end)


if __name__ == "__main__":
    import json
    print(json.dumps(plan_diversion(12.95, 77.53, 12.96, 77.55), indent=2))
