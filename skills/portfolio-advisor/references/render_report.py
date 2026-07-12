#!/usr/bin/env python3
"""Render a portfolio-report HTML page from a compact JSON data file.

Usage:
    python3 render_report.py DATA.json [TEMPLATE.html] > OUT.html

Design contract
---------------
The advisor emits a small JSON payload (semantic values only: numbers, short
tone enums, text). This script:

  1. `prepare()` — computes every *presentational* value the design needs
     (progress-bar pixel widths, APY heat-map colors, tone -> color mapping).
     The model never hand-writes pixels or hex codes.
  2. `render()`  — a Mustache-subset engine fills `report-template.html`
     ({{scalar}} slots, {{#list}}..{{/list}} repeat blocks, {{^x}} inverted).

Stdlib only. No third-party dependencies.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
#  Layout constants (pixel geometry lifted from the Pencil export)            #
# --------------------------------------------------------------------------- #

ALLOC_BAR_W = 832      # composition allocation stacked bar, full width (px)
TOP_TRACK_W = 540      # top-positions bar track width (px)
TOP_CAP_PCT = 20.0     # bar reads share / cap; cap = single-holding cap
GAP_TRACK_W = 360      # gaps-section bar track width (px)
BTC_BAND_W = 244       # BTC band mini-bar track width (px)

# --------------------------------------------------------------------------- #
#  Tone palette — semantic status -> concrete colors                          #
# --------------------------------------------------------------------------- #
# Every dynamically-colored chip/badge/card resolves through one of these.
# `bg`/`text`/`border`/`accent` cover pills, number bubbles and accent bars.

TONES = {
    "good":    {"bg": "#E9F5E9", "text": "#2A6B2A", "border": "#A9D5A9", "accent": "#2A6B2A"},
    "warn":    {"bg": "#FFF3E0", "text": "#8A5300", "border": "#F3C97E", "accent": "#8A5300"},
    "bad":     {"bg": "#FDE6E6", "text": "#A02020", "border": "#F3A4A4", "accent": "#A02020"},
    "neutral": {"bg": "#FAFAFA", "text": "#999999", "border": "#ECECEC", "accent": "#999999"},
    "info":    {"bg": "#F0F5FF", "text": "#0066FF", "border": "#0066FF", "accent": "#0066FF"},
}

# Soft card backgrounds for the gaps list and changes grid (lighter than pills).
GAP_ROW_BG = {
    "bad":     {"bg": "#FFF5F5", "border": "#F3A4A4"},
    "warn":    {"bg": "#FFFAEF", "border": "#F3C97E"},
    "neutral": {"bg": "#FFFFFF", "border": "#ECECEC"},
    "good":    {"bg": "#FFFFFF", "border": "#ECECEC"},
}
CHANGE_CARD_BG = {
    "warn":    {"bg": "#FFF3E0", "border": "#F3C97E"},
    "bad":     {"bg": "#FFF5F5", "border": "#F3A4A4"},
    "good":    {"bg": "#FFFFFF", "border": "#ECECEC"},
    "neutral": {"bg": "#FFFFFF", "border": "#ECECEC"},
}
# Bold delta-text color for gap rows (distinct from the pill palette).
DELTA_TEXT = {"good": "#2A6B2A", "warn": "#C47A00", "bad": "#A02020", "neutral": "#999999"}

# Fixed category palette for allocation segments / legend / top-position bars.
CATEGORY_COLOR = {
    "stocks":  "#5B8BD6",
    "fiat":    "#D6A85B",
    "crypto":  "#8E5BD6",
    "deposit": "#5BC299",
}

# Gaps-list bar fill: semantic status of the bar (over cap / on target / etc.).
GAP_FILL = {
    "over":     "#F3A64B",   # above cap / above target — amber
    "ontarget": "#5BC299",   # inside band / on target — green
    "fiat":     "#D6A85B",   # fiat cash — gold
    "base":     "#5B8BD6",   # base-currency / equity — blue
}

# APY heat map: (lower_bound_inclusive, bg, text). First match wins, high->low.
APY_HEAT = [
    (12.0, "#C5E8D4", "#1F5A3A"),   # >=12%  best
    (9.0,  "#D8EDD0", "#355C20"),   # 9-12%  good
    (7.0,  "#F5E8C0", "#6A4D10"),   # 7-9%   mid
    (4.0,  "#F5D6C0", "#6A3010"),   # 4-7%   low
    (0.0,  "#FAFAFA", "#CCCCCC"),   # <4%    faint (same as empty)
]
APY_EMPTY = {"bg": "#FAFAFA", "text": "#CCCCCC"}   # missing cell ("—")


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #

def _px(frac: float, width: int) -> int:
    """Clamp fraction to [0,1] and scale to a pixel width."""
    return round(max(0.0, min(1.0, float(frac))) * width)


def _tone(name, fallback="neutral"):
    return TONES.get(name or fallback, TONES[fallback])


def _apy_heat(apy):
    if apy is None or apy == "":
        return dict(APY_EMPTY)
    try:
        v = float(apy)
    except (TypeError, ValueError):
        return dict(APY_EMPTY)
    for lo, bg, text in APY_HEAT:
        if v >= lo:
            return {"bg": bg, "text": text}
    return dict(APY_EMPTY)


# --------------------------------------------------------------------------- #
#  prepare() — semantic JSON -> fully-resolved template context               #
# --------------------------------------------------------------------------- #

def prepare(d: dict) -> dict:
    """Return a deep-ish copy of `d` enriched with presentational fields.

    Mutates nested dicts in place (input is a freshly-parsed JSON object, so
    that is safe). Only the fields the template actually reads are added.
    """

    # ---- Hero: MTD / vs pills carry a sign-driven tone ----
    hero = d.get("hero", {})
    for pill in ("mtd", "vs"):
        p = hero.get(pill)
        if isinstance(p, dict):
            p.update(_tone(p.get("tone")))

    # snapshot cards: optional value tone (defaults to ink #1A1A1A)
    for card in hero.get("snapshot", []):
        card["value_color"] = _tone(card["tone"])["text"] if card.get("tone") else "#1A1A1A"

    # ---- Actions: featured + compact rec cards ----
    actions = d.get("actions", {})
    feat = actions.get("featured")
    if isinstance(feat, dict):
        t = _tone(feat.get("tone", "good"))
        feat["accent"] = t["accent"]
        feat["pill_bg"] = t["bg"]
        feat["pill_text"] = t["text"]
        feat["impact_color"] = t["text"]
        feat["has_caveat"] = bool(feat.get("caveat"))
    for rec in actions.get("recs", []):
        t = _tone(rec.get("tone", "neutral"))
        rec["num_bg"] = t["accent"]
        rec["pill_bg"] = t["bg"]
        rec["pill_text"] = t["text"]

    # ---- Composition: allocation bar, legend, top positions ----
    comp = d.get("composition", {})
    for seg in comp.get("allocation", []):
        seg["color"] = CATEGORY_COLOR.get(seg.get("category"), seg.get("color", "#CCCCCC"))
        seg["width_px"] = _px(seg["pct"] / 100.0, ALLOC_BAR_W)
    for leg in comp.get("legend", []):
        leg["color"] = CATEGORY_COLOR.get(leg.get("category"), leg.get("color", "#CCCCCC"))
    cap = comp.get("top_cap_pct", TOP_CAP_PCT)
    comp["top_cap_label"] = f"cap {int(cap)}%"
    for pos in comp.get("top_positions", []):
        pos["color"] = CATEGORY_COLOR.get(pos.get("category"), pos.get("color", "#5B8BD6"))
        pos["fill_px"] = _px(pos["pct"] / cap, TOP_TRACK_W)

    # ---- Market: BTC / Fear&Greed / Yields ----
    market = d.get("market", {})
    btc = market.get("btc")
    if isinstance(btc, dict):
        t = _tone(btc.get("tone", "good"))
        btc["pill_bg"] = t["bg"]
        btc["pill_text"] = t["text"]
        btc["band_color"] = CATEGORY_COLOR["crypto"]
        btc["band_px"] = _px(btc.get("band_frac", 0.5), BTC_BAND_W)
    fng = market.get("fng")
    if isinstance(fng, dict):
        fng["color"] = _tone(fng.get("tone", "warn"))["text"]

    # ---- Yield matrix: header venues + per-cell heat ----
    matrix = d.get("yield_matrix", {})
    venues = matrix.get("venues", [])
    for row in matrix.get("rows", []):
        cells = []
        for v in venues:
            cell = dict(row.get("cells", {}).get(v["key"], {}))
            raw = cell.get("apy")
            cell.update(_apy_heat(raw))
            apy_val = None                      # empty unless apy parses as a number
            if raw is not None:
                try:
                    apy_val = float(raw)
                except (TypeError, ValueError):
                    apy_val = None
            cell["empty"] = apy_val is None
            cell["apy_display"] = "—" if apy_val is None else f"{apy_val:.2f}%"
            cells.append(cell)
        row["cells_list"] = cells

    # ---- Gaps: risk strip badges + gap-list bars ----
    gaps = d.get("gaps", {})
    for card in gaps.get("risk", []):
        t = _tone(card.get("tone", "good"))
        card["badge_bg"] = t["bg"]
        card["badge_text"] = t["text"]
    for row in gaps.get("list", []):
        tone = row.get("tone", "neutral")
        bg = GAP_ROW_BG.get(tone, GAP_ROW_BG["neutral"])
        row["row_bg"] = bg["bg"]
        row["row_border"] = bg["border"]
        row["fill_color"] = GAP_FILL.get(row.get("bar"), "#5B8BD6")
        row["fill_px"] = _px(row.get("fill_frac", 0.0), GAP_TRACK_W)
        # delta text color has its own tone (a neutral row can carry a green delta)
        row["delta_color"] = DELTA_TEXT.get(row.get("delta_tone", tone), "#999999")
        row["has_mark"] = row.get("mark_frac") is not None
        if row["has_mark"]:
            # 2px marker centred on the target position, minus 1px half-width
            row["mark_px"] = _px(row["mark_frac"], GAP_TRACK_W)

    # ---- Macro timeline: color by window, split around the "today" marker ----
    macro = d.get("macro", {})
    before, after = [], []
    for ev in macro.get("events", []):
        when = ev.get("when", "past")   # past | future
        if when == "future":
            ev["bg"], ev["border"] = "#FFF3E0", "#F3C97E"
            after.append(ev)
        else:  # past
            ev["bg"], ev["border"] = "#FAFAFA", "#ECECEC"
            before.append(ev)
    macro["before"] = before
    macro["after"] = after

    # ---- Changes grid: card tone -> bg/border ----
    changes = d.get("changes", {})
    for row in changes.get("rows", []):
        for card in row.get("cards", []):
            cb = CHANGE_CARD_BG.get(card.get("tone", "neutral"), CHANGE_CARD_BG["neutral"])
            card["card_bg"] = cb["bg"]
            card["card_border"] = cb["border"]

    return d


# --------------------------------------------------------------------------- #
#  Mustache-subset template engine                                            #
# --------------------------------------------------------------------------- #
#  Supports: {{var}} (HTML-escaped), {{{var}}} / {{&var}} (raw),
#            {{#section}}...{{/section}} (list -> loop, dict -> push once,
#            truthy scalar -> render once, falsy/empty -> skip),
#            {{^section}}...{{/section}} (inverted), {{! comment }},
#            dotted keys a.b.c, and {{.}} for the current scalar item.

_TAG = re.compile(r"\{\{(\{.*?\}|[#/^&!]?.*?)\}\}", re.DOTALL)


class _Section:
    __slots__ = ("name", "inverted", "nodes")

    def __init__(self, name, inverted):
        self.name = name
        self.inverted = inverted
        self.nodes = []


def _parse(template: str):
    root = _Section(None, False)
    stack = [root]
    pos = 0
    for m in _TAG.finditer(template):
        text = template[pos:m.start()]
        if text:
            stack[-1].nodes.append(("text", text))
        pos = m.end()
        tag = m.group(1).strip()
        if not tag:
            continue
        sigil = tag[0]
        if sigil == "!":                       # comment
            continue
        if sigil == "#" or sigil == "^":       # open section
            sec = _Section(tag[1:].strip(), sigil == "^")
            stack[-1].nodes.append(("section", sec))
            stack.append(sec)
        elif sigil == "/":                     # close section
            name = tag[1:].strip()
            if len(stack) < 2 or stack[-1].name != name:
                raise ValueError(f"template: mismatched {{{{/{name}}}}}")
            stack.pop()
        elif sigil == "&":                     # raw
            stack[-1].nodes.append(("raw", tag[1:].strip()))
        elif sigil == "{":                     # {{{ raw }}}
            stack[-1].nodes.append(("raw", tag[1:-1].strip() if tag.endswith("}") else tag[1:].strip()))
        else:                                  # escaped variable
            stack[-1].nodes.append(("var", tag))
    tail = template[pos:]
    if tail:
        stack[-1].nodes.append(("text", tail))
    if len(stack) != 1:
        raise ValueError(f"template: unclosed section {{{{#{stack[-1].name}}}}}")
    return root


_MISSING = object()


def _lookup(stack, key):
    if key == ".":
        return stack[-1]
    parts = key.split(".")
    for scope in reversed(stack):
        if isinstance(scope, dict) and parts[0] in scope:
            val = scope[parts[0]]
            for p in parts[1:]:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    return _MISSING
            return val
    return _MISSING


def _truthy(v):
    if v is _MISSING or v is None or v is False:
        return False
    if isinstance(v, (list, tuple, dict, str)):
        return len(v) > 0
    return True


def _render_nodes(nodes, stack, out):
    for kind, node in nodes:
        if kind == "text":
            out.append(node)
        elif kind == "var":
            v = _lookup(stack, node)
            if v is not _MISSING and v is not None and v is not False:
                out.append(html.escape(str(v)))
        elif kind == "raw":
            v = _lookup(stack, node)
            if v is not _MISSING and v is not None and v is not False:
                out.append(str(v))
        elif kind == "section":
            v = _lookup(stack, node.name)
            if node.inverted:
                if not _truthy(v):
                    _render_nodes(node.nodes, stack, out)
                continue
            if not _truthy(v):
                continue
            if isinstance(v, list):
                for item in v:
                    stack.append(item)
                    _render_nodes(node.nodes, stack, out)
                    stack.pop()
            elif isinstance(v, dict):
                stack.append(v)
                _render_nodes(node.nodes, stack, out)
                stack.pop()
            else:                              # truthy scalar / bool
                _render_nodes(node.nodes, stack, out)


def render(template: str, ctx: dict) -> str:
    root = _parse(template)
    out: list[str] = []
    _render_nodes(root.nodes, [ctx], out)
    return "".join(out)


# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__ or "usage: render_report.py DATA.json [TEMPLATE.html]\n")
        return 2
    data_path = Path(argv[1])
    # Template defaults to the one shipped beside this script (the plugin's
    # references dir), so the caller only needs to pass the data file.
    tpl_path = Path(argv[2]) if len(argv) > 2 else Path(__file__).resolve().parent / "report-template.html"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    template = tpl_path.read_text(encoding="utf-8")
    ctx = prepare(data)
    out_html: str = render(template, ctx)
    sys.stdout.write(out_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
