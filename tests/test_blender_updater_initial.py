"""Real-Blender regression for an updater's pre-animation geometry."""

from pathlib import Path
import sys
import unittest

try:
    import bpy  # noqa: F401
except ModuleNotFoundError:
    bpy = None

if bpy is not None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from BlenderMath.core import Polyline, Scene, ValueTracker, linear
else:
    from core import Polyline, Scene, ValueTracker, linear


@unittest.skipIf(bpy is None, "requires Blender Python")
class BlenderUpdaterInitialGeometryTests(unittest.TestCase):
    def test_held_first_frame_does_not_inherit_final_geometry(self):
        from BlenderMath.backend.blender_52.compiler import BlenderCompiler

        tracker = ValueTracker(0.0)
        line = Polyline([(0, 0, 0), (1, 0, 0)])
        line.add_updater(lambda curve: curve.set_points(
            [(0, 0, 0), (1, 0, tracker.value)],
        ))
        scene = Scene(fps=10).add(line)
        scene.wait(1.0)
        scene.play(tracker.animate.set_value(2.0), run_time=1.0, rate_func=linear)

        self.assertEqual(line.geometry["points"][1], (1, 0, 2.0))
        initial = BlenderCompiler(scene)._initial_geometry(line)
        self.assertEqual(initial["points"][1], (1, 0, 0.0))


if __name__ == "__main__":
    unittest.main()
