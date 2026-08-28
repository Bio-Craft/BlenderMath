import math
import unittest

from core import (
    BLUE, BLUE_C, BLUE_E, COLORMAP_3B1B, GREEN, RED, WHITE, YELLOW, Axes, Circle, Create, Dot, Expression, ExpressionError, FadeOut, Line, MathTex,
    NumberPlane, Rectangle, Scene, ThreeDAxes, Transform, TransformMatchingTex, Write,
    ValueTracker, VGroup, linear,
)
from core.scene import BakedUpdaterClip
from core.morph import prepare_morph_points, resample_curve, sample_cubic_bezier_path
from core.gp_fill import nested_fill_groups


class ExpressionTests(unittest.TestCase):
    def test_math_parameters_and_safety(self):
        expression = Expression("a * sin(x) + pi")
        self.assertAlmostEqual(expression(x=math.pi / 2, a=2), math.pi + 2)
        with self.assertRaises(ExpressionError):
            Expression("__import__('os').getcwd()")


class ColorTests(unittest.TestCase):
    def test_manimgl_palette_constants_are_rgba(self):
        self.assertEqual(BLUE, BLUE_C)
        self.assertEqual(BLUE_E, (28 / 255, 117 / 255, 138 / 255, 1.0))
        self.assertEqual(COLORMAP_3B1B, (BLUE_E, GREEN, YELLOW, RED))


class GreasePencilFillTests(unittest.TestCase):
    def test_nested_hole_shares_outer_fill_group(self):
        outer = [(0, 0), (4, 0), (4, 4), (0, 4)]
        hole = [(1, 1), (1, 3), (3, 3), (3, 1)]
        self.assertEqual(nested_fill_groups([outer, hole]), [1, 1])

    def test_overlapping_stroke_outlines_use_separate_fill_groups(self):
        horizontal = [(0, 1), (4, 1), (4, 2), (0, 2)]
        vertical = [(1, 0), (2, 0), (2, 4), (1, 4)]
        self.assertEqual(nested_fill_groups([horizontal, vertical]), [1, 2])


