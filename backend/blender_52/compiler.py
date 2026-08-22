"""Blender 5.2 adapter: scene graph and timeline to native data blocks."""

from __future__ import annotations

from copy import deepcopy
import math

import bpy
from mathutils import Vector

from ...core.animation import (
    Animation, Create, FadeIn, FadeOut, TrackerAnimation, Transform,
    TransformMatchingTex, Write,
)
from ...core.scene import BakedUpdaterClip, Scene, TimelineClip
from ...core.mobject import TransformState
from ...core.morph import (
    align_curve_points, interpolate_points, prepare_morph_points, resample_curve,
    sample_cubic_bezier_path,
)

COLLECTION_NAME = "BlenderMath"
GP_RADIUS_SCALE = 0.35


def _linear_channel_to_srgb_byte(value):
    value = max(0.0, min(1.0, float(value)))
    srgb = 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
    return round(srgb * 255)


class BlenderCompiler:
    def __init__(
        self,
        scene: Scene,
        *,
        clear: bool = True,
        collection_name: str = COLLECTION_NAME,
    ):
        self.scene = scene.build()
        self.clear = clear
        self.collection_name = collection_name
        self.collection = None
        self.objects = {}
        self.materials = {}
        self.trackers = {}
        self.external_objects = {}
        self.fill_objects = {}
        self.math_material_baselines = {}

    def compile(self):
        # External importers create Grease Pencil drawings at the current
        # Blender frame.  Reset before compiling so Typst glyphs exist from the
        # beginning of a scrubbable scene, regardless of where the editor or a
        # previous preview render left the playhead.
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_set(1)
        self.collection = self._get_collection()
        for view_layer in getattr(bpy.context.scene, "view_layers", ()):
            view_layer.use_pass_z = True
        if self.clear:
            self._clear_collection()
        for root in self.scene.mobjects:
            self._compile_mobject(root)
        self._compile_timeline()
        bpy.context.scene.frame_end = self.scene.frame_end
        bpy.context.scene.render.fps = self.scene.fps
        bpy.context.scene.frame_set(1)
        return [self.objects[root.uid] for root in self.scene.mobjects]

    def _get_collection(self):
        collection = bpy.data.collections.get(self.collection_name)
        if collection is None:
            collection = bpy.data.collections.new(self.collection_name)
        if bpy.context.scene.collection.children.get(collection.name) is None:
            bpy.context.scene.collection.children.link(collection)
        return collection

    def _clear_collection(self):
        for obj in tuple(self.collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

    def _compile_mobject(self, mobject, parent=None):
        data = None
        if mobject.kind in {"curve", "arrow"}:
            morph_pairs = self._geometry_morph_pairs(mobject)
            geometry = self._initial_geometry(mobject)
            if morph_pairs:
                geometry = deepcopy(morph_pairs[0][0])
            data = self._curve_data(mobject, geometry, morph_pairs)
        elif mobject.kind == "shape_2d":
            data = self._grease_pencil_data(mobject, self._initial_geometry(mobject))
        elif mobject.kind == "dot":
            data = self._dot_data(mobject)
        elif mobject.kind == "text":
            data = self._text_data(mobject)
        elif mobject.kind == "geometry_nodes_arrow":
            data = bpy.data.meshes.new(f"{mobject.name} Geometry")
        obj = bpy.data.objects.new(mobject.name, data)
        self.collection.objects.link(obj)
        if obj.type == "GREASEPENCIL":
            obj.use_grease_pencil_lights = False
        obj["blendermath_uid"] = mobject.uid
        obj["blendermath_kind"] = mobject.kind
        obj.parent = parent
        needs_plane_adapter = mobject.kind in {"shape_2d", "text", "math"}
        if mobject.kind == "shape_2d" and mobject.parent is not None and mobject.parent.kind == "shape_2d":
            needs_plane_adapter = False
        if needs_plane_adapter:
            # GP fills triangulate in local XY; delta rotation maps that plane to
            # BlenderMath's XZ canvas. Blender fonts also originate in local XY.
            obj.delta_rotation_euler.x = math.pi / 2
        self.objects[mobject.uid] = obj
        self._apply_state(mobject, self._initial_state(mobject))
        if mobject.kind == "math":
            self._compile_math(mobject, obj)
        if data is not None:
            material = self._gp_material(mobject) if mobject.kind == "shape_2d" else self._material(mobject)
            data.materials.append(material)
            self.materials[mobject.uid] = material
            if mobject.kind == "curve" and mobject.geometry.get("cyclic") and mobject.style.fill_color and mobject.style.fill_opacity > 0:
                self._compile_fill(mobject, obj)
        if mobject.kind == "geometry_nodes_arrow":
            self._configure_arrow_3d(mobject, obj, self._initial_geometry(mobject))
        for child in mobject.children:
            self._compile_mobject(child, obj)
        return obj

    @staticmethod
    def _configure_arrow_3d(mobject, obj, geometry):
        from .assets import create_arrow_3d_asset

        group = create_arrow_3d_asset()
        modifier = obj.modifiers.new(name="BM Arrow 3D", type="NODES")
        modifier.node_group = group
        values = {
            "Start": geometry["start"],
            "End": geometry["end"],
            "Shaft Radius": geometry["shaft_radius"],
            "Tip Radius": geometry["tip_radius"],
            "Tip Length": geometry["tip_length"],
        }
        for item in group.interface.items_tree:
            if getattr(item, "item_type", None) == "SOCKET" and getattr(item, "in_out", None) == "INPUT":
                if item.name in values:
                    getattr(modifier.properties.inputs, item.identifier).value = values[item.name]

    def _keyframe_arrow_3d(self, target, initial_geometry, final_geometry, amount, frame):
        if target.kind != "geometry_nodes_arrow" or not initial_geometry or not final_geometry:
            return
        modifier = self.objects[target.uid].modifiers.get("BM Arrow 3D")
        if modifier is None:
            return
        names = {
            "Start": "start", "End": "end", "Shaft Radius": "shaft_radius",
            "Tip Radius": "tip_radius", "Tip Length": "tip_length",
        }
        for item in modifier.node_group.interface.items_tree:
            key = names.get(getattr(item, "name", ""))
            if key is None:
                continue
            left, right = initial_geometry[key], final_geometry[key]
            if isinstance(left, tuple):
                value = tuple(a + (b - a) * amount for a, b in zip(left, right))
            else:
                value = left + (right - left) * amount
            prop = getattr(modifier.properties.inputs, item.identifier)
            prop.value = value
            prop.keyframe_insert(data_path="value", frame=frame)

    def _initial_geometry(self, mobject):
        morph_pairs = self._geometry_morph_pairs(mobject)
        if morph_pairs:
            return deepcopy(morph_pairs[0][0])
        clips = [
            clip for clip in self.scene.timeline
            if isinstance(clip, TimelineClip)
            and getattr(clip.animation, "mobject", None) is mobject
            and clip.initial_geometry is not None
        ]
        return deepcopy(min(clips, key=lambda clip: clip.start_frame).initial_geometry) if clips else deepcopy(mobject.geometry)

    def _initial_state(self, mobject):
        clips = [
            clip for clip in self.scene.timeline
            if isinstance(clip, TimelineClip)
            and getattr(clip.animation, "mobject", None) is mobject
            and isinstance(clip.initial, TransformState)
        ]
        return deepcopy(min(clips, key=lambda clip: clip.start_frame).initial) if clips else deepcopy(mobject.state)

    def _geometry_morph_pairs(self, mobject):
        pairs = []
        for clip in self.scene.timeline:
            animation = getattr(clip, "animation", None)
            if not isinstance(animation, Transform):
                continue
            if animation.mobject is mobject and clip.initial_geometry.get("points") is not None:
                pairs.append((clip.initial_geometry, clip.final_geometry))
            for source, initial, final, *_rest in animation.child_morphs:
                if source is mobject:
                    pairs.append((initial, final))
        return pairs

    def _grease_pencil_data(self, mobject, geometry):
        grease_pencil = bpy.data.grease_pencils.new(f"{mobject.name} Geometry")
        grease_pencil.stroke_depth_order = "3D"
        layer = grease_pencil.layers.new("BlenderMath", set_active=True)
        frame = layer.frames.new(1)
        drawing = frame.drawing
        cyclic = bool(geometry.get("cyclic"))
        points = geometry["points"]
        if len(points) < 32:
            points = (
                _subdivide_closed_polyline(points, 32)
                if cyclic else _subdivide_open_polyline(points, 32)
            )
        self._populate_gp_drawing(drawing, points, mobject.style, cyclic=cyclic)
        return grease_pencil

    @staticmethod
    def _populate_gp_drawing(drawing, points, style, cyclic=False):
        drawing.add_strokes([len(points)])
        stroke = drawing.strokes[0]
        local_points = [(x, z, -y) for x, y, z in points]
        drawing.attributes["position"].data.foreach_set(
            "vector", [component for point in local_points for component in point]
        )
        stroke.cyclic = cyclic
        # Zero means "not part of a fill region" in the Blender 5.2 drawing
        # schema, even when the material itself has fill enabled.
        stroke.fill_id = 1 if cyclic else 0
        stroke.fill_opacity = style.fill_opacity
        for point in stroke.points:
            point.radius = max(0.00025, style.width * GP_RADIUS_SCALE)
            point.opacity = 1.0
        drawing.tag_positions_changed()

    @staticmethod
    def _text_data(mobject):
        text = bpy.data.curves.new(f"{mobject.name} Geometry", "FONT")
        text.body = mobject.geometry["text"]
        text.size = mobject.geometry["font_size"]
        text.align_x = "CENTER"
        text.align_y = "CENTER"
        text.extrude = 0.0
        return text

    @staticmethod
    def _gp_material(mobject):
        material = bpy.data.materials.new(f"BM {mobject.uid} GP Material")
        bpy.data.materials.create_gpencil_data(material)
        gp = material.grease_pencil
        gp.show_stroke = True
        gp.show_fill = bool(mobject.style.fill_color and mobject.style.fill_opacity > 0)
        gp.color = mobject.style.color
        fill = mobject.style.fill_color or mobject.style.color
        gp.fill_color = (*fill[:3], mobject.style.fill_opacity)
        material.diffuse_color = mobject.style.color
        return material

    def _compile_fill(self, mobject, stroke_obj):
        points = mobject.geometry["points"]
        mesh = bpy.data.meshes.new(f"{mobject.name} Fill Geometry")
        mesh.from_pydata(points, [], [tuple(range(len(points)))])
        mesh.update()
        fill_obj = bpy.data.objects.new(f"{mobject.name} Fill", mesh)
        self.collection.objects.link(fill_obj)
        fill_obj.parent = stroke_obj
        fill_obj["blendermath_kind"] = "fill"
        color = (*mobject.style.fill_color[:3], mobject.style.fill_opacity)
        material = bpy.data.materials.new(f"BM {mobject.uid} Fill Material")
        material.diffuse_color = color
        material.use_nodes = True
        principled = material.node_tree.nodes.get("Principled BSDF")
        alpha = None
        if principled:
            principled.inputs["Base Color"].default_value = color
            alpha = principled.inputs["Alpha"]
            alpha.default_value = mobject.style.fill_opacity
        mesh.materials.append(material)
        self.fill_objects[mobject.uid] = (fill_obj, material, alpha)

    def _compile_math(self, mobject, root):
        from .typst import resolve_typst_express

        typst_express = resolve_typst_express()
        typst_source, part_identifiers = mobject.render_source_with_part_ids()
        imported = typst_express(
            typst_source,
            name=f"BM_{mobject.uid}",
            origin_to_char=True,
            join_curves=False,
            convert_to_mesh=mobject.representation == "MESH",
            use_grease_pencil=mobject.representation == "GREASE_PENCIL",
        )
        glyphs = list(imported.objects)
        self._center_imported_glyphs(glyphs)
        for glyph in glyphs:
            if glyph.type == "GREASEPENCIL":
                glyph.data.stroke_depth_order = "3D"
                glyph.use_grease_pencil_lights = False
                subdivide = glyph.modifiers.new("BM Typst Subdivide", "GREASE_PENCIL_SUBDIV")
                # Typst already supplies the intended Bezier outline. Simple
                # subdivision adds points for Write/Transform without rounding
                # corners or changing stroke weight, which is especially
                # noticeable on CJK glyphs.
                subdivide.level = 2
                subdivide.subdivision_type = "SIMPLE"
            if getattr(glyph.data, "materials", None):
                # The importer reuses materials across glyphs. Write needs
                # independent alpha curves for each staggered glyph window.
                for index, material in enumerate(tuple(glyph.data.materials)):
                    glyph.data.materials[index] = material.copy()
            glyph.parent = root
            if self.collection.objects.get(glyph.name) is None:
                self.collection.objects.link(glyph)
        self.external_objects[mobject.uid] = glyphs
        baselines = {}
        for glyph in glyphs:
            part_key = None
            for material in glyph.data.materials:
                gp = getattr(material, "grease_pencil", None)
                if gp:
                    rgb = tuple(
                        _linear_channel_to_srgb_byte(component)
                        for component in gp.fill_color[:3]
                    )
                    if rgb in part_identifiers:
                        part_key = part_identifiers[rgb]
                        break
            if part_key is not None:
                glyph["blendermath_part_source"] = part_key[0]
                glyph["blendermath_part_occurrence"] = part_key[1]
            for material in glyph.data.materials:
                gp = getattr(material, "grease_pencil", None)
                if gp:
                    # Typst glyphs are closed GP shapes.  The importer may leave
                    # both visibility flags disabled, which only appears to work
                    # while Write's temporary outline is present.  Make the
                    # intended fill/stroke contract explicit so fill-only text
                    # remains visible after Write and can be faded reliably.
                    gp.show_fill = True
                    gp.show_stroke = mobject.stroke_mode != "NONE"
                    if part_key is not None:
                        color = mobject.token_colors.get(
                            part_key,
                            mobject.token_colors.get((part_key[0], None), mobject.style.color),
                        )
                        gp.fill_color = tuple(color)
                    # Typst imports black by default. BlenderMath's canvas
                    # defaults to white while semantic colors remain intact.
                    if max(gp.fill_color[:3]) < .08:
                        gp.fill_color = tuple(mobject.style.color)
                    if mobject.stroke_mode == "NONE":
                        gp.color = (*gp.fill_color[:3], 0.0)
                    elif mobject.stroke_mode == "MATCH_FILL":
                        gp.color = tuple(gp.fill_color)
                    else:
                        gp.color = (0.0, 0.0, 0.0, 1.0)
                    baselines[material.name_full] = (tuple(gp.color), tuple(gp.fill_color))
        self.math_material_baselines[mobject.uid] = baselines

    @staticmethod
    def _center_imported_glyphs(glyphs):
        """Place a MathTex root at the visual center of all imported glyphs."""
        corners = [
            glyph.matrix_world @ Vector(corner)
            for glyph in glyphs
            for corner in glyph.bound_box
        ]
        if not corners:
            return
        center = Vector(tuple(
            (min(point[index] for point in corners) + max(point[index] for point in corners)) / 2
            for index in range(3)
        ))
        for glyph in glyphs:
            glyph.location -= center

    def _curve_data(self, mobject, geometry=None, morph_pairs=()):
        geometry = geometry or mobject.geometry
        curve = bpy.data.curves.new(f"{mobject.name} Geometry", "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2
        curve.bevel_depth = mobject.style.width
        curve.bevel_resolution = 3
        spline = curve.splines.new("POLY")
        points = geometry["points"]
        if morph_pairs:
            count = max(64, *(len(item["points"]) for pair in morph_pairs for item in pair))
            points = prepare_morph_points(
                morph_pairs[0][0]["points"], morph_pairs[0][1]["points"],
                cyclic=bool(geometry.get("cyclic")), count=count,
            )[0]
        spline.points.add(len(points) - 1)
        spline.points.foreach_set("co", [value for point in points for value in (*point, 1.0)])
        spline.use_cyclic_u = geometry.get("cyclic", False)
        return curve

    def _dot_data(self, mobject):
        # Octahedron avoids operators/context and remains cheap for large point sets.
        radius = mobject.geometry["radius"]
        vertices = [(radius, 0, 0), (-radius, 0, 0), (0, radius, 0), (0, -radius, 0), (0, 0, radius), (0, 0, -radius)]
        faces = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
        mesh = bpy.data.meshes.new(f"{mobject.name} Geometry")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        return mesh

    def _material(self, mobject):
        material = bpy.data.materials.new(f"BM {mobject.uid} Material")
        material.diffuse_color = mobject.style.color
        material.use_nodes = True
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        principled = material.node_tree.nodes.get("Principled BSDF")
        if principled:
            base = principled.inputs.get("Base Color")
            if base:
                base.default_value = mobject.style.color
            alpha = principled.inputs.get("Alpha")
            if alpha:
                alpha.default_value = mobject.state.opacity
        return material

    def _apply_state(self, mobject, state, frame=None, keyframe=False):
        obj = self.objects[mobject.uid]
        obj.location = state.location
        obj.rotation_euler = state.rotation
        if mobject.kind in {"shape_2d", "text", "math"}:
            # Plane data is stored in local XY and rotated onto BlenderMath's
            # XZ canvas, so semantic depth/height scales map to local Z/Y.
            obj.scale = (state.scale[0], state.scale[2], state.scale[1])
        else:
            obj.scale = state.scale
        fully_transparent = state.opacity <= 1e-6
        obj.hide_render = not state.visible or fully_transparent
        obj.hide_viewport = not state.visible or fully_transparent
        obj.color = (*mobject.style.color[:3], state.opacity)
        if getattr(obj.data, "bevel_factor_end", None) is not None:
            obj.data.bevel_factor_end = state.draw_progress
        material = self.materials.get(mobject.uid)
        if material:
            material.diffuse_color = (*mobject.style.color[:3], state.opacity)
            principled = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
            alpha = principled.inputs.get("Alpha") if principled else None
            if alpha:
                alpha.default_value = state.opacity
        if keyframe and frame is not None:
            for path in ("location", "rotation_euler", "scale", "hide_render", "hide_viewport", "color"):
                obj.keyframe_insert(data_path=path, frame=frame)
            if getattr(obj.data, "bevel_factor_end", None) is not None:
                obj.data.keyframe_insert(data_path="bevel_factor_end", frame=frame)
            if material:
                material.keyframe_insert(data_path="diffuse_color", frame=frame)
                if alpha:
                    alpha.keyframe_insert(data_path="default_value", frame=frame)

    def _compile_timeline(self):
        for clip in self.scene.timeline:
            if isinstance(clip, BakedUpdaterClip):
                for frame, state in clip.samples:
                    self._apply_state(clip.mobject, state, frame, True)
                continue
            animation = clip.animation
            if isinstance(animation, TrackerAnimation):
                control = self.trackers.get(id(animation.tracker))
                if control is None:
                    control = bpy.data.objects.new(f"BM Tracker {animation.tracker.name}", None)
                    self.collection.objects.link(control)
                    control["value"] = clip.initial
                    self.trackers[id(animation.tracker)] = control
                control["value"] = clip.initial
                control.keyframe_insert(data_path='["value"]', frame=clip.start_frame)
                control["value"] = clip.final
                control.keyframe_insert(data_path='["value"]', frame=clip.end_frame)
                continue
            self._keyframe_animation(clip)

    def _keyframe_animation(self, clip: TimelineClip):
        animation = clip.animation
        if isinstance(animation, (Create, Write)):
            for member in animation.mobject.family():
                if member.kind == "shape_2d":
                    self._write_shape_grease_pencil(member, clip)
        if animation.mobject.kind == "math" and animation.mobject.uid in self.external_objects:
            self._keyframe_math(animation, clip)
        targets = list(animation.mobject.family()) if isinstance(animation, (Create, Write, FadeIn, FadeOut)) else [animation.mobject]
        for target in targets:
            if (
                target is not animation.mobject
                and target.kind == "math"
                and target.uid in self.external_objects
            ):
                child_animation = type(animation)(
                    target, run_time=animation.run_time, rate_func=animation.rate_func
                )
                child_clip = deepcopy(clip)
                child_clip.animation = child_animation
                self._keyframe_math(child_animation, child_clip)
            if target is animation.mobject:
                initial, final = deepcopy(clip.initial), deepcopy(clip.final)
                initial_style, final_style = clip.initial_style, clip.final_style
            else:
                initial = self._initial_state(target)
                final = deepcopy(initial)
                initial_style = final_style = deepcopy(target.style)
                if isinstance(animation, (Create, Write)):
                    initial.draw_progress, final.draw_progress = 0.0, 1.0
                elif isinstance(animation, FadeIn):
                    initial.opacity, final.opacity = 0.0, 1.0
                elif isinstance(animation, FadeOut):
                    initial.opacity, final.opacity = 1.0, 0.0
                    final.visible = False
            self._sample_state_animation(
                target, initial, final, clip,
                initial_style=initial_style, final_style=final_style,
            )
        if isinstance(animation, Transform):
            for child_morph in animation.child_morphs:
                if child_morph[0] is not animation.mobject:
                    self._sample_child_morph(child_morph, clip)
            for child_animation in animation.child_math_transforms:
                child_clip = deepcopy(clip)
                child_clip.animation = child_animation
                child_clip.initial, child_clip.final = child_animation.states()
                child_clip.initial_style, child_clip.final_style = child_animation.styles()
                child_clip.initial_geometry, child_clip.final_geometry = child_animation.geometries()
                self._keyframe_math(child_animation, child_clip)
                self._sample_state_animation(
                    child_animation.mobject, child_clip.initial, child_clip.final, child_clip,
                    child_clip.initial_style, child_clip.final_style,
                )

    def _write_shape_grease_pencil(self, mobject, clip):
        obj = self.objects[mobject.uid]
        build = obj.modifiers.get("BM Create Stroke") or obj.modifiers.new(
            name="BM Create Stroke", type="GREASE_PENCIL_BUILD"
        )
        build.mode = "SEQUENTIAL"
        build.transition = "GROW"
        build.time_mode = "PERCENTAGE"
        build.use_percentage = True
        fill = obj.modifiers.get("BM Create Fill") or obj.modifiers.new(
            name="BM Create Fill", type="GREASE_PENCIL_OPACITY"
        )
        fill.color_mode = "FILL"
        fill.use_uniform_opacity = True
        span = max(1, clip.end_frame - clip.start_frame)
        has_fill = bool(
            mobject.geometry.get("cyclic")
            and mobject.style.fill_color
            and mobject.style.fill_opacity > 0
        )
        stroke_end = (
            clip.start_frame + round(span * 0.72)
            if has_fill else clip.end_frame
        )
        for frame in range(clip.start_frame, clip.end_frame + 1):
            stroke_progress = (frame - clip.start_frame) / max(1, stroke_end - clip.start_frame)
            stroke_progress = max(0.0, min(1.0, stroke_progress))
            amount = clip.animation.rate_func(stroke_progress)
            build.percentage_factor = amount
            build.keyframe_insert(data_path="percentage_factor", frame=frame)
            fill_progress = max(0.0, min(1.0, (frame - stroke_end) / max(1, clip.end_frame - stroke_end)))
            fill.color_factor = clip.animation.rate_func(fill_progress)
            fill.keyframe_insert(data_path="color_factor", frame=frame)

    @staticmethod
    def _interpolate_state(initial, final, amount):
        def lerp(left, right):
            return tuple(a + (b - a) * amount for a, b in zip(left, right))

        return TransformState(
            location=lerp(initial.location, final.location),
            rotation=lerp(initial.rotation, final.rotation),
            scale=lerp(initial.scale, final.scale),
            opacity=initial.opacity + (final.opacity - initial.opacity) * amount,
            draw_progress=initial.draw_progress + (final.draw_progress - initial.draw_progress) * amount,
            visible=initial.visible if amount < 1.0 else final.visible,
        )

    def _sample_state_animation(self, target, initial, final, clip, initial_style=None, final_style=None):
        if isinstance(clip.animation, Transform):
            self._bake_gp_morph(target, clip.initial_geometry, clip.final_geometry, clip)
            self._bake_curve_morph(target, clip.initial_geometry, clip.final_geometry, clip)
        span = max(1, clip.end_frame - clip.start_frame)
        for frame in range(clip.start_frame, clip.end_frame + 1):
            progress = (frame - clip.start_frame) / span
            amount = max(0.0, min(1.0, clip.animation.rate_func(progress)))
            state = self._interpolate_state(initial, final, amount)
            if target is clip.animation.mobject and isinstance(clip.animation, Transform):
                state.location = self._path_location(clip.animation, initial.location, final.location, amount)
            self._apply_state(target, state, frame, True)
            style = self._interpolate_style(
                initial_style if initial_style is not None else clip.initial_style,
                final_style if final_style is not None else clip.final_style,
                amount,
            )
            self._apply_style(target, style, state.opacity, frame)
            if target is clip.animation.mobject:
                self._keyframe_arrow_3d(
                    target, clip.initial_geometry, clip.final_geometry, amount, frame
                )
            if (
                target.kind == "math"
                and target.uid in self.external_objects
                and not isinstance(clip.animation, (Create, Write, FadeIn, FadeOut, Transform))
            ):
                self._apply_math_style(target, style, amount, frame, opacity=state.opacity)
            if target.uid in self.fill_objects:
                self._keyframe_fill(target, state, frame, animation=clip.animation, progress=progress)

    def _sample_child_morph(self, child_morph, clip):
        target, initial_geometry, final_geometry, initial, final, initial_style, final_style = child_morph
        self._bake_gp_morph(target, initial_geometry, final_geometry, clip)
        self._bake_curve_morph(target, initial_geometry, final_geometry, clip)
        span = max(1, clip.end_frame - clip.start_frame)
        for frame in range(clip.start_frame, clip.end_frame + 1):
            progress = (frame - clip.start_frame) / span
            amount = max(0.0, min(1.0, clip.animation.rate_func(progress)))
            state = self._interpolate_state(initial, final, amount)
            style = self._interpolate_style(initial_style, final_style, amount)
            self._apply_state(target, state, frame, True)
            self._apply_style(target, style, state.opacity, frame)

    def _bake_curve_morph(self, target, initial_geometry, final_geometry, clip):
        if target.kind not in {"curve", "arrow"}:
            return
        if not initial_geometry or not final_geometry:
            return
        if initial_geometry.get("points") is None or final_geometry.get("points") is None:
            return
        source_cyclic = bool(initial_geometry.get("cyclic"))
        if source_cyclic != bool(final_geometry.get("cyclic")):
            raise ValueError("Curve morph requires matching open/closed topology")
        obj = self.objects[target.uid]
        if not obj.data.splines:
            return
        spline = obj.data.splines[0]
        source, final = prepare_morph_points(
            initial_geometry["points"], final_geometry["points"],
            cyclic=source_cyclic, count=len(spline.points),
        )
        span = max(1, clip.end_frame - clip.start_frame)
        for frame in range(clip.start_frame, clip.end_frame + 1):
            progress = (frame - clip.start_frame) / span
            amount = max(0.0, min(1.0, clip.animation.rate_func(progress)))
            points = interpolate_points(source, final, amount)
            for spline_point, point in zip(spline.points, points):
                spline_point.co = (*point, 1.0)
                spline_point.keyframe_insert(data_path="co", frame=frame)

    def _bake_gp_morph(self, target, source_geometry, final_geometry, clip):
        animation = clip.animation
        if target.kind != "shape_2d":
            return
        if not source_geometry or not final_geometry:
            return
        if source_geometry.get("points") is None or final_geometry.get("points") is None:
            return
        source_cyclic = bool(source_geometry.get("cyclic"))
        if source_cyclic != bool(final_geometry.get("cyclic")):
            raise ValueError("Grease Pencil morph requires matching open/closed topology")
        source, final = prepare_morph_points(
            source_geometry["points"], final_geometry["points"], cyclic=source_cyclic
        )
        obj = self.objects[target.uid]
        layer = obj.data.layers[0]
        span = max(1, clip.end_frame - clip.start_frame)
        for frame_number in range(clip.start_frame, clip.end_frame + 1):
            progress = (frame_number - clip.start_frame) / span
            amount = max(0.0, min(1.0, animation.rate_func(progress)))
            existing = next((frame for frame in layer.frames if frame.frame_number == frame_number), None)
            if existing is not None:
                layer.frames.remove(frame_number)
            frame = layer.frames.new(frame_number)
            frame.keyframe_type = "KEYFRAME" if frame_number in {clip.start_frame, clip.end_frame} else "BREAKDOWN"
            style = self._interpolate_style(clip.initial_style, clip.final_style, amount)
            self._populate_gp_drawing(
                frame.drawing, interpolate_points(source, final, amount), style,
                cyclic=source_cyclic,
            )

    @staticmethod
    def _interpolate_style(initial, final, amount):
        if initial is None or final is None:
            return final or initial

        def color(left, right):
            return tuple(a + (b - a) * amount for a, b in zip(left, right))

        initial_fill = initial.fill_color or initial.color
        final_fill = final.fill_color or final.color
        from ...core.mobject import Style
        return Style(
            color=color(initial.color, final.color),
            width=initial.width + (final.width - initial.width) * amount,
            fill_color=color(initial_fill, final_fill),
            fill_opacity=initial.fill_opacity + (final.fill_opacity - initial.fill_opacity) * amount,
        )

    def _apply_style(self, mobject, style, opacity, frame):
        if style is None:
            return
        material = self.materials.get(mobject.uid)
        if material is None:
            return
        gp = getattr(material, "grease_pencil", None)
        if gp:
            gp.color = (*style.color[:3], style.color[3] * opacity)
            fill = style.fill_color or style.color
            gp.fill_color = (*fill[:3], style.fill_opacity * opacity)
            gp.keyframe_insert(data_path="color", frame=frame)
            gp.keyframe_insert(data_path="fill_color", frame=frame)
            return
        material.diffuse_color = (*style.color[:3], style.color[3] * opacity)
        material.keyframe_insert(data_path="diffuse_color", frame=frame)

    def _apply_math_style(self, mobject, style, amount, frame, opacity=1.0):
        baselines = self.math_material_baselines.get(mobject.uid, {})
        target_fill = style.fill_color or style.color
        for glyph in self.external_objects[mobject.uid]:
            for material in glyph.data.materials:
                gp = getattr(material, "grease_pencil", None)
                baseline = baselines.get(material.name_full)
                if not gp or not baseline:
                    continue
                start_stroke, start_fill = baseline
                if mobject.stroke_mode == "NONE":
                    end_stroke = (*style.color[:3], 0.0)
                elif mobject.stroke_mode == "MATCH_FILL":
                    end_stroke = target_fill
                elif mobject.stroke_mode == "BLACK":
                    end_stroke = (0.0, 0.0, 0.0, target_fill[3])
                else:
                    end_stroke = style.color
                stroke = tuple(a + (b - a) * amount for a, b in zip(start_stroke, end_stroke))
                fill = tuple(a + (b - a) * amount for a, b in zip(start_fill, target_fill))
                gp.color = (*stroke[:3], stroke[3] * opacity)
                gp.fill_color = (*fill[:3], fill[3] * opacity)
                gp.keyframe_insert(data_path="color", frame=frame)
                gp.keyframe_insert(data_path="fill_color", frame=frame)

    @staticmethod
    def _path_location(animation, start, end, amount):
        if animation.path_func is not None:
            return tuple(float(value) for value in animation.path_func(start, end, amount))
        angle = animation.path_arc
        if abs(angle) < 1e-9:
            return tuple(a + (b - a) * amount for a, b in zip(start, end))
        sx, sy, sz = start
        ex, ey, ez = end
        dx, dz = ex - sx, ez - sz
        chord = (dx * dx + dz * dz) ** 0.5
        if chord < 1e-9:
            return start
        midpoint = ((sx + ex) / 2, (sz + ez) / 2)
        offset = chord / (2 * math.tan(angle / 2))
        cx = midpoint[0] - dz / chord * offset
        cz = midpoint[1] + dx / chord * offset
        vx, vz = sx - cx, sz - cz
        theta = angle * amount
        cosine, sine = math.cos(theta), math.sin(theta)
        return (
            cx + vx * cosine - vz * sine,
            sy + (ey - sy) * amount,
            cz + vx * sine + vz * cosine,
        )

    def _keyframe_fill(self, mobject, state, frame, animation, progress):
        fill_obj, material, alpha = self.fill_objects[mobject.uid]
        base_opacity = mobject.style.fill_opacity
        if isinstance(animation, (Create, Write)):
            reveal = max(0.0, min(1.0, (progress - 0.7) / 0.3))
            opacity = base_opacity * animation.rate_func(reveal)
        else:
            opacity = base_opacity * state.opacity
        fill_obj.color = (*mobject.style.fill_color[:3], opacity)
        material.diffuse_color = (*mobject.style.fill_color[:3], opacity)
        if alpha:
            alpha.default_value = opacity
        fill_obj.keyframe_insert(data_path="color", frame=frame)
        material.keyframe_insert(data_path="diffuse_color", frame=frame)
        if alpha:
            alpha.keyframe_insert(data_path="default_value", frame=frame)

    def _keyframe_math(self, animation, clip):
        glyphs = self.external_objects[animation.mobject.uid]
        if not glyphs:
            return
        if isinstance(animation, Transform) and animation.target.kind == "math":
            self._keyframe_math_transform(animation, clip)
            return
        span = max(1, clip.end_frame - clip.start_frame)
        write_glyphs = [glyph for glyph in glyphs if glyph.type == "GREASEPENCIL"]
        write_timings = self._staggered_write_timings(
            clip.start_frame, clip.end_frame, len(write_glyphs)
        )
        material_baselines = self.math_material_baselines.get(animation.mobject.uid, {})
        write_index = 0
        for index, glyph in enumerate(glyphs):
            if isinstance(animation, Write) and glyph.type == "GREASEPENCIL":
                start, end = write_timings[write_index]
                write_index += 1
                self._write_grease_pencil(
                    glyph,
                    start,
                    end,
                    animation.rate_func,
                    reveal_hidden_stroke=animation.mobject.stroke_mode == "NONE",
                    material_baselines=material_baselines,
                )
            elif glyph.type == "GREASEPENCIL" and isinstance(animation, (Create, FadeIn)):
                self._animate_gp_material_opacity(
                    glyph, clip, fade_in=True, material_baselines=material_baselines,
                )
            elif glyph.type == "GREASEPENCIL" and isinstance(animation, FadeOut):
                self._animate_gp_material_opacity(
                    glyph, clip, fade_in=False, material_baselines=material_baselines,
                )
            elif isinstance(animation, (Create, Write, FadeIn)):
                start = clip.start_frame + round(span * index / len(glyphs)) if isinstance(animation, Write) else clip.start_frame
                end = min(clip.end_frame, start + max(1, round(span / len(glyphs)))) if isinstance(animation, Write) else clip.end_frame
                self._sample_custom_opacity(glyph, start, end, 0.0, 1.0, animation.rate_func)
            elif isinstance(animation, FadeOut):
                self._sample_custom_opacity(glyph, clip.start_frame, clip.end_frame, 1.0, 0.0, animation.rate_func)

    def _keyframe_math_transform(self, animation, clip):
        target = animation.target
        target_root = bpy.data.objects.new(f"BM {target.uid} Morph Target", None)
        self.collection.objects.link(target_root)
        target_root.delta_rotation_euler.x = math.pi / 2
        self._compile_math(target, target_root)
        source_glyphs = [glyph for glyph in self.external_objects[animation.mobject.uid] if glyph.type == "GREASEPENCIL"]
        target_glyphs = [glyph for glyph in self.external_objects[target.uid] if glyph.type == "GREASEPENCIL"]
        source_baselines = self.math_material_baselines.get(animation.mobject.uid, {})
        target_baselines = self.math_material_baselines.get(target.uid, {})
        if isinstance(animation, TransformMatchingTex):
            self._align_math_target(animation, source_glyphs, target_glyphs)
            pairs, unmatched_source, extras = self._match_math_glyphs(
                animation, source_glyphs, target_glyphs,
            )
        else:
            pair_count = min(len(source_glyphs), len(target_glyphs))
            pairs = list(zip(source_glyphs[:pair_count], target_glyphs[:pair_count]))
            unmatched_source = source_glyphs[pair_count:]
            extras = target_glyphs[pair_count:]
        active_glyphs = []
        for source, destination in pairs:
            self._bake_math_glyph_morph(source, destination, clip)
            self._copy_math_part_key(destination, source)
            self._update_math_material_baselines(source, destination, source_baselines)
            active_glyphs.append(source)
            bpy.data.objects.remove(destination, do_unlink=True)
        for source in unmatched_source:
            self._animate_gp_material_opacity(
                source, clip, fade_in=False, material_baselines=source_baselines,
            )
        source_root = self.objects[animation.mobject.uid]
        for glyph in extras:
            glyph.parent = source_root
            self._animate_gp_material_opacity(
                glyph, clip, fade_in=True, material_baselines=target_baselines,
            )
        active_glyphs.extend(extras)
        self.external_objects[animation.mobject.uid] = active_glyphs
        source_baselines.update({
            name: colors
            for name, colors in target_baselines.items()
            if any(material.name_full == name for glyph in extras for material in glyph.data.materials)
        })
        bpy.data.objects.remove(target_root, do_unlink=True)
        self.external_objects.pop(target.uid, None)
        self.math_material_baselines.pop(target.uid, None)

    @staticmethod
    def _math_part_key(glyph):
        source = glyph.get("blendermath_part_source")
        if source is None:
            return None
        return source, int(glyph.get("blendermath_part_occurrence", 0))

    @staticmethod
    def _copy_math_part_key(source, destination):
        key = BlenderCompiler._math_part_key(source)
        if key is None:
            destination.pop("blendermath_part_source", None)
            destination.pop("blendermath_part_occurrence", None)
            return
        destination["blendermath_part_source"] = key[0]
        destination["blendermath_part_occurrence"] = key[1]

    @classmethod
    def _match_math_glyphs(cls, animation, source_glyphs, target_glyphs):
        targets_by_key = {}
        for glyph in target_glyphs:
            targets_by_key.setdefault(cls._math_part_key(glyph), []).append(glyph)
        pairs = []
        unmatched_source = []
        used_targets = set()
        for source in source_glyphs:
            key = cls._math_part_key(source)
            if key is None:
                unmatched_source.append(source)
                continue
            mapped_key = (animation.key_map.get(key[0], key[0]), key[1])
            candidates = targets_by_key.get(mapped_key, [])
            destination = next((item for item in candidates if item not in used_targets), None)
            if destination is None:
                unmatched_source.append(source)
                continue
            pairs.append((source, destination))
            used_targets.add(destination)
        extras = [glyph for glyph in target_glyphs if glyph not in used_targets]
        return pairs, unmatched_source, extras

    @classmethod
    def _align_math_target(cls, animation, source_glyphs, target_glyphs):
        token = animation.align_token
        if token is None:
            return
        source_anchor = next(
            (glyph for glyph in source_glyphs if (cls._math_part_key(glyph) or (None,))[0] == token),
            None,
        )
        target_token = animation.key_map.get(token, token)
        target_anchor = next(
            (glyph for glyph in target_glyphs if (cls._math_part_key(glyph) or (None,))[0] == target_token),
            None,
        )
        if source_anchor is None or target_anchor is None:
            raise ValueError(f"Alignment token not found in both formulas: {token!r}")
        delta = source_anchor.location - target_anchor.location
        for glyph in target_glyphs:
            glyph.location += delta

    @staticmethod
    def _update_math_material_baselines(source, destination, baselines):
        for source_material, target_material in zip(source.data.materials, destination.data.materials):
            source_gp = getattr(source_material, "grease_pencil", None)
            target_gp = getattr(target_material, "grease_pencil", None)
            if source_gp and target_gp:
                baselines[source_material.name_full] = (
                    tuple(target_gp.color), tuple(target_gp.fill_color),
                )

    def _bake_math_glyph_morph(self, source, destination, clip):
        source_strokes = self._extract_gp_strokes(source, clip.start_frame)
        target_strokes = self._extract_gp_strokes(destination, 1)
        count = max(len(source_strokes), len(target_strokes))
        pairs = []
        for index in range(count):
            left = source_strokes[index] if index < len(source_strokes) else None
            right = target_strokes[index] if index < len(target_strokes) else None
            reference = left or right
            if left is None:
                center = _point_average(right["points"])
                left = {**right, "points": [center] * len(right["points"])}
            if right is None:
                center = _point_average(left["points"])
                right = {**left, "points": [center] * len(left["points"])}
            cyclic = bool(left["cyclic"] and right["cyclic"])
            left_path = self._gp_stroke_path(left)
            right_path = self._gp_stroke_path(right)
            sample_count = max(64, len(left_path), len(right_path))
            start = resample_curve(left_path, sample_count, cyclic=cyclic)
            end = resample_curve(right_path, sample_count, cyclic=cyclic)
            end = align_curve_points(start, end, cyclic=cyclic)
            pairs.append((
                start,
                end,
                {
                    **reference,
                    "cyclic": cyclic,
                    "curve_type": 1,
                    "resolution": 1,
                    "left_handles": None,
                    "right_handles": None,
                    "left_handle_types": None,
                    "right_handle_types": None,
                },
            ))
        layer = source.data.layers[0]
        span = max(1, clip.end_frame - clip.start_frame)
        start_location = tuple(source.location)
        end_location = tuple(destination.location)
        material_pairs = []
        for source_material, target_material in zip(source.data.materials, destination.data.materials):
            source_gp = getattr(source_material, "grease_pencil", None)
            target_gp = getattr(target_material, "grease_pencil", None)
            if source_gp and target_gp:
                material_pairs.append((
                    source_gp,
                    tuple(source_gp.color), tuple(target_gp.color),
                    tuple(source_gp.fill_color), tuple(target_gp.fill_color),
                ))
        for frame_number in range(clip.start_frame, clip.end_frame + 1):
            progress = (frame_number - clip.start_frame) / span
            amount = max(0.0, min(1.0, clip.animation.rate_func(progress)))
            if any(frame.frame_number == frame_number for frame in layer.frames):
                layer.frames.remove(frame_number)
            frame = layer.frames.new(frame_number)
            frame.keyframe_type = "KEYFRAME" if frame_number in {clip.start_frame, clip.end_frame} else "BREAKDOWN"
            strokes = [
                {**metadata, "points": interpolate_points(start, end, amount)}
                for start, end, metadata in pairs
            ]
            self._populate_raw_gp_strokes(frame.drawing, strokes)
            source.location = self._path_location(
                clip.animation, start_location, end_location, amount,
            )
            source.keyframe_insert(data_path="location", frame=frame_number)
            for gp, start_stroke, end_stroke, start_fill, end_fill in material_pairs:
                gp.color = tuple(a + (b - a) * amount for a, b in zip(start_stroke, end_stroke))
                gp.fill_color = tuple(a + (b - a) * amount for a, b in zip(start_fill, end_fill))
                gp.keyframe_insert(data_path="color", frame=frame_number)
                gp.keyframe_insert(data_path="fill_color", frame=frame_number)

    @staticmethod
    def _extract_gp_strokes(obj, frame_number):
        layer = obj.data.layers[0]
        frames = [frame for frame in layer.frames if frame.frame_number <= frame_number]
        frame = max(frames, key=lambda item: item.frame_number) if frames else layer.frames[0]
        drawing = frame.drawing
        result = []
        point_offset = 0
        curve_type = drawing.attributes.get("curve_type")
        resolution = drawing.attributes.get("resolution")
        handle_left = drawing.attributes.get("handle_left")
        handle_right = drawing.attributes.get("handle_right")
        handle_type_left = drawing.attributes.get("handle_type_left")
        handle_type_right = drawing.attributes.get("handle_type_right")
        for stroke_index, stroke in enumerate(drawing.strokes):
            point_count = len(stroke.points)
            point_slice = slice(point_offset, point_offset + point_count)
            result.append({
                "points": [tuple(point.position) for point in stroke.points],
                "cyclic": stroke.cyclic,
                "fill_id": stroke.fill_id,
                "fill_opacity": stroke.fill_opacity,
                "material_index": stroke.material_index,
                "radius": sum(point.radius for point in stroke.points) / max(1, len(stroke.points)),
                "curve_type": curve_type.data[stroke_index].value if curve_type else 1,
                "resolution": resolution.data[stroke_index].value if resolution else 1,
                "left_handles": (
                    [tuple(item.vector) for item in handle_left.data[point_slice]]
                    if handle_left else None
                ),
                "right_handles": (
                    [tuple(item.vector) for item in handle_right.data[point_slice]]
                    if handle_right else None
                ),
                "left_handle_types": (
                    [item.value for item in handle_type_left.data[point_slice]]
                    if handle_type_left else None
                ),
                "right_handle_types": (
                    [item.value for item in handle_type_right.data[point_slice]]
                    if handle_type_right else None
                ),
            })
            point_offset += point_count
        return result

    @staticmethod
    def _gp_stroke_path(stroke):
        if (
            stroke.get("curve_type") == 2
            and stroke.get("left_handles") is not None
            and stroke.get("right_handles") is not None
        ):
            return sample_cubic_bezier_path(
                stroke["points"],
                stroke["left_handles"],
                stroke["right_handles"],
                cyclic=stroke["cyclic"],
                resolution=min(4, max(2, stroke.get("resolution", 4))),
            )
        return stroke["points"]

    @staticmethod
    def _populate_raw_gp_strokes(drawing, strokes):
        drawing.add_strokes([len(stroke["points"]) for stroke in strokes])
        positions = [component for stroke in strokes for point in stroke["points"] for component in point]
        drawing.attributes["position"].data.foreach_set("vector", positions)
        for output, source in zip(drawing.strokes, strokes):
            output.cyclic = source["cyclic"]
            output.fill_id = source["fill_id"]
            output.fill_opacity = source["fill_opacity"]
            output.material_index = source["material_index"]
            for point in output.points:
                point.radius = source["radius"]
                point.opacity = 1.0
        curve_type = drawing.attributes.get("curve_type")
        resolution = drawing.attributes.get("resolution")
        if resolution is None:
            resolution = drawing.attributes.new("resolution", "INT", "CURVE")
        for index, source in enumerate(strokes):
            curve_type.data[index].value = source.get("curve_type", 1)
            resolution.data[index].value = source.get("resolution", 1)

        drawing.tag_positions_changed()

    @staticmethod
    def _animate_gp_material_opacity(glyph, clip, fade_in, material_baselines=None):
        span = max(1, clip.end_frame - clip.start_frame)
        baselines = []
        material_baselines = material_baselines or {}
        for material in glyph.data.materials:
            gp = getattr(material, "grease_pencil", None)
            if gp:
                stroke, fill = material_baselines.get(
                    material.name_full, (tuple(gp.color), tuple(gp.fill_color))
                )
                baselines.append((gp, stroke, fill))
        for frame in range(clip.start_frame, clip.end_frame + 1):
            progress = (frame - clip.start_frame) / span
            amount = max(0.0, min(1.0, clip.animation.rate_func(progress)))
            opacity = amount if fade_in else 1.0 - amount
            for gp, stroke, fill in baselines:
                gp.color = (*stroke[:3], stroke[3] * opacity)
                gp.fill_color = (*fill[:3], fill[3] * opacity)
                gp.keyframe_insert(data_path="color", frame=frame)
                gp.keyframe_insert(data_path="fill_color", frame=frame)

    @staticmethod
    def _staggered_write_timings(start, end, count, lag_ratio=0.05):
        """Return Manim-style overlapping glyph windows across one animation span."""
        if count <= 0:
            return []
        span = max(1, end - start)
        duration = span / (1.0 + lag_ratio * (count - 1))
        offset = duration * lag_ratio
        timings = []
        for index in range(count):
            glyph_start = start + round(index * offset)
            glyph_end = min(end, glyph_start + max(2, round(duration)))
            timings.append((glyph_start, glyph_end))
        return timings

    @staticmethod
    def _sample_custom_opacity(obj, start, end, initial, final, rate_func):
        span = max(1, end - start)
        for frame in range(start, end + 1):
            amount = max(0.0, min(1.0, rate_func((frame - start) / span)))
            obj["opacity"] = initial + (final - initial) * amount
            obj.keyframe_insert(data_path='["opacity"]', frame=frame)

    @staticmethod
    def _write_grease_pencil(
        obj, start, end, rate_func, reveal_hidden_stroke=False,
        material_baselines=None,
    ):
        build = obj.modifiers.new(name="BM Write Stroke", type="GREASE_PENCIL_BUILD")
        build.mode = "SEQUENTIAL"
        build.transition = "GROW"
        build.time_mode = "PERCENTAGE"
        build.use_percentage = True
        fill = obj.modifiers.new(name="BM Write Fill", type="GREASE_PENCIL_OPACITY")
        fill.color_mode = "FILL"
        fill.use_uniform_opacity = True
        material_baselines = material_baselines or {}
        baselines = []
        for material in obj.data.materials:
            gp = getattr(material, "grease_pencil", None)
            if gp:
                stroke, fill_color = material_baselines.get(
                    material.name_full, (tuple(gp.color), tuple(gp.fill_color))
                )
                baselines.append((gp, stroke, fill_color))
        span = max(1, end - start)
        stroke_end = start + round(span * (0.62 if reveal_hidden_stroke else 0.75))
        for frame in range(start, end + 1):
            stroke_progress = (frame - start) / max(1, stroke_end - start)
            stroke_progress = max(0.0, min(1.0, stroke_progress))
            amount = rate_func(stroke_progress)
            build.percentage_factor = amount
            build.keyframe_insert(data_path="percentage_factor", frame=frame)
            fill_progress = max(0.0, min(1.0, (frame - stroke_end) / max(1, end - stroke_end)))
            fill.color_factor = rate_func(fill_progress)
            fill.keyframe_insert(data_path="color_factor", frame=frame)
            stroke_fade = 1.0 - rate_func(fill_progress)
            for gp, stroke, fill_color in baselines:
                gp.fill_color = fill_color
                gp.color = (
                    (*fill_color[:3], fill_color[3] * stroke_fade)
                    if reveal_hidden_stroke else stroke
                )
                gp.keyframe_insert(data_path="color", frame=frame)
                gp.keyframe_insert(data_path="fill_color", frame=frame)


def compile_scene(scene: Scene, clear: bool = True):
    return BlenderCompiler(scene, clear=clear).compile()


def _point_average(points):
    return tuple(sum(point[index] for point in points) / len(points) for index in range(3))


def _subdivide_open_polyline(points, minimum_count):
    if len(points) < 2:
        return list(points)
    steps = max(1, math.ceil((minimum_count - 1) / (len(points) - 1)))
    result = [tuple(points[0])]
    for left, right in zip(points, points[1:]):
        result.extend(
            tuple(a + (b - a) * index / steps for a, b in zip(left, right))
            for index in range(1, steps + 1)
        )
    return result


def _subdivide_closed_polyline(points, minimum_count):
    if len(points) < 2:
        return list(points)
    steps = max(1, math.ceil(minimum_count / len(points)))
    result = []
    for left, right in zip(points, points[1:] + points[:1]):
        result.extend(
            tuple(a + (b - a) * index / steps for a, b in zip(left, right))
            for index in range(steps)
        )
    return result
