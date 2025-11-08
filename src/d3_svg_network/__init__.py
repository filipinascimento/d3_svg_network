# pip install lxml
from lxml import etree
from lxml.cssselect import CSSSelector
from cssselect import GenericTranslator
from functools import cmp_to_key, lru_cache
import copy

SVG_NS = "http://www.w3.org/2000/svg"
NSMAP = {None: SVG_NS}


class _SVGDefaultNamespaceTranslator(GenericTranslator):
    """Ensure bare element selectors target the SVG namespace."""

    def __init__(self, default_prefix="svg"):
        super().__init__()
        self._default_prefix = default_prefix

    def xpath_element(self, selector):
        if (
            self._default_prefix
            and selector.namespace is None
            and selector.element is not None
        ):
            selector = selector.__class__(self._default_prefix, selector.element)
        return super().xpath_element(selector)


_SVG_NAMESPACE_PREFIX = "svg"
_SVG_CSS_TRANSLATOR = _SVGDefaultNamespaceTranslator(default_prefix=_SVG_NAMESPACE_PREFIX)
_SVG_CSS_NAMESPACES = {_SVG_NAMESPACE_PREFIX: SVG_NS}


@lru_cache(maxsize=128)
def _svg_css_selector(css):
    return CSSSelector(
        css,
        translator=_SVG_CSS_TRANSLATOR,
        namespaces=_SVG_CSS_NAMESPACES,
    )

def _normalize_attr_name(name):
    """Convert pythonic attr names (text_anchor) into SVG attrs (text-anchor)."""
    return name.replace("_", "-")


def _el(tag, **attrs):
    el = etree.Element(f"{{{SVG_NS}}}{tag}", nsmap=NSMAP)
    for k, v in attrs.items():
        el.set(_normalize_attr_name(k), str(v))
    return el


