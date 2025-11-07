import igraph as ig

from d3_svg_network import MiniD3SVG, Selection, NetworkSVG

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
