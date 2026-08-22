"""Blender UI for building native BlenderMath scenes."""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty

from .backend.blender_52 import compile_scene
from .backend.blender_52.assets import create_curve_style_asset
from .core import Axes, Create, NumberPlane, Scene


class BlenderMathSettings(bpy.types.PropertyGroup):
    expression: StringProperty(name="f(x)", default="sin(x)")
    domain_min: FloatProperty(name="Min", default=-6.283185)
    domain_max: FloatProperty(name="Max", default=6.283185)
    samples: IntProperty(name="Base Samples", default=64, min=8, max=4096)
    number_plane: BoolProperty(name="Number Plane", default=True)
    animate_create: BoolProperty(name="Animate Create", default=True)
    scene_text: PointerProperty(name="Scene Script", type=bpy.types.Text)
    scene_class: StringProperty(name="Scene Class", default="")
    preset: EnumProperty(
        name="Preset",
        items=(
            ("AXES", "Axes", "Cartesian axes with ticks"),
            ("PLANE", "Number Plane", "Cartesian number plane"),
            ("UNIT_CIRCLE", "Unit Circle", "Number plane and unit circle"),
        ),
        default="PLANE",
    )
    example: EnumProperty(
        name="Example",
        items=(
            ("CREATION", "Creation", "Primitive Create animations"),
            ("TRANSFORMATIONS", "Transformations", "Move, scale, and rotate"),
            ("FADING", "Fading", "Fade in and fade out"),
            ("FILL_STROKE", "Fill / Stroke", "Independent planar fill and outline"),
            ("SCENE_GRAPH", "Scene Graph", "VGroup hierarchy"),
            ("COORDINATES", "Coordinates", "Axes, NumberPlane, and c2p"),
            ("AXIS_SCALING", "Axis Scaling", "Resample one function as coordinate units change"),
            ("GEOMETRY_NODES_3D", "Geometry Nodes 3D", "Endpoint-driven arrows and 3D axes"),
            ("FUNCTION_GRAPHS", "Function Graphs", "Adaptive and discontinuous plots"),
            ("PARAMETRIC", "Parametric", "Parametric and polar curves"),
            ("PROBABILITY", "Probability Distribution", "Growing binomial bars and a normal approximation"),
            ("QUADRATIC_DERIVATION", "Quadratic Derivation", "Typst term matching through the quadratic formula"),
            ("TRACKER", "Tracker / Updater", "Scrubbable dynamic point"),
            ("TIMELINE", "Timeline", "Parallel animation and easing"),
            ("SIMULATION", "Simulation", "RK4 Lorenz trajectory"),
            ("SPATIAL_LAYOUT", "Spatial Layout", "Bounds-aware arrange, grid, and edge placement"),
            ("MATH_TYPST", "MathTex (Typst)", "Requires blender_typst_importer"),
        ),
        default="CREATION",
    )


class BLENDERMATH_OT_build_plot(bpy.types.Operator):
    bl_idname = "blendermath.build_plot"
    bl_label = "Build Scene"
    bl_description = "Build axes, graph, and native timeline animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.blendermath
        if settings.domain_max <= settings.domain_min:
            self.report({"ERROR"}, "Domain maximum must exceed minimum")
            return {"CANCELLED"}
        try:
            scene = Scene("Plot Scene")
            axis_type = NumberPlane if settings.number_plane else Axes
            axes = axis_type(x_range=(settings.domain_min, settings.domain_max, 1), y_range=(-3, 3, 1))
            graph = axes.plot(settings.expression, domain=(settings.domain_min, settings.domain_max), samples=settings.samples)
            if settings.animate_create:
                scene.play(Create(axes), run_time=1.0)
                scene.play(Create(graph), run_time=1.5)
            else:
                scene.add(axes, graph)
            roots = compile_scene(scene)
        except (ValueError, ArithmeticError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        context.view_layer.objects.active = roots[0]
        roots[0].select_set(True)
        return {"FINISHED"}


class BLENDERMATH_OT_dynamic_demo(bpy.types.Operator):
    bl_idname = "blendermath.dynamic_demo"
    bl_label = "Build Tracker Demo"
    bl_description = "Build an animated x-squared graph with a tracker-driven point"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, _context):
        from .examples.derivative_scene import DerivativeScene
        compile_scene(DerivativeScene())
        return {"FINISHED"}


