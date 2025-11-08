"""Example of rendering a directed network with curved edge paths."""

import igraph as ig

from d3_svg_network import NetworkSVG


def main():
    g = ig.Graph(directed=True)
    g.add_vertices(4)
    g.add_edges([(0, 1), (1, 0), (1, 2), (2, 3), (3, 0), (0, 2)])
    g.vs["Position"] = [
        (50, 40),
        (150, 40),
        (150, 140),
        (50, 140),
    ]
    g.vs["Color"] = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    g.vs["Label"] = [f"Node {i}" for i in range(g.vcount())]

    net = NetworkSVG(
        g,
        width=220,
        height=200,
        bg="#fff",
        directed_curves=True,
        directed_curve_factor=0.9,
    )

    net.edges.attr("stroke", "#555")
    net.labels.select_all("text").attr("font_size", 12)

    net.save("network_directed_curves.svg")


if __name__ == "__main__":
    main()
