# BlenderMath Repository Rules

## Mission

BlenderMath (`bmath`) is the reusable mathematical, simulation, and explanatory-animation layer for modern Blender. It is a library and Blender add-on, not a collection of project-specific scene scripts.

The Euler-Lotka film is the primary integration project. Treat failures or duplication found there as product feedback for bmath, while keeping demographic data, narration, Minecraft assets, and scene-specific staging out of this repository.

## Ownership Boundary

- Put reusable axes, coordinate conversion, geometry, Grease Pencil drawing, Typst text, layout, animation, matching, path motion, simulation, and Geometry Nodes capabilities in bmath.
- Put Euler-Lotka data, chapter timing, narration, villagers, materials, cameras, and shot composition in the Euler-Lotka repository.
- Before adding a local helper in a downstream scene, search bmath for an existing abstraction.
- If a downstream scene exposes a genuine missing primitive, implement it here first with a focused public API, tests, and an example; then consume it downstream.
- Do not duplicate an existing bmath object with raw `bpy` geometry. In particular, reuse `Axes`/`NumberLine`, `c2p`/`n2p`, `Polyline`, `Dot`, `Transform(path_func=...)`, Typst objects, and scene timeline primitives.
- Project-specific 3D data models may remain downstream until a general abstraction is justified. Current example: the Euler-Lotka annual 3D age-profile bars.

## Consistency Contract

- Visual objects and their labels must derive positions from the same coordinate object. Never hand-maintain a second timeline or axis beside an existing bmath axis.
- Animation state, transform origin, scale origin, stroke/fill opacity, and GP depth behavior must remain consistent across `Create`, `Write`, `FadeIn`, `FadeOut`, `Transform`, and matching transforms.
- Typst math/text must remain fill-only by default unless a caller explicitly requests a stroke.
- Text labels in explanatory scenes must use maximum-brightness white or the
  brightest semantic color supplied by the caller; avoid muted grey label text.
- Grease Pencil output is unlit by default and must work with the View Layer depth pass.
- Open and closed curves must both support resampling and geometric morphs without losing smoothness.
- Keep public behavior compatible with current Blender 5.2 unless a deliberate breaking change is documented.

## Verification

- Run `E:\anaconda3\envs\Blender\python.exe -m unittest tests.test_core` for every core change.
- Add or update an example for every user-facing feature; examples are executable specifications, not screenshots alone.
- For Blender compiler, GP, Geometry Nodes, Typst, depth, or render behavior, verify in the real Blender installation at `D:\Steam\steamapps\common\Blender\blender.exe`.
- Use the fake-bpy environment at `E:\anaconda3\envs\Blender` for fast Python checks, but do not treat it as a substitute for real Blender rendering.
- Preserve existing API patterns and keep tests proportional to blast radius.

## Repository Hygiene

- Keep generated distributions, caches, editor state, render output, temporary Typst files, and Blender backup files out of Git.
- Do not commit private downstream project assets or copied data.
- Keep commits scoped and describe behavioral changes, tests, and downstream implications.
