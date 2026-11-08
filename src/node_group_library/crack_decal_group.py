"""
    This file is part of Sequence Bake.

    Sequence Bake is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or any later version.

    Sequence Bake is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.

"""

import bpy
import math

GROUP_NAME = "Crack Decal"

def new_node(nodes, node_type, name, location):
    """Create and position a shader node."""
    node = nodes.new(node_type)
    node.name = name
    node.label = name
    node.location = location
    return node


def set_socket(node, name, value):
    """Safely set a node input value."""
    socket = node.inputs.get(name)
    if socket is None:
        raise RuntimeError(f"Node '{node.name}' has no input '{name}'.")
    socket.default_value = value


def link(tree, output_socket, input_socket):
    """Create a node link"""
    tree.links.new(output_socket, input_socket)


def math_node(nodes, name, operation, location):
    """Create a ShaderNodeMath node"""
    node = new_node(nodes, "ShaderNodeMath", name, location)
    node.operation = operation
    return node


def add_math(nodes, name, location):
    """Create an ADD node"""
    return math_node(nodes, name, "ADD", location)


def subtract_math(nodes, name, location):
    """Create a SUBTRACT node"""
    return math_node(nodes, name, "SUBTRACT", location)


def multiply_math(nodes, name, location):
    """Create a MULTIPLY node"""
    return math_node(nodes, name, "MULTIPLY", location)


def vector_math_node(nodes, name, operation, location):
    """Create a ShaderNodeVectorMath node."""
    node = new_node(nodes, "ShaderNodeVectorMath", name, location)
    node.operation = operation
    return node


def create_float_input(group, name, default, minimum, maximum):
    """Create an exposed float input"""
    socket = group.interface.new_socket(
        name=name,
        in_out="INPUT",
        socket_type="NodeSocketFloat",
    )
    socket.default_value = default
    socket.min_value = minimum
    socket.max_value = maximum
    return socket


def create_color_input(group, name, default):
    """Create an exposed color input"""
    socket = group.interface.new_socket(
        name=name,
        in_out="INPUT",
        socket_type="NodeSocketColor",
    )
    socket.default_value = default
    return socket


def create_output(group, name, socket_type):
    """Create an exposed output"""
    return group.interface.new_socket(
        name=name,
        in_out="OUTPUT",
        socket_type=socket_type,
    )


def create_group_interface(group):
    """Construct the interface mimicking physical crack properties."""
    create_float_input(group, "Position X", 0.0, -2.0, 2.0)
    create_float_input(group, "Position Y", 0.0, -2.0, 2.0)
    create_float_input(group, "Rotation", 0.0, -180.0, 180.0)
    create_float_input(group, "Crack Count", 5.0, 1.0, 50.0)
    create_float_input(group, "Crack Width", 0.015, 0.001, 0.1)
    create_float_input(group, "Width Variation", 0.75, 0.0, 1.0)
    create_float_input(group, "Jaggedness", 0.4, 0.0, 2.0)
    create_float_input(group, "Decal Radius", 0.45, 0.05, 1.5)
    create_float_input(group, "Edge Softness", 0.15, 0.001, 1.0)
    create_color_input(group, "Crack Color", (0.01, 0.01, 0.01, 1.0))
    create_float_input(group, "Roughness", 0.9, 0.0, 1.0)
    create_float_input(group, "Bump Strength", -0.5, -1.0, 1.0)
    create_float_input(group, "Bump Distance", 0.01, 0.0, 1.0)
    create_output(group, "Shader", "NodeSocketShader")
    create_output(group, "Crack Mask", "NodeSocketFloat")

    
