"""Optional Plotly rendering check: pip install kaleido, then run this script."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.io as pio
from plotly.utils import PlotlyJSONEncoder
import app


def charts_in(node):
    if isinstance(node, dict):
        if node.get("type") == "Graph" and node.get("namespace") == "dash_core_components":
            yield node["props"]
        else:
            for child in node.values():
                yield from charts_in(child)
    elif isinstance(node, list):
        for child in node:
            yield from charts_in(child)


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent.parent / "artifacts" / "chart-check"
    folder.mkdir(parents=True, exist_ok=True)
    content = app.render("trends", "HU", "2026-01-01", "2026-10-13", [], "distance", "light", app.DEFAULT_GOALS, [], "", "newest", [], 0)[0]
    figures = list(charts_in(json.loads(json.dumps(content, cls=PlotlyJSONEncoder))))
    if len(figures) != 8:
        raise AssertionError(f"Expected 8 trend charts, got {len(figures)}")
    svg_paths = [folder / f"{chart['id']}.svg" for chart in figures]
    png_paths = [folder / f"{chart['id']}.png" for chart in figures]
    payloads = [chart["figure"] for chart in figures]
    heights = [int(chart["style"]["height"].removesuffix("px")) for chart in figures]
    pio.write_images(payloads, svg_paths, format="svg", width=740, height=heights)
    pio.write_images(payloads, png_paths, format="png", width=740, height=heights, scale=2)
    for chart, path in zip(figures, svg_paths):
        root = ET.parse(path).getroot()
        marks = [element for element in root.iter() if any(name in element.get("class", "").split() for name in ["js-line", "point", "box", "hm"])]
        if not marks:
            raise AssertionError(f"{path.name}: chart rendered without data marks")
        if int(chart["style"]["height"].removesuffix("px")) < 205:
            raise AssertionError(f"{path.name}: graph container too small")
        print(f"{chart['id']}: {len(marks)} rendered data marks, {chart['style']['height']} container")