def _to_float_tuple(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return (float(value[0]), float(value[1]))
    raise ValueError("Position values must be length-2 iterables of numbers")


def _hex_components(color):
    if not isinstance(color, str):
        return None
    c = color.strip()
    if c.startswith("#"):
        c = c[1:]
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return None
    try:
        return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _darker_hex(color, factor=0.7):
    comps = _hex_components(color)
    if not comps:
        return color
    darker = tuple(max(0, min(255, int(c * factor))) for c in comps)
    return "#%02x%02x%02x" % darker


def _attr_lookup(obj, candidates, default=None):
    for key in candidates:
        try:
            val = obj[key]
        except (KeyError, ValueError):
            continue
        if val is not None:
            return val
    return default


def _as_float(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return default

class Selection:
    _data_binding = {}

    def __init__(self, elements):
        # elements: list[etree._Element]
        self.elements = elements
        self._enter = []
        self._exit = []

    @classmethod
    def _get_data(cls, el):
        binding = cls._data_binding.get(id(el))
        if binding and binding[0] is el:
            return binding[1]
        return None

    @classmethod
    def _set_data(cls, el, value):
        cls._data_binding[id(el)] = (el, value)

    def append(self, tag, **attrs):
        """Append a child to every element in the selection; returns a new Selection of appended nodes."""
        kids = []
        for el in self.elements:
            child = _el(tag, **attrs)
            el.append(child)
            kids.append(child)
        return Selection(kids)

    def attr(self, name, value=None):
        """
        Set an attribute on all elements (returns self), or get the first value if value is None.
        """
        attr_name = _normalize_attr_name(name)
        if value is None:
            return self.elements[0].get(attr_name) if self.elements else None
        for idx, el in enumerate(self.elements):
            val = value
            if callable(value):
                val = value(Selection._get_data(el), idx, el)
            if val is None:
                continue
            el.set(attr_name, str(val))
        return self

    def attrs(self, **kvs):
        """Set multiple attributes at once."""
        for k, v in kvs.items():
            self.attr(k, v)
        return self

    def style(self, **kvs):
        """Merge into the 'style' attribute: style(fill='red', stroke='black')."""
        for idx, el in enumerate(self.elements):
            current = {}
            if el.get("style"):
                for pair in el.get("style").split(";"):
                    if pair.strip():
                        k, _, v = pair.partition(":")
                        current[k.strip()] = v.strip()
            for k, v in kvs.items():
                val = v
                if callable(v):
                    val = v(Selection._get_data(el), idx, el)
                if val is None:
                    continue
                current[_normalize_attr_name(k)] = str(val)
            el.set("style", ";".join(f"{k}:{v}" for k, v in current.items()))
        return self

    def text(self, s):
        for idx, el in enumerate(self.elements):
            val = s
            if callable(s):
                val = s(Selection._get_data(el), idx, el)
            if val is None:
                continue
            el.text = str(val)
        return self

    def datum(self, value=None):
        """Get or set bound data on the selection."""
        if value is None:
            return Selection._get_data(self.elements[0]) if self.elements else None
        for idx, el in enumerate(self.elements):
            current = Selection._get_data(el)
            new_val = value(current, idx, el) if callable(value) else value
            Selection._set_data(el, new_val)
        return self

    def data(self, data_iterable):
        """Bind a sequence of data objects to the selection (lengths must match)."""
        data_list = list(data_iterable)
        if len(data_list) != len(self.elements):
            raise ValueError(
                "MiniD3 Selection.data requires len(data) == number of selected elements"
            )
        for el, datum in zip(self.elements, data_list):
            Selection._set_data(el, datum)
        return self

    def select(self, css):
        """Select first match under each element; returns a Selection of all matches."""
        sel = _svg_css_selector(css)
        found = []
        for el in self.elements:
            matches = sel(el)
            if not matches:
                continue
            match = matches[0]
            Selection._set_data(match, Selection._get_data(el))
            found.append(match)
        return Selection(found)

    def select_all(self, css):
        """Select all matches under each element."""
        sel = _svg_css_selector(css)
        found = []
        for el in self.elements:
            matches = sel(el)
            if not matches:
                continue
            parent_data = Selection._get_data(el)
            for match in matches:
                Selection._set_data(match, parent_data)
            found.extend(matches)
        return Selection(found)

class MiniD3SVG:
    def __init__(self, width=800, height=600, viewBox=None, bg=None):
        self.root = _el("svg", width=str(width), height=str(height))
        if viewBox:
            self.root.set("viewBox", viewBox)
        if bg:
            # rect background
            rect = _el("rect", x="0", y="0", width="100%", height="100%", fill=bg)
            self.root.append(rect)
        self._defs = None

    @classmethod
    def from_string(cls, svg_text):
        doc = etree.fromstring(svg_text.encode("utf-8"))
        obj = cls.__new__(cls)
        obj.root = doc
        return obj

    @classmethod
    def from_file(cls, path):
        with open(path, "rb") as f:
            doc = etree.parse(f).getroot()
        obj = cls.__new__(cls)
        obj.root = doc
        return obj

    def select(self, css):
        sel = _svg_css_selector(css)
        found = sel(self.root)
        return Selection(found[:1])

    def select_all(self, css):
        sel = _svg_css_selector(css)
        return Selection(sel(self.root))

    def append(self, tag, **attrs):
        child = _el(tag, **attrs)
        self.root.append(child)
        return Selection([child])

    def add_style(self, css_text, **attrs):
        style_attrs = {"type": "text/css"}
        style_attrs.update({ _normalize_attr_name(k): v for k, v in attrs.items() })
        style_el = _el("style", **style_attrs)
        style_el.text = css_text
        # ensure styles sit near the top for readability
        self.root.insert(0, style_el)
        return Selection([style_el])

    def to_string(self, pretty=True):
        return etree.tostring(self.root, pretty_print=pretty, encoding="unicode")

    def save(self, path, pretty=True):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_string(pretty=pretty))


class NetworkSVG:
    """Convenience helper that renders igraph.Graph data into SVG primitives.

    Example
    -------
    >>> import igraph as ig
    >>> g = ig.Graph.GRG(10, 0.4)
    >>> coords = g.layout("grid").coords
    >>> g.vs["Position"] = [(x * 400, y * 300) for x, y in coords]
    >>> net = NetworkSVG(g, width=400, height=300)
    >>> degree_scale = scale_linear(domain=(0, max(g.degree())), range_=(6, 18))
    >>> net.nodes.select_all("circle").attr(
    ...     "r", lambda node, *_: degree_scale(g.degree(node.index))
    ... )
    >>> net.edges.attr("stroke", lambda edge, *_: "red" if edge["weight"] > 2 else "#999")
    >>> net.save("graph.svg")
    """

    def __init__(
        self,
        graph,
        width=800,
        height=600,
        bg=None,
        positions=None,
        node_generator=None,
        edge_generator=None,
        label_generator=None,
        directed_curves=False,
        directed_curve_factor=1.0,
        label_font_family="Roboto, Helvetica, Arial, sans-serif",
        fit_to_view=False,
        fit_margin=20,
    ):
        try:
            import igraph as ig  # noqa: F401  (type check / guidance)
        except ImportError:  # pragma: no cover - igraph should already be present
            raise ImportError("NetworkSVG requires python-igraph to be installed")

        self.graph = graph
        self._width = width
        self._height = height
        self.svg = MiniD3SVG(width=width, height=height, bg=bg)
        self._node_generator = node_generator
        self._edge_generator = edge_generator
        self._label_generator = label_generator
        self._fit_to_view = fit_to_view
        self._fit_margin = self._normalize_margin(fit_margin)
        self._original_positions = self._resolve_positions(positions)
        self.positions = self._fit_positions(self._original_positions)
        self._directed_curves = directed_curves
        self._directed_curve_factor = directed_curve_factor
        self._label_font_family = label_font_family

        self._edge_layer = self.svg.append("g", **{"class": "edge-visuals"})
        self._node_layer = self.svg.append("g", **{"class": "node-visuals"})
        self._label_layer = self.svg.append("g", **{"class": "label-visuals"})

        if self._label_font_family:
            self.add_style(
                f".label text {{ font-family: {self._label_font_family}; }}"
            )

        self.edges = self._build_edges()
        self.nodes = self._build_nodes()
        self.labels = self._build_labels()
        self.edge_visuals = self.edges
        self.node_visuals = self.nodes
        self.label_visuals = self.labels

    # ------------------------------------------------------------------
    # public API helpers
    def save(self, path, pretty=True, illustrator_safe=True):
        svg_text = self.to_string(pretty=pretty, illustrator_safe=illustrator_safe)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg_text)

    def to_string(self, pretty=True, illustrator_safe=True):
        root = self._export_root(illustrator_safe)
        return etree.tostring(root, pretty_print=pretty, encoding="unicode")

    def _export_root(self, illustrator_safe):
        if not illustrator_safe:
            return self.svg.root
        cloned = copy.deepcopy(self.svg.root)
        _prepare_label_strokes_for_illustrator(cloned)
        return cloned

    def add_style(self, css_text, **attrs):
        return self.svg.add_style(css_text, **attrs)

    def set_text_style(self, selector="text", **properties):
        if not properties:
            return None
        declarations = "; ".join(
            f"{_normalize_attr_name(k)}: {v}" for k, v in properties.items() if v is not None
        )
        if not declarations:
            return None
        css = f"{selector} {{{declarations};}}"
        return self.add_style(css)

    # ------------------------------------------------------------------
    def _resolve_positions(self, provided):
        if provided is not None:
            return self._positions_from_user(provided)

        attr_names = self.graph.vs.attribute_names()
        for candidate in ["Position", "position", "positions"]:
            if candidate in attr_names:
                values = self.graph.vs[candidate]
                return [self._coerce_position(v, idx) for idx, v in enumerate(values)]

        x_attr = next((name for name in ["x", "X"] if name in attr_names), None)
        y_attr = next((name for name in ["y", "Y"] if name in attr_names), None)
        if x_attr and y_attr:
            xs = self.graph.vs[x_attr]
            ys = self.graph.vs[y_attr]
            if len(xs) != len(ys):
                raise ValueError("x and y attribute lengths do not match")
            return [self._coerce_position((xs[i], ys[i]), i) for i in range(len(xs))]

        raise ValueError(
            "NetworkSVG requires node positions (provide positions=..., a 'Position' "
            "vertex attribute, or 'x'/'y' attributes)"
        )

    def _positions_from_user(self, provided):
        if callable(provided):
            coords = []
            for idx, vertex in enumerate(self.graph.vs):
                coords.append(self._coerce_position(provided(vertex, idx), idx))
            return coords
        coords = list(provided)
        if len(coords) != self.graph.vcount():
            raise ValueError("positions iterable must match number of vertices")
        return [self._coerce_position(pos, idx) for idx, pos in enumerate(coords)]

    def _coerce_position(self, value, idx):
        try:
            return _to_float_tuple(value)
        except ValueError as exc:
            raise ValueError(f"Invalid position for vertex {idx}: {value!r}") from exc

    def _normalize_margin(self, margin):
        def _to_float(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        if isinstance(margin, (int, float)):
            val = _to_float(margin)
            return (val, val, val, val)
        if isinstance(margin, (list, tuple)):
            if len(margin) == 2:
                hx, hy = (_to_float(margin[0]), _to_float(margin[1]))
                return (hx, hx, hy, hy)
            if len(margin) == 4:
                left, right, top, bottom = (
                    _to_float(margin[0]),
                    _to_float(margin[1]),
                    _to_float(margin[2]),
                    _to_float(margin[3]),
                )
                return (left, right, top, bottom)
        # fallback
        return (20.0, 20.0, 20.0, 20.0)

    def _fit_positions(self, positions):
        if not self._fit_to_view:
            return positions
        left, right, top, bottom = self._fit_margin
        avail_w = max(self._width - left - right, 1.0)
        avail_h = max(self._height - top - bottom, 1.0)
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)
        scale = min(avail_w / span_x, avail_h / span_y)
        used_w = span_x * scale
        used_h = span_y * scale
        extra_x = max(avail_w - used_w, 0.0) / 2.0
        extra_y = max(avail_h - used_h, 0.0) / 2.0
        offset_x = left + extra_x - min_x * scale
        offset_y = top + extra_y - min_y * scale
        fitted = []
        for x, y in positions:
            fitted.append((x * scale + offset_x, y * scale + offset_y))
        return fitted

    # ------------------------------------------------------------------
    def _build_edges(self):
        edge_elements = []
        edges = list(self.graph.es)
        for edge in edges:
            element = self._create_edge_element(edge)
            edge_elements.append(element)
        sel = Selection(edge_elements)
        if edge_elements:
            sel.data(edges)
        return sel

    def _build_nodes(self):
        node_elements = []
        vertices = list(self.graph.vs)
        for idx, vertex in enumerate(vertices):
            element = self._create_node_element(vertex, idx)
            node_elements.append(element)
        sel = Selection(node_elements)
        if node_elements:
            sel.data(vertices)
        return sel

    def _build_labels(self):
        label_elements = []
        label_vertices = []
        vertices = list(self.graph.vs)
        for idx, vertex in enumerate(vertices):
            element = self._create_label_element(vertex, idx)
            if element is not None:
                label_elements.append(element)
                label_vertices.append(vertex)
        sel = Selection(label_elements)
        if label_elements:
            sel.data(label_vertices)
        return sel

    # ------------------------------------------------------------------
    def _create_edge_element(self, edge):
        src = edge.source
        tgt = edge.target
        sx, sy = self.positions[src]
        tx, ty = self.positions[tgt]

        if self._edge_generator:
            spec = self._edge_generator(edge, (sx, sy), (tx, ty))
            return self._materialize(self._edge_layer, spec)

        stroke = self._edge_color(edge, src, tgt)
        width = self._edge_width(edge)
        opacity = _as_float(
            _attr_lookup(edge, ["Opacity", "opacity", "alpha"]), default=0.85
        )
        if (
            self._directed_curves
            and hasattr(self.graph, "is_directed")
            and self.graph.is_directed()
        ):
            path_d = self._directed_arc_path((sx, sy), (tx, ty))
            sel = self._edge_layer.append(
                "path",
                d=path_d,
                fill="none",
                stroke=stroke,
                stroke_width=width,
                opacity=opacity,
            )
            return sel.elements[0]
        sel = self._edge_layer.append(
            "line",
            x1=sx,
            y1=sy,
            x2=tx,
            y2=ty,
            stroke=stroke,
            stroke_width=width,
            opacity=opacity,
        )
        return sel.elements[0]

    def _edge_color(self, edge, src_idx, tgt_idx):
        color = _attr_lookup(edge, ["Color", "color", "stroke"])
        use_source = _as_bool(_attr_lookup(edge, ["UseSourceColor", "use_source_color"]))
        use_target = _as_bool(_attr_lookup(edge, ["UseTargetColor", "use_target_color"]))
        if not color and (use_source or use_target):
            node_idx = src_idx if use_source else tgt_idx
            color = self._node_fill(self.graph.vs[node_idx])
        return color or "#999999"

    def _edge_width(self, edge):
        width = _attr_lookup(edge, ["Width", "width", "stroke_width"])
        if width is None:
            weight = _attr_lookup(edge, ["weight", "Weight"])
            if weight is not None:
                width = 1.0 + 0.5 * _as_float(weight, 0)
        return _as_float(width, 1.0)

    def _directed_arc_path(self, start, end):
        sx, sy = start
        tx, ty = end
        dx = tx - sx
        dy = ty - sy
        dist = (dx ** 2 + dy ** 2) ** 0.5
        factor = max(self._directed_curve_factor, 0.51)
        radius = max(dist * factor, 1.0)
        large_arc = 0
        sweep = 1
        return (
            f"M {sx:.3f} {sy:.3f} "
            f"A {radius:.3f} {radius:.3f} 0 {large_arc} {sweep} {tx:.3f} {ty:.3f}"
        )

    def _create_node_element(self, vertex, idx):
        x, y = self.positions[idx]
        if self._node_generator:
            spec = self._node_generator(vertex, (x, y))
            parent = self._node_layer.append(
                "g", **{"class": "node", "transform": f"translate({x},{y})"}
            )
            if spec is not None:
                self._materialize(parent, spec)
            return parent.elements[0]

        radius = self._node_radius(vertex)
        fill = self._node_fill(vertex)
        stroke = self._node_outline(vertex, fill)
        stroke_width = self._node_outline_width(vertex)
        node_sel = self._node_layer.append(
            "g",
            **{"class": "node", "transform": f"translate({x},{y})"},
        )
        node_sel.append(
            "circle", r=radius, fill=fill, stroke=stroke, stroke_width=stroke_width
        )
        return node_sel.elements[0]

    def _create_label_element(self, vertex, idx):
        label_text = _attr_lookup(vertex, ["Label", "label", "name"])
        show_label = _attr_lookup(vertex, ["ShowLabel", "show_label"])
        if show_label is False:
            return None
        if not label_text:
            return None
        x, y = self.positions[idx]

        if self._label_generator:
            parent = self._label_layer.append(
                "g", **{"class": "label", "transform": f"translate({x},{y})"}
            )
            spec = self._label_generator(vertex, (x, y), label_text)
            if spec is not None:
                self._materialize(parent, spec)
            return parent.elements[0]

        node_fill = self._node_fill(vertex)
        text_fill = "#ffffff" if node_fill else "#1a1a1a"
        stroke = _darker_hex(node_fill) if node_fill else "#000000"
        stroke_width = _as_float(_attr_lookup(vertex, ["LabelOutline", "label_outline"]), 2.0)
        font_size = _attr_lookup(vertex, ["LabelSize", "label_size", "FontSize", "font_size"])
        label_group = self._label_layer.append(
            "g", **{"class": "label", "transform": f"translate({x},{y})"}
        )
        text_attrs = {
            "text_anchor": "middle",
            "dy": "0.35em",
            "fill": text_fill,
            "stroke": stroke,
            "stroke_width": stroke_width,
            "paint_order": "stroke fill",
            "stroke_linecap": "round",
            "stroke_linejoin": "round",
            "stroke_miterlimit": 1,
        }
        if font_size:
            text_attrs["font_size"] = font_size
        label_group.append("text", **text_attrs).text(label_text)
        return label_group.elements[0]

    # ------------------------------------------------------------------
    # sorting
    def sort_nodes(self, by=None, key=None, cmp=None, reverse=False):
        self._sort_layer(self.nodes, self._node_layer.elements[0], by, key, cmp, reverse)
        return self.nodes

    def sort_edges(self, by=None, key=None, cmp=None, reverse=False):
        self._sort_layer(self.edges, self._edge_layer.elements[0], by, key, cmp, reverse)
        return self.edges

    def sort_labels(self, by=None, key=None, cmp=None, reverse=False):
        if not self.labels.elements:
            return self.labels
        self._sort_layer(self.labels, self._label_layer.elements[0], by, key, cmp, reverse)
        return self.labels

    def _sort_layer(self, selection, parent_element, by, key, cmp_func, reverse):
        elements = list(selection.elements)
        if not elements:
            return
        data_items = [Selection._get_data(el) for el in elements]
        indices = list(range(len(elements)))

        def safe_attr(datum, attr_name):
            if datum is None or attr_name is None:
                return None
            try:
                return datum[attr_name]
            except (KeyError, ValueError):
                return getattr(datum, attr_name, None)

        if cmp_func is not None:
            cmp_key = cmp_to_key(lambda i, j: cmp_func(data_items[i], data_items[j]))
            indices.sort(key=cmp_key, reverse=reverse)
        else:
            def resolve(i):
                datum = data_items[i]
                if key is not None:
                    return key(datum)
                if by is not None:
                    return safe_attr(datum, by)
                return getattr(datum, "index", i)

            def sort_key(i):
                value = resolve(i)
                return (value is None, value)

            indices.sort(key=sort_key, reverse=reverse)

        parent = parent_element
        sorted_elements = [elements[i] for i in indices]
        for el in sorted_elements:
            parent.append(el)
        selection.elements[:] = sorted_elements

    def _node_radius(self, vertex):
        size = _attr_lookup(vertex, ["Size", "size", "radius", "Radius"])
        return _as_float(size, 8.0)

    def _node_fill(self, vertex):
        color = _attr_lookup(vertex, ["Color", "color", "fill"])
        return color or "#4C78A8"

    def _node_outline(self, vertex, fill_color):
        outline = _attr_lookup(vertex, ["OutlineColor", "outline_color", "stroke"])
        if outline:
            return outline
        return _darker_hex(fill_color)

    def _node_outline_width(self, vertex):
        width = _attr_lookup(vertex, ["OutlineWidth", "outline_width", "stroke_width"])
        return _as_float(width, 1.0)

    def _materialize(self, parent_sel, spec):
        if spec is None:
            return parent_sel.elements[0]
        if isinstance(spec, Selection):
            return spec.elements[0]
        if isinstance(spec, tuple) and len(spec) == 2:
            tag, attrs = spec
            child = parent_sel.append(tag, **attrs)
            return child.elements[0]
        if isinstance(spec, dict) and "tag" in spec:
            tag = spec["tag"]
            attrs = spec.get("attrs", {})
            child = parent_sel.append(tag, **attrs)
            for sub in spec.get("children", []) or []:
                self._materialize(child, sub)
            return child.elements[0]
        if isinstance(spec, etree._Element):
            parent_sel.elements[0].append(spec)
            return spec
        raise ValueError(
            "Generator functions must return Selection, (tag, attrs), dict(tag=..), or Element"
        )