class SceneGraphTests(unittest.TestCase):
    def test_animating_nested_child_does_not_register_duplicate_scene_root(self):
        from core import Circle, Scene, VGroup

        child = VGroup(Circle(name="Child"), name="Child Group")
        root = VGroup(child, name="Root Group")
        scene = Scene()
        scene.add(root)
        scene.play(child.animate.shift((1, 0, 0)))
        self.assertEqual(scene.mobjects, [root])

    def test_arrow_3d_method_animation_captures_endpoint_geometry(self):
        from core import Arrow3D

        arrow = Arrow3D((0, 0, 0), (1, 0, 0))
        animation = arrow.animate.put_start_and_end_on((-1, 0, 0), (2, 1, 0)).build()
        start, end = animation.geometries()
        self.assertEqual(start["end"], (1.0, 0.0, 0.0))
        self.assertEqual(end["start"], (-1.0, 0.0, 0.0))
        self.assertEqual(end["end"], (2.0, 1.0, 0.0))
        self.assertEqual(arrow.end, (1.0, 0.0, 0.0))

    def test_parenting_and_copy_identity(self):
        left, right = Dot(), Dot((1, 0, 0))
        group = VGroup(left, right).shift((2, 0, 1))
        self.assertIs(left.parent, group)
        clone = group.copy()
        self.assertNotEqual(clone.uid, group.uid)
        self.assertNotEqual(clone[0].uid, left.uid)

    def test_dot_defaults_to_filled_grease_pencil(self):
        dot = Dot()
        self.assertEqual(dot.kind, "shape_2d")
        self.assertTrue(dot.geometry["cyclic"])
        self.assertEqual(dot.style.fill_color, WHITE)
        self.assertEqual(dot.style.fill_opacity, 1.0)
        self.assertEqual(Dot(representation="MESH").kind, "dot")

    def test_animate_builder_does_not_mutate_early(self):
        dot = Dot()
        builder = dot.animate.shift((2, 0, 0)).scale(3)
        self.assertEqual(dot.state.location, (0, 0, 0))
        scene = Scene(fps=10).add(dot).play(builder, run_time=2)
        self.assertEqual(dot.state.location, (2, 0, 0))
        self.assertEqual(scene.timeline[0].start_frame, 1)
        self.assertEqual(scene.timeline[0].end_frame, 21)

    def test_animation_builder_keeps_individual_rate_function(self):
        dot = Dot()
        scene = Scene().play(dot.animate(rate_func=linear).shift((1, 0, 0)))
        self.assertIs(scene.timeline[0].animation.rate_func, linear)

    def test_method_animation_captures_color_change(self):
        circle = Circle().set_fill((1, 0, 0, 1), 0.25)
        initial_color = circle.style.color
        scene = Scene().play(circle.animate.set_color((0, 1, 0, 1)))
        clip = scene.timeline[0]
        self.assertEqual(circle.kind, "shape_2d")
        self.assertEqual(clip.initial_style.color, initial_color)
        self.assertEqual(clip.final_style.color, (0, 1, 0, 1))
        self.assertEqual(clip.final_style.fill_color, (0, 1, 0, 1))
        self.assertEqual(clip.final_style.fill_opacity, 0.25)

    def test_next_to_uses_object_bounds(self):
        left = Rectangle(width=4, height=1)
        right = Circle(radius=1).next_to(left, (1, 0, 0), buff=.5)
        left_box, right_box = left.get_bounding_box(), right.get_bounding_box()
        self.assertAlmostEqual(right_box[0][0] - left_box[1][0], .5)

    def test_move_and_scale_use_visual_center_for_off_center_geometry(self):
        line = Line((2, 0, 0), (4, 0, 0))
        line.move_to((1, 0, 2))
        self.assertEqual(line.get_center(), (1, 0, 2))
        line.scale(2)
        self.assertEqual(line.get_center(), (1, 0, 2))
        self.assertAlmostEqual(line.get_width(), 4)

    def test_scale_about_point_keeps_explicit_anchor_fixed(self):
        line = Line((0, 0, 0), (2, 0, 0))
        line.scale_x(2, about_point=(0, 0, 0))
        minimum, maximum = line.get_bounding_box()
        self.assertEqual(minimum, (0, 0, 0))
        self.assertEqual(maximum, (4, 0, 0))

    def test_world_space_move_to_under_transformed_parent(self):
        child = Circle(radius=.5).shift((1, 0, 0))
        VGroup(child).scale(2).rotate(math.pi / 4)
        child.move_to((3, 0, 1))
        for actual, expected in zip(child.get_center(), (3, 0, 1)):
            self.assertAlmostEqual(actual, expected)

    def test_arrange_and_grid_respect_sizes(self):
        row = VGroup(Rectangle(width=1), Rectangle(width=3), Circle(radius=.5)).arrange(buff=.25)
        for left, right in zip(row.children, row.children[1:]):
            self.assertAlmostEqual(right.get_bounding_box()[0][0] - left.get_bounding_box()[1][0], .25)
        grid = VGroup(*(Rectangle(width=1 + index, height=1) for index in range(4))).arrange_in_grid(rows=2, cols=2, buff=(.3, .4))
        self.assertLess(grid[2].get_center()[2], grid[0].get_center()[2])

    def test_align_edges_and_frame_edges(self):
        reference = Rectangle(width=4, height=2).shift((1, 0, .5))
        item = Circle(radius=.5).align_to(reference, (1, 0, 0))
        self.assertAlmostEqual(item.get_bounding_box()[1][0], reference.get_bounding_box()[1][0])
        item.to_corner((1, 0, 1), buff=.5, frame_width=10, frame_height=6)
        maximum = item.get_bounding_box()[1]
        self.assertAlmostEqual(maximum[0], 4.5)
        self.assertAlmostEqual(maximum[2], 2.5)


