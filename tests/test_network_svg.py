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


def test_set_text_style_merges_into_single_rule():
    g = ig.Graph()
    g.add_vertices(1)
    g.vs["Position"] = [(0.0, 0.0)]

    net = NetworkSVG(g)
    net.set_text_style(font_size="12px")
    net.set_text_style(fill="#333")

    style_nodes = [
        el
        for el in net.svg.root
        if el.tag.endswith("}style") and el.get("data-networksvg-role") == "text-style"
    ]

    assert len(style_nodes) == 1
    css = style_nodes[0].text
    assert css.count(".label text") == 1
    assert "font-size: 12px" in css
    assert "fill: #333" in css


def test_set_text_style_handles_multiple_selectors():
    g = ig.Graph()
    g.add_vertices(1)
    g.vs["Position"] = [(0.0, 0.0)]

    net = NetworkSVG(g)
    net.set_text_style(selector=".label text", font_size="10px")
    net.set_text_style(selector=".label tspan", font_weight="600")

    style_nodes = [
        el
        for el in net.svg.root
        if el.tag.endswith("}style") and el.get("data-networksvg-role") == "text-style"
    ]

    assert len(style_nodes) == 1
    css_lines = style_nodes[0].text.splitlines()
    assert any(".label text" in line for line in css_lines)
    assert any(".label tspan" in line for line in css_lines)
