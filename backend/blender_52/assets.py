"""Reusable native Geometry Nodes assets."""

import bpy


def create_curve_style_asset(name="BM Curve Style"):
    group = bpy.data.node_groups.get(name)
    if group:
        return group
    group = bpy.data.node_groups.new(name, "GeometryNodeTree")
    group.description = "BlenderMath curve-to-mesh style"
    group.color_tag = "GEOMETRY"
    group.interface.new_socket(name="Curve", in_out="INPUT", socket_type="NodeSocketGeometry")
    radius = group.interface.new_socket(name="Radius", in_out="INPUT", socket_type="NodeSocketFloat")
    radius.default_value = 0.025
    radius.min_value = 0.0001
    resolution = group.interface.new_socket(name="Resolution", in_out="INPUT", socket_type="NodeSocketInt")
    resolution.default_value = 8
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    incoming = group.nodes.new("NodeGroupInput")
    outgoing = group.nodes.new("NodeGroupOutput")
    circle = group.nodes.new("GeometryNodeCurvePrimitiveCircle")
    to_mesh = group.nodes.new("GeometryNodeCurveToMesh")
    incoming.location = (-420, 40)
    circle.location = (-420, -150)
    to_mesh.location = (-120, 40)
    outgoing.location = (140, 40)
    group.links.new(incoming.outputs["Curve"], to_mesh.inputs["Curve"])
    group.links.new(incoming.outputs["Radius"], circle.inputs["Radius"])
    group.links.new(incoming.outputs["Resolution"], circle.inputs["Resolution"])
    group.links.new(circle.outputs["Curve"], to_mesh.inputs["Profile Curve"])
    group.links.new(to_mesh.outputs["Mesh"], outgoing.inputs["Geometry"])
    return group


def create_arrow_3d_asset(name="BM Arrow 3D"):
    group = bpy.data.node_groups.get(name)
    if group:
        return group
    group = bpy.data.node_groups.new(name, "GeometryNodeTree")
    group.description = "Endpoint-driven BlenderMath 3D arrow"
    group.color_tag = "GEOMETRY"
    start = group.interface.new_socket(name="Start", in_out="INPUT", socket_type="NodeSocketVector")
    start.default_value = (0.0, 0.0, 0.0)
    end = group.interface.new_socket(name="End", in_out="INPUT", socket_type="NodeSocketVector")
    end.default_value = (1.0, 0.0, 0.0)
    shaft = group.interface.new_socket(name="Shaft Radius", in_out="INPUT", socket_type="NodeSocketFloat")
    shaft.default_value = .035
    tip_radius = group.interface.new_socket(name="Tip Radius", in_out="INPUT", socket_type="NodeSocketFloat")
    tip_radius.default_value = .11
    tip_length = group.interface.new_socket(name="Tip Length", in_out="INPUT", socket_type="NodeSocketFloat")
    tip_length.default_value = .24
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    incoming = group.nodes.new("NodeGroupInput")
    outgoing = group.nodes.new("NodeGroupOutput")
    subtract = group.nodes.new("ShaderNodeVectorMath")
    subtract.operation = "SUBTRACT"
    normalize = group.nodes.new("ShaderNodeVectorMath")
    normalize.operation = "NORMALIZE"
    scale_tip = group.nodes.new("ShaderNodeVectorMath")
    scale_tip.operation = "SCALE"
    shaft_end = group.nodes.new("ShaderNodeVectorMath")
    shaft_end.operation = "SUBTRACT"
    line = group.nodes.new("GeometryNodeCurvePrimitiveLine")
    profile = group.nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile.inputs["Resolution"].default_value = 12
    curve_mesh = group.nodes.new("GeometryNodeCurveToMesh")
    cone = group.nodes.new("GeometryNodeMeshCone")
    cone.inputs["Vertices"].default_value = 24
    align = group.nodes.new("FunctionNodeAlignEulerToVector")
    align.axis = "Z"
    half_tip = group.nodes.new("ShaderNodeVectorMath")
    half_tip.operation = "SCALE"
    half_tip.inputs[3].default_value = .5
    cone_center = group.nodes.new("ShaderNodeVectorMath")
    cone_center.operation = "SUBTRACT"
    transform = group.nodes.new("GeometryNodeTransform")
    join = group.nodes.new("GeometryNodeJoinGeometry")

    group.links.new(incoming.outputs["End"], subtract.inputs[0])
    group.links.new(incoming.outputs["Start"], subtract.inputs[1])
    group.links.new(subtract.outputs["Vector"], normalize.inputs[0])
    group.links.new(normalize.outputs["Vector"], scale_tip.inputs[0])
    group.links.new(incoming.outputs["Tip Length"], scale_tip.inputs[3])
    group.links.new(incoming.outputs["End"], shaft_end.inputs[0])
    group.links.new(scale_tip.outputs["Vector"], shaft_end.inputs[1])
    group.links.new(incoming.outputs["Start"], line.inputs["Start"])
    group.links.new(shaft_end.outputs["Vector"], line.inputs["End"])
    group.links.new(incoming.outputs["Shaft Radius"], profile.inputs["Radius"])
    group.links.new(line.outputs["Curve"], curve_mesh.inputs["Curve"])
    group.links.new(profile.outputs["Curve"], curve_mesh.inputs["Profile Curve"])
    group.links.new(incoming.outputs["Tip Radius"], cone.inputs["Radius Bottom"])
    group.links.new(incoming.outputs["Tip Length"], cone.inputs["Depth"])
    group.links.new(subtract.outputs["Vector"], align.inputs["Vector"])
    group.links.new(normalize.outputs["Vector"], half_tip.inputs[0])
    group.links.new(incoming.outputs["Tip Length"], half_tip.inputs[3])
    group.links.new(incoming.outputs["End"], cone_center.inputs[0])
    group.links.new(half_tip.outputs["Vector"], cone_center.inputs[1])
    group.links.new(cone.outputs["Mesh"], transform.inputs["Geometry"])
    group.links.new(cone_center.outputs["Vector"], transform.inputs["Translation"])
    group.links.new(align.outputs["Rotation"], transform.inputs["Rotation"])
    group.links.new(curve_mesh.outputs["Mesh"], join.inputs["Geometry"])
    group.links.new(transform.outputs["Geometry"], join.inputs["Geometry"])
    group.links.new(join.outputs["Geometry"], outgoing.inputs["Geometry"])
    return group