class CoordinateTests(unittest.TestCase):
    def test_asymmetric_axes_cross_at_coordinate_zero(self):
        from core import Axes

        axes = Axes(x_range=(-4, 4, 1), y_range=(-1, 5, 1), x_length=8, y_length=6)
        x_axis, y_axis = axes.children[:2]
        origin = axes.c2p(0, 0)
        self.assertEqual(x_axis.start[2], origin[2])
        self.assertEqual(x_axis.end[2], origin[2])
        self.assertEqual(y_axis.start[0], origin[0])
        self.assertEqual(y_axis.end[0], origin[0])

    def test_asymmetric_axes_place_labels_at_actual_axis_ends(self):
        from core import Axes

        axes = Axes(
            x_range=(-0.75, 10.75, 1), y_range=(0, .3, .05),
            x_length=9.2, y_length=4.8,
        )
        labels = next(child for child in axes.children if child.name == "Axis Labels")
        x_end = axes.c2p(10.75, 0)
        y_end = axes.c2p(0, .3)
        self.assertEqual(labels[0].state.location, (x_end[0] + .3, x_end[1], x_end[2]))
        self.assertEqual(labels[1].state.location, (y_end[0], y_end[1], y_end[2] + .3))

    def test_geometry_nodes_three_d_axes_include_ticks_and_labels(self):
        from core import ThreeDAxes3D

        axes = ThreeDAxes3D(x_range=(-2, 2, 1), y_range=(-2, 2, 1), z_range=(-2, 2, 1))
        self.assertEqual(len([child for child in axes.children if "Axis 3D GN" in child.name]), 3)
        self.assertEqual(len([child for child in axes.children if "Tick" in child.name]), 12)
        labels = next(child for child in axes.children if child.name == "3D Axis Labels")
        self.assertEqual([label.geometry["text"] for label in labels.children], ["x", "y", "z"])

    def test_coordinate_systems_show_axis_labels_by_default(self):
        from core import Axes, NumberLine, NumberPlane, ThreeDAxes

        for coordinates in (Axes(), NumberPlane(), ThreeDAxes()):
            labels = [child for child in coordinates.children if "Axis Labels" in child.name]
            self.assertEqual(len(labels), 1)
        number_line = NumberLine()
        self.assertTrue(any(child.name == "Number Line Axis Label" for child in number_line.children))

    def test_arrow_3d_defaults_are_thinner_than_axis_length(self):
        from core import Arrow3D

        arrow = Arrow3D()
        self.assertEqual(arrow.geometry["shaft_radius"], .018)
        self.assertEqual(arrow.geometry["tip_radius"], .065)

    def test_c2p_p2c_round_trip_with_shift(self):
        axes = Axes(x_range=(-2, 6), y_range=(-4, 4), x_length=8, y_length=4).shift((3, 0, 2))
        point = axes.c2p(1.25, -2.5)
        x, y = axes.p2c(point)
        self.assertAlmostEqual(x, 1.25)
        self.assertAlmostEqual(y, -2.5)

    def test_number_plane_is_object_tree(self):
        plane = NumberPlane(x_range=(-2, 2, 1), y_range=(-1, 1, 1))
        self.assertGreater(len(plane.children), 4)
        self.assertTrue(all(child.parent is plane for child in plane))

    def test_axes_default_to_white(self):
        axes = Axes()
        self.assertTrue(all(child.style.color == WHITE for child in axes.children))

    def test_default_plane_uses_one_world_unit_per_coordinate_unit(self):
        plane = NumberPlane(x_range=(-8, 8, 2), y_range=(-2, 2, 0.5))
        self.assertEqual(plane.x_length / 16, plane.y_length / 4)
        self.assertEqual(plane.c2p(2, 0)[0] - plane.c2p(0, 0)[0], 2)

    def test_coordinate_labels_are_parented(self):
        axes = Axes(x_range=(-2, 2, 1), y_range=(-1, 1, 1))
        numbers = axes.add_coordinates()
        names = axes.add_axis_labels("u", "v")
        self.assertIs(numbers.parent, axes)
        self.assertIs(names.parent, axes)
        self.assertTrue(all(label.kind == "text" for label in numbers.children + names.children))

    def test_coordinate_labels_can_use_typst_grease_pencil(self):
        from core import MathTex

        axes = Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1))
        labels = axes.add_coordinates(label_type=MathTex)
        self.assertTrue(labels.children)
        self.assertTrue(all(isinstance(label, MathTex) for label in labels.children))
        self.assertTrue(all(label.representation == "GREASE_PENCIL" for label in labels.children))

    def test_number_line_labels_can_use_typst_grease_pencil(self):
        from core import MathTex, NumberLine

        number_line = NumberLine(
            x_range=(0, 30, 15),
            include_numbers=False,
            include_axis_label=False,
        )
        labels = number_line.add_numbers(exclude=(), label_type=MathTex)
        self.assertEqual(len(labels.children), 3)
        self.assertTrue(all(isinstance(label, MathTex) for label in labels.children))
        self.assertTrue(all(label.representation == "GREASE_PENCIL" for label in labels.children))

    def test_three_d_axes_round_trip(self):
        axes = ThreeDAxes(x_range=(-2, 2), y_range=(-3, 3), z_range=(-4, 4)).shift((1, 2, 3))
        point = axes.c2p(1.25, -1.5, 2.5)
        coordinates = axes.p2c(point)
        for actual, expected in zip(coordinates, (1.25, -1.5, 2.5)):
            self.assertAlmostEqual(actual, expected)

    def test_adaptive_plot_and_discontinuity(self):
        axes = Axes(x_range=(-2, 2), y_range=(-4, 4))
        parabola = axes.plot(lambda x: x * x, samples=8, tolerance=0.001)
        self.assertGreater(len(parabola[0].points), 8)
        reciprocal = axes.plot(lambda x: 1 / x, samples=32)
        self.assertGreaterEqual(len(reciprocal), 2)


