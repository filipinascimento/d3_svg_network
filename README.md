# Mini D3 SVG Toolkit

The `d3_svg_network` package gives you a lightweight, Pythonic subset of D3’s selection API for building SVGs programmatically, plus a `NetworkSVG` helper that turns `igraph.Graph` objects into ready-to-style SVG diagrams.

## Prerequisites

Install the package (and its minimal dependencies):

```bash
pip install git+https://github.com/filipinascimento/d3_svg_network.git
```

Note: The package will be available via PyPI in the near future.

All examples below assume `import d3_svg_network as d3`.

## Core Concepts

- **MiniD3SVG** – manages the root `<svg>`, lets you append elements, save to disk, or grab the serialized text.
- **Selection** – wraps a list of `lxml` elements and offers `append`, `attr`, `style`, `text`, `data`, and `datum`, mirroring the most common D3 patterns.
- **Attribute names** – pass Pythonic names (`text_anchor`, `stroke_width`). They automatically convert to their SVG form (`text-anchor`, `stroke-width`).
- **Callables everywhere** – `attr`, `style`, and `text` accept callables that receive `(datum, index, element)` so you can compute values from bound data.

## Quickstart: Building an SVG

```python
import d3_svg_network as d3

svg = d3.MiniD3SVG(width=320, height=160, bg="#f8f8f8")
g = svg.append("g", transform="translate(20,20)")

data = [
    {"cx": 30, "cy": 30, "r": 12, "fill": "#1f77b4", "label": "A"},
    {"cx": 90, "cy": 70, "r": 18, "fill": "#ff7f0e", "label": "B"},
    {"cx": 150, "cy": 40, "r": 10, "fill": "#2ca02c", "label": "C"},
]

circles = [g.append("circle").elements[0] for _ in data]
d3.Selection(circles).data(data)\
    .attr("cx", lambda d, *_: d["cx"])\
    .attr("cy", lambda d, *_: d["cy"])\
    .attr("r",  lambda d, *_: d["r"])\
    .style(fill=lambda d, *_: d["fill"], stroke="#333", stroke_width=1)

labels = [g.append("text").elements[0] for _ in data]
d3.Selection(labels).data(data)\
    .attr("x", lambda d, *_: d["cx"])\
    .attr("y", lambda d, *_: d["cy"] + d["r"] + 12)\
    .attr("text_anchor", "middle")\
    .attr("font_size", 10)\
    .text(lambda d, *_: d["label"])

svg.save("circles.svg")
```

## Data Binding Helpers

- `Selection.data(iterable)` binds each datum to the corresponding element (lengths must match).
- `Selection.datum(value_or_callable)` sets/get a single datum for all elements (callables receive the previous datum).

Once bound, `attr/style/text` callables can pull fields directly off the datum, just like D3.

## NetworkSVG: From igraph to SVG

`NetworkSVG` builds default node, edge, and label visuals for any `igraph.Graph` that has coordinates. It exposes each layer (`net.nodes`, `net.edges`, `net.labels`) as selections so you can restyle or append to them immediately.

```python
import igraph as ig
import d3_svg_network as d3

g = ig.Graph.Ring(8)
g.vs["Position"] = [(i * 60 + 30, (i % 2) * 60 + 40) for i in range(g.vcount())]
g.vs["Color"] = ["#1f77b4", "#ff7f0e"] * 4
g.es["weight"] = list(range(1, g.ecount() + 1))

net = d3.NetworkSVG(g, width=500, height=150, bg="#fff")

degree_scale = d3.scale_linear(domain=(0, max(g.degree())), range_=(6, 22))
net.nodes.select_all("circle").attr(
    "r", lambda node, *_: degree_scale(g.degree(node.index))
)

net.edges.attr(
    "stroke",
    lambda edge, *_: "#d62728" if edge["weight"] >= 4 else "#999999",
)

# Optional helpers let edges inherit node colors:
net.enable_edge_average_color()            # solid stroke midway between source/target fills
# or:
net.enable_edge_color_gradient()           # gradient stroke from source to target

# keep labels above nodes
net.labels.select_all("text").attr("font_size", 12)

net.save("network.svg")
```

### Position Fallback Rules

`NetworkSVG` looks for node coordinates in this order (unless you pass `positions=` explicitly):

1. Vertex attribute named `Position`, `position`, or `positions` (list/tuple per node).
2. Separate `x`/`X` and `y`/`Y` vertex attributes.

If none exist, it raises an error asking you to supply coordinates.

### Fitting To The Viewport

Pass `fit_to_view=True` when constructing `NetworkSVG` to automatically scale and translate all node coordinates so the entire network fits inside the SVG canvas while preserving aspect ratio. Control the padding via `fit_margin` (scalar for all sides, or `(horizontal, vertical)` tuples). The original coordinates remain available through `net._original_positions`; `net.positions` contains the fitted values used for rendering.

### Default Styling Logic

- Nodes render as `<g class="node">` translated to their positions with an inner `<circle>`.
  - `Size`/`size`/`radius` attributes set the radius; default is `8`.
  - `Color`/`color`/`fill` sets the fill; default `#4C78A8`.
  - `OutlineColor`/`outline_color`/`stroke` sets stroke; otherwise a darker version of the fill.
  - `OutlineWidth`/`outline_width`/`stroke_width` sets stroke width; default `1`.