def create_node_group():
    """Create and return the procedural crack decal node group."""

    group = bpy.data.node_groups.get(GROUP_NAME)

    if group is None:
        group = bpy.data.node_groups.new(
            GROUP_NAME,
            "ShaderNodeTree",
        )
    else:
        group.nodes.clear()
        group.interface.clear()

    group.description = (
        "Procedural physical crack decal with branching, jaggedness, "
        "width variation, and localized coordinate transformations."
    )

    create_group_interface(group)

    nodes = group.nodes

    group_input = new_node(
        nodes,
        "NodeGroupInput",
        "Crack Controls",
        (-2200, 0),
    )

    group_output = new_node(
        nodes,
        "NodeGroupOutput",
        "Output",
        (1600, 0),
    )

    group_output.is_active_output = True

    texcoord = new_node(nodes, "ShaderNodeTexCoord", "UV Coordinates", (-2200, -300))
    separate_uv = new_node(nodes, "ShaderNodeSeparateXYZ", "Separate UV", (-2000, -300))
    link(group, texcoord.outputs["UV"], separate_uv.inputs["Vector"])

    offset_x = subtract_math(nodes, "Offset X", (-1800, -200))
    link(group, separate_uv.outputs["X"], offset_x.inputs["Value"])
    link(group, group_input.outputs["Position X"], offset_x.inputs["Value_001"])

    offset_y = subtract_math(nodes, "Offset Y", (-1800, -400))
    link(group, separate_uv.outputs["Y"], offset_y.inputs["Value"])
    link(group, group_input.outputs["Position Y"], offset_y.inputs["Value_001"])

    center_x = subtract_math(nodes, "Center X", (-1600, -200))
    set_socket(center_x, "Value_001", 0.5)
    link(group, offset_x.outputs["Value"], center_x.inputs["Value"])

    center_y = subtract_math(nodes, "Center Y", (-1600, -400))
    set_socket(center_y, "Value_001", 0.5)
    link(group, offset_y.outputs["Value"], center_y.inputs["Value"])

    radians = multiply_math(nodes, "Rotation Radians", (-1800, 0))
    set_socket(radians, "Value_001", math.pi / 180.0)
    link(group, group_input.outputs["Rotation"], radians.inputs["Value"])

    cosine = math_node(nodes, "Cosine", "COSINE", (-1600, 50))
    sine = math_node(nodes, "Sine", "SINE", (-1600, -50))
    link(group, radians.outputs["Value"], cosine.inputs["Value"])
    link(group, radians.outputs["Value"], sine.inputs["Value"])

    x_cos = multiply_math(nodes, "X Cosine", (-1400, -100))
    link(group, center_x.outputs["Value"], x_cos.inputs["Value"])
    link(group, cosine.outputs["Value"], x_cos.inputs["Value_001"])

    y_sin = multiply_math(nodes, "Y Sine", (-1400, -250))
    link(group, center_y.outputs["Value"], y_sin.inputs["Value"])
    link(group, sine.outputs["Value"], y_sin.inputs["Value_001"])

    x_sin = multiply_math(nodes, "X Sine", (-1400, -400))
    link(group, center_x.outputs["Value"], x_sin.inputs["Value"])
    link(group, sine.outputs["Value"], x_sin.inputs["Value_001"])

    y_cos = multiply_math(nodes, "Y Cosine", (-1400, -550))
    link(group, center_y.outputs["Value"], y_cos.inputs["Value"])
    link(group, cosine.outputs["Value"], y_cos.inputs["Value_001"])

    rotated_x = subtract_math(nodes, "Rotated X", (-1200, -200))
    link(group, x_cos.outputs["Value"], rotated_x.inputs["Value"])
    link(group, y_sin.outputs["Value"], rotated_x.inputs["Value_001"])

    rotated_y = add_math(nodes, "Rotated Y", (-1200, -450))
    link(group, x_sin.outputs["Value"], rotated_y.inputs["Value"])
    link(group, y_cos.outputs["Value"], rotated_y.inputs["Value_001"])

    uncenter_x = add_math(nodes, "Uncenter X", (-1000, -200))
    set_socket(uncenter_x, "Value_001", 0.5)
    link(group, rotated_x.outputs["Value"], uncenter_x.inputs["Value"])

    uncenter_y = add_math(nodes, "Uncenter Y", (-1000, -400))
    set_socket(uncenter_y, "Value_001", 0.5)
    link(group, rotated_y.outputs["Value"], uncenter_y.inputs["Value"])

    combine_uv = new_node(nodes, "ShaderNodeCombineXYZ", "Transformed UV", (-800, -300))
    link(group, uncenter_x.outputs["Value"], combine_uv.inputs["X"])
    link(group, uncenter_y.outputs["Value"], combine_uv.inputs["Y"])

    noise_distortion = new_node(nodes, "ShaderNodeTexNoise", "Morphology Noise", (-800, 100))
    set_socket(noise_distortion, "Scale", 15.0)
    set_socket(noise_distortion, "Detail", 15.0)
    set_socket(noise_distortion, "Roughness", 0.65)
    link(group, combine_uv.outputs["Vector"], noise_distortion.inputs["Vector"])

    center_noise = vector_math_node(nodes, "Center Noise", "SUBTRACT", (-600, 100))
    center_noise.inputs[1].default_value = (0.5, 0.5, 0.5)
    link(group, noise_distortion.outputs["Color"], center_noise.inputs[0])

    scale_distortion = vector_math_node(nodes, "Scale Distortion", "SCALE", (-400, 100))
    link(group, center_noise.outputs["Vector"], scale_distortion.inputs[0])
    link(group, group_input.outputs["Jaggedness"], scale_distortion.inputs[3])

    distorted_uv = vector_math_node(nodes, "Distorted UV", "ADD", (-200, -150))
    link(group, combine_uv.outputs["Vector"], distorted_uv.inputs[0])
    link(group, scale_distortion.outputs["Vector"], distorted_uv.inputs[1])

    voronoi = new_node(nodes, "ShaderNodeTexVoronoi", "Crack Network", (0, -150))
    voronoi.feature = "DISTANCE_TO_EDGE"
    link(group, distorted_uv.outputs["Vector"], voronoi.inputs["Vector"])
    link(group, group_input.outputs["Crack Count"], voronoi.inputs["Scale"])

    width_noise = new_node(nodes, "ShaderNodeTexNoise", "Width Noise", (-400, -500))
    set_socket(width_noise, "Scale", 5.0)
    link(group, combine_uv.outputs["Vector"], width_noise.inputs["Vector"])

    inv_variation = subtract_math(nodes, "Invert Variation", (-200, -650))
    set_socket(inv_variation, "Value", 1.0)
    link(group, group_input.outputs["Width Variation"], inv_variation.inputs["Value_001"])

    width_mix = new_node(nodes, "ShaderNodeMapRange", "Width Variation Mix", (0, -500))
    set_socket(width_mix, "To Max", 1.0)
    link(group, inv_variation.outputs["Value"], width_mix.inputs["To Min"])
    link(group, width_noise.outputs["Fac"], width_mix.inputs["Value"])

    final_width = multiply_math(nodes, "Final Width", (200, -450))
    link(group, group_input.outputs["Crack Width"], final_width.inputs["Value"])
    link(group, width_mix.outputs["Result"], final_width.inputs["Value_001"])

    crack_mask_range = new_node(nodes, "ShaderNodeMapRange", "Crack Edge Mask", (400, -150))
    crack_mask_range.clamp = True
    set_socket(crack_mask_range, "From Min", 0.0)
    set_socket(crack_mask_range, "To Min", 1.0)
    set_socket(crack_mask_range, "To Max", 0.0)
    link(group, voronoi.outputs["Distance"], crack_mask_range.inputs["Value"])
    link(group, final_width.outputs["Value"], crack_mask_range.inputs["From Max"])

    decal_center = new_node(nodes, "ShaderNodeCombineXYZ", "Decal Center", (0, -800))
    set_socket(decal_center, "X", 0.5)
    set_socket(decal_center, "Y", 0.5)

    radial_distance = vector_math_node(nodes, "Radial Distance", "DISTANCE", (200, -750))
    link(group, combine_uv.outputs["Vector"], radial_distance.inputs[0])
    link(group, decal_center.outputs["Vector"], radial_distance.inputs[1])

    decal_fade = new_node(nodes, "ShaderNodeMapRange", "Decal Fade", (400, -750))
    decal_fade.clamp = True
    set_socket(decal_fade, "To Min", 1.0)
    set_socket(decal_fade, "To Max", 0.0)
    link(group, radial_distance.outputs["Value"], decal_fade.inputs["Value"])
    link(group, group_input.outputs["Decal Radius"], decal_fade.inputs["From Max"])

    inner_radius = subtract_math(nodes, "Inner Radius", (200, -950))
    link(group, group_input.outputs["Decal Radius"], inner_radius.inputs["Value"])
    link(group, group_input.outputs["Edge Softness"], inner_radius.inputs["Value_001"])
    link(group, inner_radius.outputs["Value"], decal_fade.inputs["From Min"])

    final_mask = multiply_math(nodes, "Final Mask Composition", (700, -350))
    link(group, crack_mask_range.outputs["Result"], final_mask.inputs["Value"])
    link(group, decal_fade.outputs["Result"], final_mask.inputs["Value_001"])

    bump = new_node(nodes, "ShaderNodeBump", "Crack Bump", (700, -150))
    link(group, final_mask.outputs["Value"], bump.inputs["Height"])
    link(group, group_input.outputs["Bump Strength"], bump.inputs["Strength"])
    link(group, group_input.outputs["Bump Distance"], bump.inputs["Distance"])

    principled = new_node(nodes, "ShaderNodeBsdfPrincipled", "Crack Surface", (1000, 100))
    link(group, group_input.outputs["Crack Color"], principled.inputs["Base Color"])
    link(group, group_input.outputs["Roughness"], principled.inputs["Roughness"])
    link(group, bump.outputs["Normal"], principled.inputs["Normal"])

    transparent = new_node(nodes, "ShaderNodeBsdfTransparent", "Background", (1000, -250))

    mix_shader = new_node(nodes, "ShaderNodeMixShader", "Decal Mixer", (1300, 0))
    link(group, final_mask.outputs["Value"], mix_shader.inputs[0])
    link(group, transparent.outputs["BSDF"], mix_shader.inputs[1])
    link(group, principled.outputs["BSDF"], mix_shader.inputs[2])

    link(group, mix_shader.outputs["Shader"], group_output.inputs["Shader"])
    link(group, final_mask.outputs["Value"], group_output.inputs["Crack Mask"])

    for node in nodes:
        node.width = 180

    return group