class TimelineTests(unittest.TestCase):
    def test_explicit_transform_animations_share_center_and_anchor_semantics(self):
        from core import MoveTo, Rotate, Scale

        line = Line((2, 0, 0), (4, 0, 0))
        moved = MoveTo(line, (1, 0, 2))
        line.state = moved.end_state
        self.assertEqual(line.get_center(), (1, 0, 2))
        scaled = Scale(line, 2)
        line.state = scaled.end_state
        self.assertEqual(line.get_center(), (1, 0, 2))
        rotated = Rotate(line, math.pi / 2, about_point=(1, 0, 2))
        line.state = rotated.end_state
        for actual, expected in zip(line.get_center(), (1, 0, 2)):
            self.assertAlmostEqual(actual, expected)

    def test_axes_transform_collects_nested_math_label_transforms(self):
        from core import Axes, MathTex, Transform

        source = Axes(x_range=(-2, 2, 1), y_range=(-2, 2, 1))
        target = Axes(x_range=(-4, 4, 2), y_range=(-2, 2, 1))
        source.add_coordinates(label_type=MathTex)
        target.add_coordinates(label_type=MathTex)
        animation = Transform(source, target)
        self.assertEqual(len(animation.child_math_transforms), 8)
        self.assertTrue(all(item.mobject.kind == "math" for item in animation.child_math_transforms))

    def test_parallel_play_and_wait(self):
        a, b = Line(), Dot()
        scene = Scene(fps=24)
        scene.play(Create(a, run_time=2), Create(b, run_time=1)).wait(0.5)
        self.assertEqual(scene.timeline[0].start_frame, scene.timeline[1].start_frame)
        self.assertEqual(scene.frame_end, 61)

    def test_create_and_fade_capture_states(self):
        line = Line()
        scene = Scene().play(Create(line)).play(FadeOut(line))
        self.assertEqual(scene.timeline[0].initial.draw_progress, 0)
        self.assertEqual(scene.timeline[0].final.draw_progress, 1)
        self.assertFalse(scene.timeline[1].final.visible)

    def test_write_restores_opacity_after_fade_out(self):
        text = MathTex("$ x $")
        scene = Scene().play(FadeOut(text)).play(Write(text))
        write_clip = scene.timeline[1]
        self.assertEqual(write_clip.initial.opacity, 1.0)
        self.assertEqual(write_clip.final.opacity, 1.0)
        self.assertTrue(write_clip.final.visible)

    def test_tracker_bakes_updater_for_scrubbable_timeline(self):
        tracker = ValueTracker(0, "x")
        dot = Dot().add_updater(lambda mob: mob.move_to((tracker.value, 0, 0)))
        scene = Scene(fps=10).add(dot)
        scene.play(tracker.animate.set_value(2), run_time=1, rate_func=linear)
        baked = next(clip for clip in scene.timeline if isinstance(clip, BakedUpdaterClip))
        self.assertEqual(len(baked.samples), 11)
        self.assertEqual(baked.samples[0][1].location, (0, 0, 0))
        self.assertEqual(baked.samples[-1][1].location, (2, 0, 0))

    def test_transform_records_arc_and_custom_path(self):
        dot = Dot((-2, 0, 0))
        target = dot.copy().move_to((2, 0, 0))
        arc = Transform(dot, target, path_arc=math.pi / 2)
        self.assertAlmostEqual(arc.path_arc, math.pi / 2)
        custom = Transform(dot, target, path_func=lambda start, end, t: (0, 0, t))
        self.assertIsNotNone(custom.path_func)

    def test_transform_captures_geometry_and_updates_scene_state(self):
        circle = Circle(samples=12)
        target = Rectangle(width=2, height=1)
        scene = Scene().play(Transform(circle, target))
        clip = scene.timeline[0]
        self.assertEqual(len(clip.initial_geometry["points"]), 12)
        self.assertEqual(len(clip.final_geometry["points"]), 4)
        self.assertEqual(circle.geometry, target.geometry)

    def test_closed_curve_resampling_and_alignment(self):
        square = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
        sampled = resample_curve(square, 8, cyclic=True)
        self.assertEqual(len(sampled), 8)
        self.assertAlmostEqual(sampled[1][0], 0.0)
        start, end = prepare_morph_points(square, list(reversed(square)), cyclic=True, count=16)
        error = sum(sum((a - b) ** 2 for a, b in zip(left, right)) for left, right in zip(start, end))
        self.assertAlmostEqual(error, 0.0)

    def test_bezier_sampling_follows_handles_instead_of_anchor_polygon(self):
        points = [(0, 0, 0), (1, 0, 0)]
        sampled = sample_cubic_bezier_path(
            points,
            left_handles=[(0, 0, 0), (1, 0, 1)],
            right_handles=[(0, 0, 1), (1, 0, 0)],
            cyclic=False,
            resolution=4,
        )

        self.assertEqual(sampled[0], points[0])
        self.assertEqual(sampled[-1], points[-1])
        self.assertGreater(sampled[2][2], 0.7)

    def test_function_graph_transform_tracks_child_geometry(self):
        axes = Axes(x_range=(-2, 2), y_range=(-2, 4))
        graph = axes.plot(lambda x: x, samples=8)
        target = axes.plot(lambda x: x * x, samples=12)
        animation = Transform(graph, target)
        self.assertEqual(len(animation.child_morphs), 1)
        self.assertIs(animation.child_morphs[0][0], graph[0])
        scene = Scene().play(animation)
        self.assertEqual(graph[0].geometry, target[0].geometry)