- Edges render as `<line>` connecting endpoints.
  - `Color`/`color`/`stroke` sets stroke color; default `#999999`.
  - Set `UseSourceColor`/`UseTargetColor` to color edges based on an endpoint.
  - `Width`/`width`/`stroke_width` sets thickness; otherwise it grows with `weight` if present.
  - Pass a `edge_generator=edge_fn` callable when constructing `NetworkSVG` to emit custom shapes (arc paths, bundles, etc.). Generators receive `(edge, (x1,y1), (x2,y2))` and return either a `Selection`, `(tag, attrs)` tuple, a `{ "tag": ..., "attrs": ..., "children": [...] }` dict, or a raw `lxml` element.
  - For directed graphs, set `directed_curves=True` when creating `NetworkSVG` to draw clockwise arc paths instead of straight lines (uses SVG `<path>` with `A` commands). By default, curvature follows Gephi’s preview heuristic: `radius = edge_length / directed_curve_factor`.

### Label Layer

- Labels live in their own `<g class="label-visuals">` appended after nodes so they always sit on top.
- By default, each node with a non-empty `Label`/`label`/`name` attribute (and without `show_label=False`) gets `<g class="label">` containing centered `<text>` (`text-anchor: middle`, `dy="0.35em"` compensation, rounded stroke joins/caps). A stylesheet block defines the default font stack (`Roboto, Helvetica, Arial, sans-serif`); override via `label_font_family="Your Font"` or by injecting your own `.label text { ... }` rule.
- Label fill defaults to white when the node has a color, with a darker stroke (`paint-order: stroke fill`, `stroke-linecap: round`) so text stays readable.
- Provide `LabelSize`, `label_size`, `LabelOutline`, or a custom `label_generator` callable to override the defaults entirely.
- Configure the default label font stack via `label_font_family="...'"` when constructing `NetworkSVG` (set to `None` to skip the injected style rule).

Access the layer via `net.labels`:

```python
net.labels.select_all("text").attrs(font_size=11, font_weight="600")
```

### Sorting Layers

Keep the DOM order predictable (useful before exporting or when relying on painter’s algorithm) via:

```python
net.sort_edges(by="weight", reverse=True)
net.sort_nodes(key=lambda v: v["community"])
net.sort_labels(cmp=lambda a, b: len(a["Label"]) - len(b["Label"]))
```

Each sorter accepts either `by="attribute"`, a `key` function, or a comparator `cmp`, plus `reverse=True/False`.

### Global Styles / Fonts
### Directed Curves (optional)

When your graph is directed, construct `NetworkSVG(..., directed_curves=True)` to render each edge as a clockwise arc instead of a straight `<line>`. The helper uses SVG arc paths (`<path d="M ... A ...">`) so arrowheads or other markers will follow the curve naturally. Curvature matches Gephi’s renderer: each edge gets `radius = edge_length / directed_curve_factor` (akin to the `ARC_CURVENESS` slider), so higher factors bend more aggressively.

Need a different rule? Call `net.set_directed_curve_radius_resolver(resolver)` with a custom `(edge, length, default_radius)` resolver or `net.use_edge_attribute_for_curve_radius("CurveRadius")` to read per-edge values while retaining sensible fallbacks.

Add SVG-wide styles once and keep individual groups clean:

```python
net.set_text_style(font_family="'Source Sans Pro'", font_size="11px", fill="#222")
net.add_style(".label text { letter-spacing: 0.5px; }")
```

Both helpers insert `<style>` nodes at the top of the SVG, so all future labels/nodes inherit the same typography.

### Custom Node Generators

Provide `node_generator=callable` to override the default circle. Your callable receives `(vertex, (x, y))` and can return any of the same spec types supported by edge generators. The parent group is already translated so you can draw at the origin.

## Scale Helpers

- `scale_linear(domain=(d0, d1), range_=(r0, r1))` behaves like `d3.scaleLinear`, useful for mapping metrics (degree, weight) to radii, stroke widths, etc.
- `scale_ordinal(domain=[...], range_=[...])` maps discrete categories to a list of colors/sizes, adding unseen domain values automatically.

```python
category = d3.scale_ordinal(range_=["#1f77b4", "#ff7f0e", "#2ca02c"])
net.nodes.select_all("circle").style(fill=lambda node, *_: category(node["community"]))
```

## Saving and Inspecting

- `MiniD3SVG.save("out.svg")` or `NetworkSVG.save(...)` write prettified SVG.
- `NetworkSVG.save(..., illustrator_safe=True)` (the default) clones each label’s text so the stroke and fill render correctly in Illustrator. Pass `illustrator_safe=False` if you prefer the more compact single-text output.
- `to_string(pretty=False)` returns a raw string when you want to embed the markup directly.

## Troubleshooting

- **`ValueError: positions iterable must match number of vertices`** – ensure the provided coordinate list matches `g.vcount()`.
- **`Generator functions must return ...`** – custom node/edge generators need to return a `Selection`, `(tag, attrs)`, dict spec, or `lxml` element.
- **Attributes not applied** – remember to use Pythonic names (`text_anchor`, `stroke_width`) or pass them via `attrs(**{"text-anchor": "middle"})` if you prefer literal forms.

Feel free to extend `d3_svg_network` with additional helpers (e.g., curved-edge generators, force layouts, legend builders) using the same patterns.

## Examples & Tests

- Run the sample scripts in `examples/` for quick demos: `python examples/basic_svg.py`, `python examples/network_svg.py`, and `python examples/network_svg_curved.py`.
- Execute `python -m pytest` (with the `networks` Conda env or your own virtualenv) to run the unit tests in `tests/`.
