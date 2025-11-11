import igraph as ig

from lxml import etree

from d3_svg_network import MiniD3SVG, Selection, NetworkSVG, SVG_NS

def test_attr_name_conversion_and_data_binding():
    svg = MiniD3SVG(width=200, height=100)
    group = svg.append("g")
    data = [{"cx": 10, "cy": 15}, {"cx": 40, "cy": 35}]
    nodes = [group.append("circle").elements[0] for _ in data]

    sel = Selection(nodes).data(data)
    sel.attr("stroke_width", 2)
    sel.attr("cx", lambda d, *_: d["cx"]).attr("cy", lambda d, *_: d["cy"])

    assert nodes[0].get("stroke-width") == "2"
    assert nodes[0].get("cx") == "10"
    assert nodes[1].get("cy") == "35"


def test_networksvg_builds_layers_and_sorts():
    g = ig.Graph.Ring(4)
    g.vs["Position"] = [(i * 50.0, 40.0) for i in range(g.vcount())]
    g.vs["Color"] = ["#ff7f0e", "#2ca02c", "#1f77b4", "#9467bd"]
    g.vs["Label"] = [f"N{i}" for i in range(g.vcount())]
    g.es["weight"] = list(range(1, g.ecount() + 1))

    net = NetworkSVG(g, width=300, height=120)

    assert len(net.nodes.elements) == g.vcount()
    assert len(net.edges.elements) == g.ecount()
    assert len(net.labels.elements) == g.vcount()

    net.sort_edges(by="weight", reverse=True)
    net.sort_nodes(key=lambda v: v["Label"], reverse=True)
    net.sort_labels(cmp=lambda a, b: (a["Label"] > b["Label"]) - (a["Label"] < b["Label"]))

    first_edge_datum = Selection._get_data(net.edges.elements[0])
    assert first_edge_datum["weight"] == max(g.es["weight"])

    first_node_datum = Selection._get_data(net.nodes.elements[0])
    assert first_node_datum["Label"] == "N3"


def test_select_all_applies_attrs_with_svg_namespace():
    g = ig.Graph.Ring(3)
    g.vs["Position"] = [(i * 40.0, 20.0) for i in range(g.vcount())]
    g.vs["Color"] = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    g.vs["Label"] = [f"N{i}" for i in range(g.vcount())]

    net = NetworkSVG(g, width=200, height=100)

    circles = net.nodes.select_all("circle")
    assert circles.elements
    circles.attr("r", 15)
    assert all(circle.get("r") == "15" for circle in circles.elements)

    texts = net.labels.select_all("text")
    assert texts.elements
    texts.attrs(font_weight="600", stroke_width="4")
    assert all(text.get("font-weight") == "600" for text in texts.elements)
    assert all(text.get("stroke-width") == "4" for text in texts.elements)


def test_enable_edge_average_color_uses_node_colors():
    g = ig.Graph.Ring(2)
    g.vs["Position"] = [(0.0, 0.0), (50.0, 0.0)]
    g.vs["Color"] = ["#000000", "#ffffff"]
    net = NetworkSVG(g, width=120, height=60)

    net.enable_edge_average_color()

    assert net.edges.elements
    for edge_el in net.edges.elements:
        assert edge_el.get("stroke") == "#808080"


def test_enable_edge_color_gradient_adds_linear_gradient():
    g = ig.Graph.Ring(2)
    g.vs["Position"] = [(0.0, 0.0), (100.0, 0.0)]
    g.vs["Color"] = ["#000000", "#00ff00"]
    net = NetworkSVG(g, width=160, height=80)

    net.enable_edge_color_gradient()

    first_edge = net.edges.elements[0]
    stroke = first_edge.get("stroke")
    assert stroke.startswith("url(#edge-gradient-")

    svg = net.to_string(pretty=False, illustrator_safe=False)
    root = etree.fromstring(svg.encode("utf-8"))
    gradients = root.findall(f".//{{{SVG_NS}}}linearGradient")
    assert gradients
    gradient = gradients[0]
    assert gradient.get("gradientUnits") == "userSpaceOnUse"
    stops = gradient.findall(f"{{{SVG_NS}}}stop")
    assert len(stops) == 2
    assert stops[0].get("stop-color") == "#000000"
    assert stops[1].get("stop-color") == "#00ff00"


def test_illustrator_safe_labels_duplicate_text():
    g = ig.Graph.Ring(3)
    g.vs["Position"] = [(i * 40.0, 20.0) for i in range(g.vcount())]
    g.vs["Color"] = ["#123456"] * g.vcount()
    g.vs["Label"] = [f"L{i}" for i in range(g.vcount())]
    net = NetworkSVG(g, width=200, height=80)

    svg_text = net.to_string(pretty=False, illustrator_safe=True)
    root = etree.fromstring(svg_text.encode("utf-8"))
    label_groups = root.findall(f".//{{{SVG_NS}}}g[@class='label']")
    assert label_groups, "expected label groups in output"
    for group in label_groups:
        texts = group.findall(f"{{{SVG_NS}}}text")
        assert len(texts) == 2
        stroke_text, fill_text = texts[0], texts[1]
        assert stroke_text.get("fill") == "none"
        assert stroke_text.get("stroke") is not None
        assert fill_text.get("stroke") is None


def test_directed_curves_emit_path_elements():
    g = ig.Graph(directed=True)
    g.add_vertices(2)
    g.add_edges([(0, 1)])
    g.vs["Position"] = [(0.0, 0.0), (100.0, 0.0)]
    net = NetworkSVG(g, width=200, height=80, directed_curves=True)
    assert net.edges.elements, "expected an edge element"
    edge_el = net.edges.elements[0]
    assert edge_el.tag.endswith("path")
    assert edge_el.get("d").startswith("M ")


def test_label_font_family_injected_via_style_block():
    g = ig.Graph.Ring(2)
    g.vs["Position"] = [(0.0, 0.0), (50.0, 0.0)]
    g.vs["Label"] = ["A", "B"]

    net = NetworkSVG(g, width=120, height=60, label_font_family="Roboto Test")
    svg = net.to_string(pretty=False, illustrator_safe=False)
    assert "Roboto Test" in svg
    root = etree.fromstring(svg.encode("utf-8"))
    text_nodes = root.findall(f".//{{{SVG_NS}}}text")
    assert text_nodes
    for node in text_nodes:
        assert node.get("font-family") is None

    net_custom = NetworkSVG(g, width=120, height=60, label_font_family=None)
    svg_custom = net_custom.to_string(pretty=False, illustrator_safe=False)
    assert "Roboto Test" not in svg_custom


def test_fit_to_view_scales_positions_into_bounds():
    g = ig.Graph.Ring(2)
    g.vs["Position"] = [(1000.0, 1000.0), (2000.0, 1500.0)]
    net = NetworkSVG(g, width=200, height=200, fit_to_view=True, fit_margin=10)
    xs = [p[0] for p in net.positions]
    ys = [p[1] for p in net.positions]
    assert min(xs) >= 10 - 1e-6
    assert max(xs) <= 190 + 1e-6
    assert min(ys) >= 10 - 1e-6
    assert max(ys) <= 190 + 1e-6
