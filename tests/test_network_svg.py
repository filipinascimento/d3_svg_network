import math

import igraph as ig

from d3_svg_network import NetworkSVG


def _extract_radius(path_d):
    parts = path_d.split()
    # "M sx sy A rx ry 0 large_arc sweep tx ty"
    return float(parts[4])


def test_directed_curve_radius_matches_gephi_default():
    g = ig.Graph(directed=True)
    g.add_vertices(2)
    g.add_edges([(0, 1)])
    g.vs["Position"] = [(0.0, 0.0), (100.0, 0.0)]

    net = NetworkSVG(g, directed_curves=True, directed_curve_factor=2.0)

    path_d = net.edges.elements[0].get("d")
    radius = _extract_radius(path_d)
    assert math.isclose(radius, 50.0)


def test_directed_curve_radius_can_use_edge_attribute():
    g = ig.Graph(directed=True)
    g.add_vertices(2)
    g.add_edges([(0, 1)])
    g.vs["Position"] = [(0.0, 0.0), (80.0, 30.0)]
    g.es["CurveRadius"] = [120.0]

    net = NetworkSVG(g, directed_curves=True)
    net.use_edge_attribute_for_curve_radius("CurveRadius")

    path_d = net.edges.elements[0].get("d")
    radius = _extract_radius(path_d)
    assert math.isclose(radius, 120.0)