class MathTests(unittest.TestCase):
    def test_rich_typst_text_does_not_instrument_plain_numbers(self):
        source = (
            '#set text(font: "Microsoft YaHei")\n'
            '#text(size: 15pt)[数据：印度喀拉拉乡村本地鸡研究（2016）]'
        )
        label = MathTex(source)

        rendered, identifiers = label.render_source_with_part_ids()

        self.assertEqual(rendered, source)
        self.assertEqual(identifiers, {})
        self.assertEqual(label.tokens, [])

    def test_rich_typst_text_only_instruments_explicit_math_regions(self):
        source = '#text[2016 年的增长率为 $ r = 2 $]'
        label = MathTex(source)

        rendered, identifiers = label.render_source_with_part_ids()

        self.assertNotEqual(rendered, source)
        self.assertTrue(identifiers)
        self.assertEqual([token.source for token in label.tokens], ["r", "=", "2"])
        self.assertIn("2016 年的增长率为", rendered)

    def test_matrix_layout_is_not_flattened_by_semantic_instrumentation(self):
        matrix = MathTex("$ mat(1; 2; 3) $")

        source, identifiers = matrix.render_source_with_part_ids()

        self.assertEqual(source, matrix.source)
        self.assertEqual(identifiers, {})

    def test_math_tex_defaults_to_white_filled_grease_pencil(self):
        from core import MathTex, WHITE

        label = MathTex("$ x = 1 $")
        self.assertEqual(label.style.color, WHITE)
        self.assertEqual(label.style.fill_color, WHITE)
        self.assertEqual(label.style.fill_opacity, 1.0)
        self.assertEqual(label.representation, "GREASE_PENCIL")

    def test_semantic_token_matching_tracks_occurrence(self):
        old = MathTex("$ x^2 + y^2 = r^2 $")
        new = MathTex("$ y^2 = r^2 - x^2 $")
        matches = old.matching_tokens(new)
        self.assertIn(("x", 0), [left.key for left, _ in matches])
        self.assertIn(("=", 0), [left.key for left, _ in matches])
        self.assertEqual(old.representation, "GREASE_PENCIL")
        self.assertEqual(old.stroke_mode, "NONE")

    def test_semantic_token_coloring_instruments_typst_source(self):
        equation = MathTex("$ integral_a^b f(x) dif x $")
        equation.set_color_by_token("integral", (1, 0, 0))
        self.assertIn('#text(fill: rgb("#ff0000"))[$ integral $]', equation.render_source())
        self.assertEqual(equation.get_tokens("integral")[0].source, "integral")
        function = MathTex("$ F(x) $").set_color_by_token("F", (1, 0, 0))
        with self.assertRaises(ValueError):
            function.render_source()

    def test_matching_parts_prefer_explicit_typst_terms(self):
        equation = MathTex(
            "$ x = plus.minus sqrt(b^2 - 4 a c) $",
            substrings_to_isolate=("plus.minus", "sqrt(b^2 - 4 a c)"),
        )
        sources = [part.source for part in equation.parts]
        self.assertIn("sqrt(b^2 - 4 a c)", sources)
        self.assertNotIn("b", sources)
        self.assertEqual(sources.count("plus.minus"), 1)

    def test_transform_matching_tex_matches_occurrences_and_options(self):
        source = MathTex("$ x + x = b $")
        target = MathTex("$ b = x - x $")
        animation = TransformMatchingTex(
            source, target, align_token="=", path_arc=math.pi / 6,
        )
        keys = [left.key for left, _right in animation.matching_parts()]
        self.assertIn(("x", 0), keys)
        self.assertIn(("x", 1), keys)
        self.assertIn(("=", 0), keys)
        self.assertEqual(animation.align_token, "=")
        self.assertAlmostEqual(animation.path_arc, math.pi / 6)

    def test_part_identifiers_do_not_replace_requested_visual_colors(self):
        equation = MathTex("$ integral_a^b f(x) dif x $")
        equation.set_color_by_token("integral", RED)
        source, identifiers = equation.render_source_with_part_ids()
        self.assertTrue(identifiers)
        self.assertIn('#text(fill: rgb("#fc6255"))[$ integral $]', source)


