"""Example of rendering a directed network with curved edge paths."""

import igraph as ig

from d3_svg_network import NetworkSVG


def main():
    g = ig.Graph(directed=True)
    g.add_vertices(4)
    g.add_edges([(0, 1), (1, 0), (1, 2), (2, 3), (3, 0), (0, 2)])
    g.vs["Position"] = [
        (80, 80),
        (150, 40),
        (150, 140),
        (50, 140),
    ]
    g.vs["Color"] = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    g.vs["Label"] = [f"Node {i}" for i in range(g.vcount())]
    g.es["CurveRadius"] = [65, 65, 90, 40, 75, 55]

    net = NetworkSVG(
        g,
        width=220,
        height=200,
        bg="#fff",
        directed_curves=True,
        directed_curve_factor=1.2,
    )

    net.edges.attr("stroke", "#555").attr("stroke_width", 4).attr("marker_end", "arrow")
    # Uncomment to color directed edges using node colors:
    net.enable_edge_average_color()
    # net.enable_edge_color_gradient()
    net.labels.select_all("text").attr("font_size", 12)
    # net.use_edge_attribute_for_curve_radius("CurveRadius")

    net.save("network_directed_curves.svg")


if __name__ == "__main__":
    main()
