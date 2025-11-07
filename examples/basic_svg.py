"""Minimal example building an SVG with the MiniD3 selection API."""

from d3_svg_network import MiniD3SVG, Selection


def main():
    svg = MiniD3SVG(width=320, height=160, bg="#f8f8f8")
    group = svg.append("g", transform="translate(20,20)")

    data = [
        {"cx": 30, "cy": 30, "r": 12, "fill": "#1f77b4", "label": "A"},
        {"cx": 90, "cy": 70, "r": 18, "fill": "#ff7f0e", "label": "B"},
        {"cx": 150, "cy": 40, "r": 10, "fill": "#2ca02c", "label": "C"},
    ]

    circles = [group.append("circle").elements[0] for _ in data]
    Selection(circles).data(data) \
        .attr("cx", lambda d, *_: d["cx"]) \
        .attr("cy", lambda d, *_: d["cy"]) \
        .attr("r", lambda d, *_: d["r"]) \
        .style(fill=lambda d, *_: d["fill"], stroke="#333", stroke_width=1)

    labels = [group.append("text").elements[0] for _ in data]
    Selection(labels).data(data) \
        .attr("x", lambda d, *_: d["cx"]) \
        .attr("y", lambda d, *_: d["cy"] + d["r"] + 12) \
        .attr("text_anchor", "middle") \
        .attr("font_size", 10) \
        .text(lambda d, *_: d["label"])

    svg.save("basic_circles.svg")


if __name__ == "__main__":
    main()