class ExampleTests(unittest.TestCase):
    def test_every_non_optional_example_builds(self):
        from examples.gallery import EXAMPLES
        for name, scene_type in EXAMPLES.items():
            if name == "MATH_TYPST":
                continue
            with self.subTest(example=name):
                scene = scene_type().build()
                self.assertGreater(len(scene.mobjects), 0)
                self.assertGreater(scene.frame_end, 1)

    def test_probability_example_grows_bars_before_drawing_curve(self):
        from examples.probability_distribution import ProbabilityDistributionExample

        scene = ProbabilityDistributionExample().build()
        bars = [
            clip for clip in scene.timeline
            if getattr(clip.animation, "mobject", None).name.startswith("Binomial Bar")
        ]
        labels = [
            clip for clip in scene.timeline
            if getattr(clip.animation, "mobject", None).name.startswith("Probability Label")
        ]
        curve = [
            clip for clip in scene.timeline
            if getattr(clip.animation, "mobject", None).name == "Normal Approximation"
        ]
        self.assertEqual(len(bars), 11)
        self.assertEqual(len(labels), 11)
        self.assertTrue(all(clip.initial.scale[2] == .001 for clip in bars))
        self.assertTrue(all(clip.final.scale[2] == 1.0 for clip in bars))
        self.assertTrue(all(clip.start_frame == labels[0].start_frame for clip in bars + labels))
        self.assertTrue(all(clip.start_frame > bars[0].end_frame for clip in curve))


if __name__ == "__main__":
    unittest.main()