class BLENDERMATH_OT_build_example(bpy.types.Operator):
    bl_idname = "blendermath.build_example"
    bl_label = "Build Example"
    bl_description = "Build the selected Manim-style feature example"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from .examples.gallery import EXAMPLES
        key = context.scene.blendermath.example
        try:
            compile_scene(EXAMPLES[key]())
        except Exception as exc:
            self.report({"ERROR"}, f"{type(exc).__name__}: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class BLENDERMATH_OT_build_script(bpy.types.Operator):
    bl_idname = "blendermath.build_script"
    bl_label = "Build Script Scene"
    bl_description = "Execute the selected text block and build a BlenderMath Scene subclass"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.blendermath
        if settings.scene_text is None:
            self.report({"ERROR"}, "Choose a scene script text block")
            return {"CANCELLED"}
        namespace = {"__name__": "__blendermath_scene__", "__package__": None}
        try:
            exec(compile(settings.scene_text.as_string(), settings.scene_text.name, "exec"), namespace)
            candidates = [
                value for name, value in namespace.items()
                if isinstance(value, type) and issubclass(value, Scene) and value is not Scene
                and (not settings.scene_class or name == settings.scene_class)
            ]
            if not candidates:
                raise ValueError("No matching Scene subclass found")
            compile_scene(candidates[0]())
        except Exception as exc:
            self.report({"ERROR"}, f"{type(exc).__name__}: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class BLENDERMATH_OT_add_preset(bpy.types.Operator):
    bl_idname = "blendermath.add_preset"
    bl_label = "Add Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from .core import Circle
        preset = context.scene.blendermath.preset
        scene = Scene(f"{preset.title()} Preset")
        if preset == "AXES":
            scene.add(Axes())
        else:
            plane = NumberPlane()
            scene.add(plane)
            if preset == "UNIT_CIRCLE":
                scene.add(Circle(radius=plane.x_length / (plane.x_range[1] - plane.x_range[0]), name="Unit Circle"))
        compile_scene(scene, clear=False)
        return {"FINISHED"}


class BLENDERMATH_OT_add_asset(bpy.types.Operator):
    bl_idname = "blendermath.add_asset"
    bl_label = "Create Curve Asset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, _context):
        create_curve_style_asset()
        self.report({"INFO"}, "Created BM Curve Style")
        return {"FINISHED"}


class BLENDERMATH_PT_main(bpy.types.Panel):
    bl_label = "BlenderMath"
    bl_idname = "BLENDERMATH_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BlenderMath"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.blendermath
        layout.prop(settings, "expression")
        row = layout.row(align=True)
        row.prop(settings, "domain_min")
        row.prop(settings, "domain_max")
        layout.prop(settings, "samples")
        row = layout.row(align=True)
        row.prop(settings, "number_plane")
        row.prop(settings, "animate_create")
        layout.operator("blendermath.build_plot", icon="GRAPH")
        layout.operator("blendermath.dynamic_demo", icon="PLAY")
        layout.separator()
        layout.prop(settings, "example")
        layout.operator("blendermath.build_example", icon="PLAY")
        layout.separator()
        layout.prop(settings, "preset")
        layout.operator("blendermath.add_preset", icon="ADD")
        layout.separator()
        layout.prop(settings, "scene_text")
        layout.prop(settings, "scene_class")
        layout.operator("blendermath.build_script", icon="FILE_SCRIPT")
        layout.separator()
        layout.operator("blendermath.add_asset", icon="GEOMETRY_NODES")


_CLASSES = (
    BlenderMathSettings, BLENDERMATH_OT_build_plot, BLENDERMATH_OT_dynamic_demo,
    BLENDERMATH_OT_build_example,
    BLENDERMATH_OT_build_script, BLENDERMATH_OT_add_preset,
    BLENDERMATH_OT_add_asset, BLENDERMATH_PT_main,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.blendermath = PointerProperty(type=BlenderMathSettings)


def unregister():
    del bpy.types.Scene.blendermath
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
