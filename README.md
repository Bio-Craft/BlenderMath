# BlenderMath

BlenderMath is a Manim-style mathematical animation runtime whose output remains native, editable Blender data.

## Runtime model

- `MObject` and `VGroup`: parented scene graph with local transforms, style, state snapshots, copying, and updaters.
- `Scene`: `construct`, `add`, `remove`, `play`, and `wait`, compiled to a deterministic Blender timeline.
- `Animation`: `Create`, GP stroke/fill `Write`, `FadeIn`, `FadeOut`, `Transform`, `TransformMatchingTex`, `MoveTo`, `Rotate`, `Scale`, and chained `.animate` mutations.
- `ValueTracker`: custom-property animation plus baked Python updaters for timeline scrubbing.
- Coordinates: `Axes`, `ThreeDAxes`, `NumberPlane`, `NumberLine`, numeric/axis labels, `c2p`, `p2c`, adaptive `plot`, and discontinuity splitting.
- Geometry: `Dot`, `Line`, 2D `Arrow`, Geometry Nodes `Arrow3D`, `Circle`, `Rectangle`, `Polyline`, `ThreeDAxes3D`, and `VGroup`.
- Simulation: deterministic RK4 caches visualized as native Blender geometry.
- Math: semantic `MathTex` tokens with an optional `blender_typst_importer` geometry backend.
- Colors: the complete ManimGL/3Blue1Brown palette (`BLUE_A` through `PURPLE_E`, `WHITE`, `ORANGE`, `COLORMAP_3B1B`, and the other standard constants).

The Blender API is isolated in `backend/blender_52`; the core package can run in ordinary Python and notebooks.

### Native representation strategy

- Grease Pencil owns planar paths, independent stroke/fill, `Create`/`Write`, and point-resampled morphs.
- Geometry Nodes owns reusable parameter-driven 3D assets. `Arrow3D` exposes start, end, shaft radius, tip radius, and tip length as modifier inputs; every instance shares one node group.
- Native curves, meshes, and cached samples remain available for spatial curves and simulations where they are a better editing surface.

The GP backend maps logical `Style.width` through a thinner canvas radius scale so axes, ticks, and graphs have consistent visual weight. Typst GP glyphs receive editable Subdivide and Smooth modifiers; their source strokes remain untouched for `Write` and morph animation. Compound glyph contours are grouped by nesting so overlapping CJK strokes remain filled without closing intentional counters and holes.

Geometry Nodes parameters participate in the normal scene timeline. For example, this changes the evaluated mesh by keyframing only the endpoint inputs:

```python
vector = Arrow3D((0, 0, 0), (1, 1, 1))
self.play(vector.animate.put_start_and_end_on((-1, 0, 0), (2, 1, 0)), run_time=2)
```

## Scene DSL

```python
from bmath import *

class Derivative(Scene):
    def construct(self):
        axes = NumberPlane(x_range=(-4, 4, 1), y_range=(-1, 8, 1))
        graph = axes.plot(lambda x: x * x)
        x = ValueTracker(-2, "x")
        point = Dot(axes.c2p(x.value, x.value**2))
        point.add_updater(lambda dot: dot.move_to(axes.c2p(x.value, x.value**2)))

        self.play(Create(axes))
        self.play(Create(graph))
        self.add(point)
        self.play(x.animate.set_value(2), run_time=4, rate_func=linear)
```

ManimGL color names are RGBA tuples and work directly with all style methods:

```python
circle = Circle(style=Style(color=BLUE_D, fill_color=TEAL_C, fill_opacity=0.6))
self.play(circle.animate.set_color(YELLOW))
```

In Blender, create a Text data block containing the scene, select it under **3D View > Sidebar > BlenderMath**, and use **Build Script Scene**. The bundled **Build Tracker Demo** creates the same dynamic workflow directly.

## Typst

`MathTex` stores source-level tokens for matching. When a scene contains `MathTex`, the Blender 5.2 backend imports `typst_express` from `typst_importer.typst_to_svg`. Install and enable `blender_typst_importer` separately; BlenderMath does not copy or vendor that GPL project. Math objects use Grease Pencil by default; pass `representation="CURVE"` or `"MESH"` when those forms better suit the workflow.

Grease Pencil math has no outline by default (`stroke_mode="NONE"`). Use `"MATCH_FILL"` for a same-color outline or `"BLACK"` for a black outline.

The backend supports both legacy top-level imports and Blender Extension namespaces such as `bl_ext.blender_org.typst_importer` by discovering configured repositories at runtime.

Math tokens can be queried and styled before Typst compilation without relying on SVG path ordering:

```python
equation = MathTex("$ integral_a^b f(x) dif x $")
equation.set_color_by_token("integral", (1, 0, 0))
integral_tokens = equation.get_tokens("integral")
```

Matching transforms automatically isolate ordinary variables, numbers, and operators. Use `substrings_to_isolate` for multi-glyph Typst constructs that should move as one term:

```python
left = MathTex("$ 2 a x + b = plus.minus sqrt(d) $", substrings_to_isolate=("plus.minus", "sqrt(d)"))
right = MathTex("$ x = (-b plus.minus sqrt(d)) / (2 a) $", substrings_to_isolate=("plus.minus", "sqrt(d)"))
self.play(TransformMatchingTex(left, right, align_token="=", path_arc=.15))
```

`MatchTermTransform` is an alias. `key_map={"x": "y"}` can pair renamed parts, unmatched source and target parts fade out and in, and `align_token` keeps a relation glyph fixed across differently sized formulas.