class LinearScale:
    """Tiny helper similar to d3.scaleLinear."""

    def __init__(self, domain=(0.0, 1.0), range_=(0.0, 1.0)):
        self._domain = tuple(map(float, domain))
        self._range = tuple(map(float, range_))

    def domain(self, values):
        if len(values) != 2:
            raise ValueError("LinearScale.domain expects two values")
        self._domain = tuple(map(float, values))
        return self

    def range(self, values):
        if len(values) != 2:
            raise ValueError("LinearScale.range expects two values")
        self._range = tuple(map(float, values))
        return self

    def __call__(self, value):
        d0, d1 = self._domain
        r0, r1 = self._range
        if d1 == d0:
            return r0
        t = (float(value) - d0) / (d1 - d0)
        return r0 + t * (r1 - r0)


class OrdinalScale:
    """Map discrete inputs to items in a range list (wraps around)."""

    def __init__(self, domain=None, range_=None):
        self._domain = list(domain or [])
        self._range = list(range_ or [])

    def domain(self, values):
        self._domain = list(values)
        return self

    def range(self, values):
        self._range = list(values)
        return self

    def __call__(self, value):
        if value not in self._domain:
            self._domain.append(value)
        if not self._range:
            raise ValueError("OrdinalScale requires a non-empty range list")
        idx = self._domain.index(value) % len(self._range)
        return self._range[idx]


