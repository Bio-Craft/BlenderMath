"""Registry used by tests and Blender's example selector."""

from .coordinate_systems import CoordinateSystemsExample
from .axis_scaling import AxisScalingExample
from .geometry_nodes_3d import GeometryNodes3DExample
from .creation import CreationExample
from .fading import FadingExample
from .fill_and_stroke import FillAndStrokeExample
from .function_graphs import FunctionGraphsExample
from .math_typst import MathTypstExample
from .matrices import MatricesExample
from .parametric_curves import ParametricCurvesExample
from .probability_distribution import ProbabilityDistributionExample
from .quadratic_derivation import QuadraticDerivationExample
from .scene_graph import SceneGraphExample
from .simulation import SimulationExample
from .spatial_layout import SpatialLayoutExample
from .timeline import TimelineExample
from .tracker_updaters import TrackerUpdaterExample
from .transformations import TransformationsExample

EXAMPLES = {
    "CREATION": CreationExample,
    "TRANSFORMATIONS": TransformationsExample,
    "FADING": FadingExample,
    "FILL_STROKE": FillAndStrokeExample,
    "SCENE_GRAPH": SceneGraphExample,
    "COORDINATES": CoordinateSystemsExample,
    "AXIS_SCALING": AxisScalingExample,
    "GEOMETRY_NODES_3D": GeometryNodes3DExample,
    "FUNCTION_GRAPHS": FunctionGraphsExample,
    "PARAMETRIC": ParametricCurvesExample,
    "PROBABILITY": ProbabilityDistributionExample,
    "QUADRATIC_DERIVATION": QuadraticDerivationExample,
    "TRACKER": TrackerUpdaterExample,
    "TIMELINE": TimelineExample,
    "SIMULATION": SimulationExample,
    "SPATIAL_LAYOUT": SpatialLayoutExample,
    "MATH_TYPST": MathTypstExample,
    "MATRICES": MatricesExample,
}
