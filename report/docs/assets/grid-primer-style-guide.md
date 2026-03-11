# Grid Primer Diagram Style Guide

This document defines the visual vocabulary, color palette, sizing conventions,
cumulative-layering treatment, and legend requirements for the six Grid Primer
SVG diagrams (Stages 1 through 6). All diagrams must conform to these rules so
the sequence reads as a single, coherent visual narrative.

---

## Color Palette

Every `fill` and `stroke` value in the diagrams must come from the palette
below. No `inherit`, `currentColor`, or unnamed colors are allowed.

### Element Colors

| Role | Hex | Usage |
|------|-----|-------|
| Bus fill | `none` | Bus circles are unfilled |
| Bus stroke | `#333333` | Dark gray outline for bus nodes |
| Generator stroke / fill | `#2e7d32` | Green for generator circles, lines, labels |
| Generator background | `#e8f5e9` | Light green fill for dispatch annotation boxes |
| Load stroke | `#c62828` | Red for load arrows, lines, labels |
| Load background | `#ffebee` | Light red fill for load annotation boxes |
| Line normal | `#1565c0` | Blue for uncongested transmission lines and flow arrows |
| Line background | `#e3f2fd` | Light blue fill for annotation boxes (e.g., N-1 box) |
| Line congested | `#e65100` | Orange for congested lines and thermal-limit indicators |
| Congestion background | `#ffccbc` | Light orange fill for thermal-limit bar background |
| Line tripped | `#b71c1c` | Dark red for tripped/contingency lines and X markers |
| Trip background | `#ffcdd2` | Light red fill for trip label boxes |
| LMP / annotation stroke | `#ff8f00` | Amber for LMP boxes and PTDF labels |
| LMP background | `#fff8e1` | Light amber fill for LMP annotation boxes |

### Neutral Colors

| Role | Hex | Usage |
|------|-----|-------|
| Primary text / bus labels | `#333333` | Bus label text and annotation body text |
| Secondary text / legend | `#666666` | Annotation and legend caption text |
| Tertiary text | `#999999` | Subtle secondary captions |
| Meter background | `#e0e0e0` | Gray fill for unfilled meter bars |

### Special Values

| Value | Usage |
|-------|-------|
| `none` | Explicit "no fill" on bus circles and load arrows |

---

## Symbol Vocabulary

Each element type uses a consistent visual shape across all six diagrams.

| Element | Shape | Notes |
|---------|-------|-------|
| **Bus** | Circle (unfilled, stroked `#333`) | Bus label (B1, B2, ...) centered inside |
| **Generator** | Circle with tilde (`~`) inside | Connected to bus by a horizontal line |
| **Load** | Downward-pointing triangle (polygon) | Connected to bus by a horizontal line, with a vertical stub above |
| **Transmission line** | Solid `<line>` element | Color depends on state (normal, congested, tripped) |
| **Flow arrow** | Filled `<polygon>` arrowhead | Placed on transmission lines to indicate direction |
| **Congestion marker** | Filled `<rect>` bar across congested line | Orange fill with binding-limit label |
| **Trip marker** | Two crossed `<line>` elements forming an X | Dark red, placed at midpoint of tripped line |
| **Annotation box** | `<rect>` with rounded corners (`rx`) | Color-coded by element type (green/red/amber/blue) |
| **Legend / caption** | `<text>` element(s) near bottom of diagram | Uses secondary text color `#666` |

---

## Sizing Conventions

| Property | Value | Notes |
|----------|-------|-------|
| Bus circle radius | 25 px | `r="25"` (diameter = 50 px) |
| Generator circle radius | 25--30 px | Slightly variable; 25 px in later stages, 30 px in Stage 1 |
| Line stroke width (normal) | 2 px | Highlighted (new) transmission lines |
| Line stroke width (dimmed) | 1 px | Prior-stage elements |
| Line stroke width (congested) | 3 px | Congested line in Stage 5 |
| Trip line stroke width | 2.5 px | Tripped line in Stage 6 |
| X-marker stroke width | 3 px | Trip X marker in Stage 6 |
| Label font size | 14 px | Bus labels (B1, B2, ...) |
| Generator label font size | 12--14 px | Generator name labels (G1, G2) |
| Tilde font size | 18--20 px | Generator tilde symbol |
| Annotation font size | 10--12 px | Dispatch values, LMP, captions |
| Font family | `Arial, sans-serif` | System-safe stack; no external fonts |
| viewBox | `0 0 800 500` | All diagrams use identical 800x500 landscape viewBox |

---

## Cumulative Layering Rules

The diagrams form a progressive sequence. Each stage highlights its new elements
at full opacity while dimming elements carried forward from prior stages.

### Opacity and Stroke Treatment

| Layer | Opacity | Stroke Width | Description |
|-------|---------|-------------|-------------|
| **Highlighted** (new) | `1.0` | Normal (2 px) or bold (3 px for congestion) | New elements introduced at this stage |
| **Dimmed** (prior) | `0.35` | Reduced (1 px) | Elements from earlier stages |

### Stage-Specific Rules

| Stage | Treatment |
|-------|-----------|
| **Stage 1** | All elements at full opacity (no dimming -- everything is new) |
| **Stage 2** | Stage 1 bus + generator dimmed; new bus, line, load, flow arrow highlighted |
| **Stage 3** | Stages 1-2 elements dimmed; new buses, generators, lines, PTDF labels highlighted |
| **Stage 4** | All topology dimmed; OPF annotations (dispatch boxes, LMP boxes) highlighted |
| **Stage 5** | All topology dimmed; congestion line, thermal bars, LMP decomposition highlighted |
| **Stage 6** | All topology dimmed; tripped line, X marker, re-dispatch boxes, N-1 box highlighted |

### Dimming Implementation

Dimmed elements use the `opacity` attribute on each individual SVG element:

```xml
<!-- Dimmed example -->
<circle cx="200" cy="250" r="25" fill="none" stroke="#333" stroke-width="1" opacity="0.35" />

<!-- Highlighted example (no opacity attribute = 1.0) -->
<circle cx="600" cy="250" r="25" fill="none" stroke="#333" stroke-width="2" />
```

---

## Legend Requirements

| Stage | Legend |
|-------|--------|
| **Stage 1** | Caption text describing the single-bus concept |
| **Stages 2--6** | Caption text at the bottom of the diagram explaining the stage's key concept. Stages 4--6 additionally include in-diagram annotation boxes that serve as implicit legends for new visual elements (dispatch boxes, LMP boxes, thermal bars, trip markers). |

All legend/caption text uses font size 12 px in color `#666666` and is
positioned near the bottom of the viewBox (y >= 430).

---

## SVG Hygiene Rules

1. **No raster images.** No `<image>` elements with `data:` URIs or external
   raster file references.
2. **No external dependencies.** No `<link>`, `@import`, external `@font-face`,
   or external `<use xlink:href="...">` references.
3. **File size limit.** Each SVG must be under 50 KB.
4. **Consistent viewBox.** All six diagrams use `viewBox="0 0 800 500"`
   (landscape, 8:5 aspect ratio).
5. **Self-contained.** Each SVG must render correctly without any external
   resources.