def scale_linear(domain=(0.0, 1.0), range_=(0.0, 1.0)):
    return LinearScale(domain, range_)


def scale_ordinal(domain=None, range_=None):
    return OrdinalScale(domain, range_)


def _prepare_label_strokes_for_illustrator(root):
    """Duplicate label text nodes so Illustrator shows stroke underneath fill."""
    ns = {"svg": SVG_NS}
    label_groups = root.xpath(
        ".//svg:g[contains(concat(' ', normalize-space(@class), ' '), ' label ')]",
        namespaces=ns,
    )
    text_tag = f"{{{SVG_NS}}}text"
    for group in label_groups:
        texts = [child for child in list(group) if child.tag == text_tag]
        for text in texts:
            stroke = text.get("stroke")
            if not stroke:
                continue
            stroke_width = text.get("stroke-width")
            if stroke_width is not None:
                try:
                    if float(stroke_width) == 0.0:
                        continue
                except ValueError:
                    pass
            bg = copy.deepcopy(text)
            bg.set("fill", "none")
            bg.attrib.pop("paint-order", None)
            # keep stroke attributes on bg, remove from foreground
            for attr in list(text.attrib.keys()):
                if attr.startswith("stroke"):
                    bg.set(attr, text.get(attr))
                    del text.attrib[attr]
            text.attrib.pop("paint-order", None)
            group.insert(group.index(text), bg)