For Grease Pencil math, `Write` uses a native Build modifier for stroke growth and a fill-only Opacity modifier for the later fill reveal. With the default `stroke_mode="NONE"`, a same-color outline is temporarily revealed while writing, then fades as the glyph fill appears; the finished formula remains outline-free. `FadeIn` and `FadeOut` remain whole-object opacity animations.

Individual method animations may carry independent timing:

```python
self.play(
    left.animate(run_time=3, rate_func=linear).shift((6, 0, 0)),
    right.animate(run_time=3, rate_func=ease_in_out_sine).shift((6, 0, 0)),
)
```

Spatial layout uses recursive transformed bounds rather than object origins:

```python
label.next_to(graph, UP, buff=.3)
group.arrange(direction=RIGHT, buff=.5, aligned_edge=DOWN)
group.arrange_in_grid(rows=2, cols=3, buff=(.4, .3))
group.to_corner((1, 0, 1))
left.align_to(right, UP)
left.match_width(right)
```

The Blender backend samples rate functions into deterministic F-Curve keys, so custom easing does not depend on Blender's default Bezier handles.

Closed planar geometry can use separate stroke and fill styling:

```python
circle = Circle(style=Style(
    color=(0.1, 0.5, 1, 1),
    width=0.04,
    fill_color=(1, 0.2, 0.1, 1),
    fill_opacity=0.6,
))
```

Planar shapes use native Blender 5.2 Grease Pencil by default, with independently controllable stroke and fill. `Create` uses a Build modifier for the outline and a fill-only Opacity modifier for the later fill reveal.

All BlenderMath Grease Pencil objects, including imported Typst glyphs, disable Grease Pencil lighting so palette colors remain stable under scene lights.

`Dot` is a filled Grease Pencil mark by default, so it participates in `Create`, morphing, stroke, and fill animation. Use `Dot(..., representation="MESH")` when a volumetric 3D marker is needed. Short open strokes such as axes and ticks are automatically arc-length subdivided for smooth GP Build animation.

Coordinate systems support native Blender text labels without requiring Typst:

```python
axes = Axes()
axes.add_coordinates()
axes.add_axis_labels("x", "y")
line = NumberLine(include_numbers=True)
space = ThreeDAxes()
space.add_axis_labels("x", "y", "z")
```

Transforms support straight, circular-arc, and custom paths:

```python
self.play(Transform(source, target, path_arc=PI / 2))
self.play(Transform(source, target, path_func=my_path))
```

Closed Grease Pencil shapes also morph geometrically. BlenderMath resamples both boundaries by arc length, aligns loop direction/start, and writes editable GP keyframes and breakdowns:

```python
self.play(Transform(circle, Rectangle(width=3, height=2)), run_time=2)
```

Open polylines and continuous function graphs use the same arc-length correspondence and are baked to native Grease Pencil breakdown frames:

```python
source = axes.plot(lambda x: sin(x))
target = axes.plot(lambda x: 0.15 * x**2 - 1)
self.play(Transform(source, target), run_time=3)
```

Plain `Transform` between `MathTex` objects performs whole-formula visual morphing without character semantics: glyphs are paired in visual order, their Grease Pencil strokes are sampled from the imported Bezier outlines before point matching, and surplus glyphs fade out or in. This preserves smooth Typst contours throughout the morph. Use `TransformMatchingTex` when terms should preserve their identities.

`TransformMatchingTex` performs source-semantic matching and records part ids on compiled Grease Pencil glyphs. It does not yet parse arbitrary Typst syntax trees: function calls and complex constructs should be listed in `substrings_to_isolate`. Shape-only matching between unrelated terms and automatic algebraic equivalence matching remain future work. The backend raises a clear error when Typst Importer is unavailable.

## Tests

```powershell
E:\anaconda3\envs\Blender\python.exe -m unittest discover -s tests -v
```

`fake-bpy-module-5.2` is a static typing package, not a Blender runtime. Blender data-block integration must be tested with an actual Blender 5.2 executable.

## Feature examples

The `examples` package contains one scene per feature family. Blender's **Example** selector can build each scene directly:

| Scene | Demonstrates |
|---|---|
| `CreationExample` | Primitive geometry and `Create` |
| `TransformationsExample` | `.animate`, move, rotate, and scale |
| `FadingExample` | `FadeIn` and `FadeOut` |
| `FillAndStrokeExample` | independent planar fill and stroke |
| `SceneGraphExample` | nested child rotation and inherited parent transforms |
| `CoordinateSystemsExample` | labeled `Axes`, `NumberPlane`, `NumberLine`, `ThreeDAxes`, and `c2p` |
| `AxisScalingExample` | centered fixed-size axes change x units from 1 to 2; Typst GP labels update while the same function compresses horizontally |
| `GeometryNodes3DExample` | shared Geometry Nodes asset for endpoint-driven arrows plus ranged, ticked, labeled 3D axes |
| `FunctionGraphsExample` | adaptive sampling and discontinuities |
| `ParametricCurvesExample` | parametric and polar plotting |
| `ProbabilityDistributionExample` | growing binomial bars and a normal approximation |
| `TrackerUpdaterExample` | `ValueTracker` and baked updater motion |
| `TimelineExample` | parallel `play`, waits, and easing |
| `SimulationExample` | RK4 Lorenz simulation cache |
| `SpatialLayoutExample` | bounds-aware rows, grids, edge placement, and mixed object sizes |
| `MathTypstExample` | optional Typst `MathTex` import |
| `QuadraticDerivationExample` | semantic term motion, equality alignment, and a quadratic-formula derivation |
