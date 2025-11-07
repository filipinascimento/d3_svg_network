"""Example converting an igraph network into SVG using NetworkSVG."""

import igraph as ig

from d3_svg_network import NetworkSVG, scale_linear


def main():
    g = ig.Graph.Ring(8)
    g.vs["Position"] = [(i * 60 + 30, (i % 2) * 60 + 40) for i in range(g.vcount())]
    g.vs["Color"] = ["#1f77b4", "#ff7f0e"] * 4
    g.vs["Label"] = [f"Node {i}" for i in range(g.vcount())]
    g.es["weight"] = list(range(1, g.ecount() + 1))

    net = NetworkSVG(g, width=500, height=150, bg="#fff")
    net.set_text_style(font_family="'Source Sans Pro'", font_size="11px")

    degree_scale = scale_linear(domain=(0, max(g.degree())), range_=(6, 22))
    net.nodes.select_all("circle").attr(
        "r", lambda node, *_: degree_scale(g.degree(node.index))
    )

    net.edges.attr(
        "stroke",
        lambda edge, *_: "#d62728" if edge["weight"] >= 4 else "#999999",
    )

    net.labels.select_all("text").attrs(font_weight="600")

    net.save("network.svg")


if __name__ == "__main__":
    main()
