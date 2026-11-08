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

MATERIAL_NAME = "MAT_Crosswalk_Decal"
GROUP_NAME = "Crosswalk Decal"
PREVIEW_NAME = "Crosswalk_Decal_Preview"

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
        raise RuntimeError(
            f"Node '{node.name}' has no input '{name}'."
        )

    socket.default_value = value


def link(tree, output_socket, input_socket):
    """Create a node link."""
    tree.links.new(output_socket, input_socket)


def math_node(nodes, name, operation, location):
    """Create a ShaderNodeMath node."""
    node = new_node(
        nodes,
        "ShaderNodeMath",
        name,
        location,
    )

    node.operation = operation

    return node


def add_math(nodes, name, location):
    """Create an ADD node."""
    return math_node(nodes, name, "ADD", location)


def subtract_math(nodes, name, location):
    """Create a SUBTRACT node."""
    return math_node(nodes, name, "SUBTRACT", location)


def multiply_math(nodes, name, location):
    """Create a MULTIPLY node."""
    return math_node(nodes, name, "MULTIPLY", location)


def divide_math(nodes, name, location):
    """Create a DIVIDE node."""
    return math_node(nodes, name, "DIVIDE", location)


def absolute_math(nodes, name, location):
    """Create an ABSOLUTE node."""
    return math_node(nodes, name, "ABSOLUTE", location)


def maximum_math(nodes, name, location):
    """Create a MAXIMUM node."""
    return math_node(nodes, name, "MAXIMUM", location)

def less_than(nodes, name, location):
    """Create a LESS_THAN math node."""
    return math_node(nodes, name, "LESS_THAN", location)

def minimum_math(nodes, name, location):
    """Create a MINIMUM node."""
    return math_node(nodes, name, "MINIMUM", location)


def smoothstep_math(nodes, name, location):
    """Create a SMOOTH_MIN node."""
    return math_node(nodes, name, "SMOOTH_MIN", location)


def create_float_input(group, name, default, minimum, maximum):
    """Create an exposed float input."""
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
    """Create an exposed color input."""
    socket = group.interface.new_socket(
        name=name,
        in_out="INPUT",
        socket_type="NodeSocketColor",
    )

    socket.default_value = default
    
    return socket


def create_output(group, name, socket_type):
    """Create an exposed output."""
    return group.interface.new_socket(
        name=name,
        in_out="OUTPUT",
        socket_type=socket_type,
    )


def create_group_interface(group):
    """Create the Crosswalk Decal interface."""

    create_float_input(
        group,
        "Position X",
        0.0,
        -1.0,
        1.0,
    )

    create_float_input(
        group,
        "Position Y",
        0.0,
        -1.0,
        1.0,
    )

    create_float_input(
        group,
        "Stripe Count",
        7.0,
        1.0,
        32.0,
    )

    create_float_input(
        group,
        "Stripe Width",
        0.075,
        0.005,
        0.5,
    )

    create_float_input(
        group,
        "Stripe Gap",
        0.045,
        0.001,
        0.5,
    )

    create_float_input(
        group,
        "Pattern Rotation",
        0.0,
        -180.0,
        180.0,
    )

    create_float_input(
        group,
        "Decal Width",
        0.80,
        0.05,
        1.0,
    )

    create_float_input(
        group,
        "Decal Length",
        0.80,
        0.05,
        1.0,
    )

    create_float_input(
        group,
        "Edge Softness",
        0.015,
        0.0001,
        0.25,
    )

    create_color_input(
        group,
        "Paint Color",
        (0.85, 0.85, 0.82, 1.0),
    )

    create_float_input(
        group,
        "Paint Variation",
        0.08,
        0.0,
        1.0,
    )

    create_float_input(
        group,
        "Wear Amount",
        0.20,
        0.0,
        1.0,
    )

    create_float_input(
        group,
        "Wear Scale",
        7.0,
        0.1,
        50.0,
    )

    create_float_input(
        group,
        "Wear Contrast",
        2.5,
        0.1,
        10.0,
    )

    create_float_input(
        group,
        "Edge Breakup",
        0.20,
        0.0,
        1.0,
    )

    create_float_input(
        group,
        "Dirt Amount",
        0.15,
        0.0,
        1.0,
    )

    create_float_input(
        group,
        "Dirt Scale",
        12.0,
        0.1,
        50.0,
    )

    create_float_input(
        group,
        "Dirt Contrast",
        2.0,
        0.1,
        10.0,
    )

    create_float_input(
        group,
        "Roughness",
        0.78,
        0.0,
        1.0,
    )

    create_float_input(
        group,
        "Bump Strength",
        0.12,
        0.0,
        1.0,
    )

    create_float_input(
        group,
        "Bump Distance",
        0.035,
        0.0,
        0.25,
    )

    create_output(
        group,
        "Shader",
        "NodeSocketShader",
    )

    create_output(
        group,
        "Decal Mask",
        "NodeSocketFloat",
    )


def create_crosswalk_group():
    """Create the procedural crosswalk shader group."""
    
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
        "Procedural crosswalk decal with configurable "
        "position, rotation, dimensions, stripe pattern, edge softness, "
        "wear, breakup, dirt, roughness, and bump."
    )

    create_group_interface(group)

    nodes = group.nodes
    links = group.links

    group_input = new_node(
        nodes,
        "NodeGroupInput",
        "Crosswalk Controls",
        (-1900, 100),
    )

    group_output = new_node(
        nodes,
        "NodeGroupOutput",
        "Crosswalk Output",
        (1700, 100),
    )

    texcoord = new_node(
        nodes,
        "ShaderNodeTexCoord",
        "UV Coordinates",
        (-1900, -500),
    )

    separate = new_node(
        nodes,
        "ShaderNodeSeparateXYZ",
        "Separate UV",
        (-1700, -500),
    )

    link(
        group,
        texcoord.outputs["UV"],
        separate.inputs["Vector"],
    )

    center_x = subtract_math(
        nodes,
        "Center X",
        (-1500, -350),
    )

    set_socket(
        center_x,
        "Value_001",
        0.5,
    )

    link(
        group,
        separate.outputs["X"],
        center_x.inputs["Value"],
    )

    center_y = subtract_math(
        nodes,
        "Center Y",
        (-1500, -550),
    )

    set_socket(
        center_y,
        "Value_001",
        0.5,
    )

    link(
        group,
        separate.outputs["Y"],
        center_y.inputs["Value"],
    )

    offset_x = subtract_math(
        nodes,
        "Position X Offset",
        (-1300, -350),
    )

    link(
        group,
        center_x.outputs["Value"],
        offset_x.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Position X"],
        offset_x.inputs["Value_001"],
    )

    offset_y = subtract_math(
        nodes,
        "Position Y Offset",
        (-1300, -550),
    )

    link(
        group,
        center_y.outputs["Value"],
        offset_y.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Position Y"],
        offset_y.inputs["Value_001"],
    )

    radians = multiply_math(
        nodes,
        "Rotation Radians",
        (-1100, -100),
    )

    set_socket(
        radians,
        "Value_001",
        math.pi / 180.0,
    )

    link(
        group,
        group_input.outputs["Pattern Rotation"],
        radians.inputs["Value"],
    )

    cosine = math_node(
        nodes,
        "Cosine",
        "COSINE",
        (-900, 0),
    )

    sine = math_node(
        nodes,
        "Sine",
        "SINE",
        (-900, -150),
    )

    link(
        group,
        radians.outputs["Value"],
        cosine.inputs["Value"],
    )

    link(
        group,
        radians.outputs["Value"],
        sine.inputs["Value"],
    )

    # X * cos
    x_cos = multiply_math(
        nodes,
        "X Cosine",
        (-700, -300),
    )

    link(
        group,
        offset_x.outputs["Value"],
        x_cos.inputs["Value"],
    )

    link(
        group,
        cosine.outputs["Value"],
        x_cos.inputs["Value_001"],
    )

    # Y * sin
    y_sin = multiply_math(
        nodes,
        "Y Sine",
        (-700, -450),
    )

    link(
        group,
        offset_y.outputs["Value"],
        y_sin.inputs["Value"],
    )

    link(
        group,
        sine.outputs["Value"],
        y_sin.inputs["Value_001"],
    )

    # X * sin
    x_sin = multiply_math(
        nodes,
        "X Sine",
        (-700, -600),
    )

    link(
        group,
        offset_x.outputs["Value"],
        x_sin.inputs["Value"],
    )

    link(
        group,
        sine.outputs["Value"],
        x_sin.inputs["Value_001"],
    )

    # Y * cos
    y_cos = multiply_math(
        nodes,
        "Y Cosine",
        (-700, -750),
    )

    link(
        group,
        offset_y.outputs["Value"],
        y_cos.inputs["Value"],
    )

    link(
        group,
        cosine.outputs["Value"],
        y_cos.inputs["Value_001"],
    )

    # Rotated X = X*cos - Y*sin
    rotated_x = subtract_math(
        nodes,
        "Rotated X",
        (-500, -300),
    )

    link(
        group,
        x_cos.outputs["Value"],
        rotated_x.inputs["Value"],
    )

    link(
        group,
        y_sin.outputs["Value"],
        rotated_x.inputs["Value_001"],
    )

    # Rotated Y = X*sin + Y*cos
    rotated_y = add_math(
        nodes,
        "Rotated Y",
        (-500, -600),
    )

    link(
        group,
        x_sin.outputs["Value"],
        rotated_y.inputs["Value"],
    )

    link(
        group,
        y_cos.outputs["Value"],
        rotated_y.inputs["Value_001"],
    )

    abs_x = absolute_math(
        nodes,
        "Absolute X",
        (-300, -300),
    )

    abs_y = absolute_math(
        nodes,
        "Absolute Y",
        (-300, -600),
    )

    link(
        group,
        rotated_x.outputs["Value"],
        abs_x.inputs["Value"],
    )

    link(
        group,
        rotated_y.outputs["Value"],
        abs_y.inputs["Value"],
    )

    half_width = multiply_math(
        nodes,
        "Half Width",
        (-100, 100),
    )

    set_socket(
        half_width,
        "Value_001",
        0.5,
    )

    link(
        group,
        group_input.outputs["Decal Width"],
        half_width.inputs["Value"],
    )

    half_length = multiply_math(
        nodes,
        "Half Length",
        (-100, -100),
    )

    set_socket(
        half_length,
        "Value_001",
        0.5,
    )

    link(
        group,
        group_input.outputs["Decal Length"],
        half_length.inputs["Value"],
    )

    x_edge_distance = subtract_math(
        nodes,
        "X Edge Distance",
        (100, -300),
    )

    link(
        group,
        half_width.outputs["Value"],
        x_edge_distance.inputs["Value"],
    )

    link(
        group,
        abs_x.outputs["Value"],
        x_edge_distance.inputs["Value_001"],
    )

    y_edge_distance = subtract_math(
        nodes,
        "Y Edge Distance",
        (100, -600),
    )

    link(
        group,
        half_length.outputs["Value"],
        y_edge_distance.inputs["Value"],
    )

    link(
        group,
        abs_y.outputs["Value"],
        y_edge_distance.inputs["Value_001"],
    )

    x_soft = new_node(
        nodes,
        "ShaderNodeMapRange",
        "Soft X Edge",
        (350, -250),
    )

    x_soft.interpolation_type = "SMOOTHERSTEP"
    x_soft.clamp = True

    set_socket(
        x_soft,
        "From Min",
        0.0,
    )

    set_socket(
        x_soft,
        "From Max",
        0.05,
    )

    set_socket(
        x_soft,
        "To Min",
        0.0,
    )

    set_socket(
        x_soft,
        "To Max",
        1.0,
    )

    link(
        group,
        x_edge_distance.outputs["Value"],
        x_soft.inputs["Value"],
    )

    # Edge softness controls From Max.
    link(
        group,
        group_input.outputs["Edge Softness"],
        x_soft.inputs["From Max"],
    )

    y_soft = new_node(
        nodes,
        "ShaderNodeMapRange",
        "Soft Y Edge",
        (350, -600),
    )

    y_soft.interpolation_type = "SMOOTHERSTEP"
    y_soft.clamp = True

    set_socket(
        y_soft,
        "From Min",
        0.0,
    )

    set_socket(
        y_soft,
        "To Min",
        0.0,
    )

    set_socket(
        y_soft,
        "To Max",
        1.0,
    )

    link(
        group,
        y_edge_distance.outputs["Value"],
        y_soft.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Edge Softness"],
        y_soft.inputs["From Max"],
    )

    footprint = multiply_math(
        nodes,
        "SOFT DECAL FOOTPRINT",
        (600, -400),
    )

    link(
        group,
        x_soft.outputs["Result"],
        footprint.inputs["Value"],
    )

    link(
        group,
        y_soft.outputs["Result"],
        footprint.inputs["Value_001"],
    )

    positive_y = add_math(
        nodes,
        "Positive Y",
        (-100, -900),
    )

    set_socket(
        positive_y,
        "Value_001",
        0.5,
    )

    link(
        group,
        rotated_y.outputs["Value"],
        positive_y.inputs["Value"],
    )

    stripe_period = add_math(
        nodes,
        "Stripe Period",
        (100, -900),
    )

    link(
        group,
        group_input.outputs["Stripe Width"],
        stripe_period.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Stripe Gap"],
        stripe_period.inputs["Value_001"],
    )

    stripe_coordinate = multiply_math(
        nodes,
        "Stripe Coordinate",
        (300, -900),
    )

    link(
        group,
        positive_y.outputs["Value"],
        stripe_coordinate.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Stripe Count"],
        stripe_coordinate.inputs["Value_001"],
    )

    stripe_fraction = math_node(
        nodes,
        "Stripe Fraction",
        "FRACT",
        (500, -900),
    )

    link(
        group,
        stripe_coordinate.outputs["Value"],
        stripe_fraction.inputs["Value"],
    )

    stripe_ratio = divide_math(
        nodes,
        "Stripe Width Ratio",
        (300, -1050),
    )

    link(
        group,
        group_input.outputs["Stripe Width"],
        stripe_ratio.inputs["Value"],
    )

    link(
        group,
        stripe_period.outputs["Value"],
        stripe_ratio.inputs["Value_001"],
    )

    stripe_mask = less_than(
        nodes,
        "CROSSWALK STRIPES",
        (700, -900),
    )

    link(
        group,
        stripe_fraction.outputs["Value"],
        stripe_mask.inputs["Value"],
    )

    link(
        group,
        stripe_ratio.outputs["Value"],
        stripe_mask.inputs["Value_001"],
    )

    base_mask = multiply_math(
        nodes,
        "Base Crosswalk Mask",
        (900, -650),
    )

    link(
        group,
        stripe_mask.outputs["Value"],
        base_mask.inputs["Value"],
    )

    link(
        group,
        footprint.outputs["Value"],
        base_mask.inputs["Value_001"],
    )

    wear_noise = new_node(
        nodes,
        "ShaderNodeTexNoise",
        "Paint Wear Noise",
        (300, -1250),
    )

    set_socket(
        wear_noise,
        "Detail",
        5.0,
    )

    set_socket(
        wear_noise,
        "Roughness",
        0.75,
    )

    link(
        group,
        texcoord.outputs["Generated"],
        wear_noise.inputs["Vector"],
    )

    link(
        group,
        group_input.outputs["Wear Scale"],
        wear_noise.inputs["Scale"],
    )

    wear_ramp = new_node(
        nodes,
        "ShaderNodeValToRGB",
        "Wear Threshold",
        (500, -1250),
    )

    wear_ramp.color_ramp.elements[0].position = 0.35
    wear_ramp.color_ramp.elements[1].position = 0.65

    link(
        group,
        wear_noise.outputs["Fac"],
        wear_ramp.inputs["Fac"],
    )

    wear_contrast = math_node(
        nodes,
        "Wear Contrast",
        "POWER",
        (700, -1250),
    )

    link(
        group,
        wear_ramp.outputs["Color"],
        wear_contrast.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Wear Contrast"],
        wear_contrast.inputs["Value_001"],
    )

    wear_amount = multiply_math(
        nodes,
        "Wear Amount",
        (900, -1250),
    )

    link(
        group,
        wear_contrast.outputs["Value"],
        wear_amount.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Wear Amount"],
        wear_amount.inputs["Value_001"],
    )

    remaining_paint = subtract_math(
        nodes,
        "Remaining Paint",
        (1100, -1050),
    )

    set_socket(
        remaining_paint,
        "Value",
        1.0,
    )

    link(
        group,
        wear_amount.outputs["Value"],
        remaining_paint.inputs["Value_001"],
    )

    edge_noise = new_node(
        nodes,
        "ShaderNodeTexNoise",
        "Edge Breakup Noise",
        (300, -1500),
    )

    set_socket(
        edge_noise,
        "Scale",
        22.0,
    )

    set_socket(
        edge_noise,
        "Detail",
        4.0,
    )

    set_socket(
        edge_noise,
        "Roughness",
        0.8,
    )

    link(
        group,
        texcoord.outputs["Generated"],
        edge_noise.inputs["Vector"],
    )

    edge_ramp = new_node(
        nodes,
        "ShaderNodeValToRGB",
        "Edge Breakup Pattern",
        (500, -1500),
    )

    edge_ramp.color_ramp.elements[0].position = 0.42
    edge_ramp.color_ramp.elements[1].position = 0.58

    link(
        group,
        edge_noise.outputs["Fac"],
        edge_ramp.inputs["Fac"],
    )

    edge_breakup = multiply_math(
        nodes,
        "Edge Breakup Amount",
        (750, -1500),
    )

    link(
        group,
        edge_ramp.outputs["Color"],
        edge_breakup.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Edge Breakup"],
        edge_breakup.inputs["Value_001"],
    )

    edge_remaining = subtract_math(
        nodes,
        "Edge Remaining",
        (950, -1500),
    )

    set_socket(
        edge_remaining,
        "Value",
        1.0,
    )

    link(
        group,
        edge_breakup.outputs["Value"],
        edge_remaining.inputs["Value_001"],
    )

    wear_mask = multiply_math(
        nodes,
        "Wear Mask",
        (1150, -650),
    )

    link(
        group,
        base_mask.outputs["Value"],
        wear_mask.inputs["Value"],
    )

    link(
        group,
        remaining_paint.outputs["Value"],
        wear_mask.inputs["Value_001"],
    )

    final_mask = multiply_math(
        nodes,
        "FINAL DECAL MASK",
        (1350, -500),
    )

    link(
        group,
        wear_mask.outputs["Value"],
        final_mask.inputs["Value"],
    )

    link(
        group,
        edge_remaining.outputs["Value"],
        final_mask.inputs["Value_001"],
    )

    color_noise = new_node(
        nodes,
        "ShaderNodeTexNoise",
        "Paint Variation Noise",
        (500, -1750),
    )

    set_socket(
        color_noise,
        "Scale",
        18.0,
    )

    set_socket(
        color_noise,
        "Detail",
        3.0,
    )

    set_socket(
        color_noise,
        "Roughness",
        0.6,
    )

    link(
        group,
        texcoord.outputs["Generated"],
        color_noise.inputs["Vector"],
    )

    variation_ramp = new_node(
        nodes,
        "ShaderNodeValToRGB",
        "Paint Variation",
        (700, -1750),
    )

    variation_ramp.color_ramp.elements[0].color = (
        0.65,
        0.65,
        0.65,
        1.0,
    )

    variation_ramp.color_ramp.elements[1].color = (
        1.0,
        1.0,
        1.0,
        1.0,
    )

    link(
        group,
        color_noise.outputs["Fac"],
        variation_ramp.inputs["Fac"],
    )

    paint_color = new_node(
        nodes,
        "ShaderNodeMixRGB",
        "Paint Color Variation",
        (900, -1700),
    )

    paint_color.blend_type = "MULTIPLY"

    link(
        group,
        group_input.outputs["Paint Variation"],
        paint_color.inputs[0],
    )

    link(
        group,
        group_input.outputs["Paint Color"],
        paint_color.inputs[1],
    )

    link(
        group,
        variation_ramp.outputs["Color"],
        paint_color.inputs[2],
    )

    dirt_noise = new_node(
        nodes,
        "ShaderNodeTexNoise",
        "Road Dirt Noise",
        (500, -1950),
    )

    set_socket(
        dirt_noise,
        "Detail",
        5.0,
    )

    set_socket(
        dirt_noise,
        "Roughness",
        0.85,
    )

    link(
        group,
        texcoord.outputs["Generated"],
        dirt_noise.inputs["Vector"],
    )

    link(
        group,
        group_input.outputs["Dirt Scale"],
        dirt_noise.inputs["Scale"],
    )

    dirt_ramp = new_node(
        nodes,
        "ShaderNodeValToRGB",
        "Dirt Pattern",
        (700, -1950),
    )

    dirt_ramp.color_ramp.elements[0].position = 0.30
    dirt_ramp.color_ramp.elements[1].position = 0.70

    link(
        group,
        dirt_noise.outputs["Fac"],
        dirt_ramp.inputs["Fac"],
    )

    dirt_contrast = math_node(
        nodes,
        "Dirt Contrast",
        "POWER",
        (900, -1950),
    )

    link(
        group,
        dirt_ramp.outputs["Color"],
        dirt_contrast.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Dirt Contrast"],
        dirt_contrast.inputs["Value_001"],
    )

    dirt_amount = multiply_math(
        nodes,
        "Dirt Amount",
        (1050, -1950),
    )

    link(
        group,
        dirt_contrast.outputs["Value"],
        dirt_amount.inputs["Value"],
    )

    link(
        group,
        group_input.outputs["Dirt Amount"],
        dirt_amount.inputs["Value_001"],
    )

    dirt_color = new_node(
        nodes,
        "ShaderNodeRGB",
        "Road Dirt Color",
        (900, -2150),
    )

    dirt_color.outputs["Color"].default_value = (
        0.20,
        0.17,
        0.13,
        1.0,
    )

    dirty_paint = new_node(
        nodes,
        "ShaderNodeMixRGB",
        "Dirty Paint",
        (1150, -1750),
    )

    dirty_paint.blend_type = "MIX"

    link(
        group,
        dirt_amount.outputs["Value"],
        dirty_paint.inputs[0],
    )

    link(
        group,
        paint_color.outputs["Color"],
        dirty_paint.inputs[1],
    )

    link(
        group,
        dirt_color.outputs["Color"],
        dirty_paint.inputs[2],
    )

    principled = new_node(
        nodes,
        "ShaderNodeBsdfPrincipled",
        "Crosswalk Paint",
        (1450, 100),
    )

    link(
        group,
        dirty_paint.outputs["Color"],
        principled.inputs["Base Color"],
    )

    link(
        group,
        group_input.outputs["Roughness"],
        principled.inputs["Roughness"],
    )

    link(
        group,
        final_mask.outputs["Value"],
        principled.inputs["Alpha"],
    )

    bump = new_node(
        nodes,
        "ShaderNodeBump",
        "Paint Wear Bump",
        (1200, -300),
    )

    link(
        group,
        wear_amount.outputs["Value"],
        bump.inputs["Height"],
    )

    link(
        group,
        group_input.outputs["Bump Strength"],
        bump.inputs["Strength"],
    )

    link(
        group,
        group_input.outputs["Bump Distance"],
        bump.inputs["Distance"],
    )

    link(
        group,
        bump.outputs["Normal"],
        principled.inputs["Normal"],
    )

    link(
        group,
        principled.outputs["BSDF"],
        group_output.inputs["Shader"],
    )

    link(
        group,
        final_mask.outputs["Value"],
        group_output.inputs["Decal Mask"],
    )

    return group


def create_crosswalk_material():
    """Create the crosswalk decal material."""

    material = bpy.data.materials.get(MATERIAL_NAME)

    if material is None:
        material = bpy.data.materials.new(MATERIAL_NAME)

    tree = material.node_tree

    nodes = tree.nodes
    links = tree.links

    nodes.clear()

    group = create_crosswalk_group()

    group_node = nodes.new("ShaderNodeGroup")
    group_node.name = GROUP_NAME
    group_node.label = "CROSSWALK DECAL"
    group_node.node_tree = group
    group_node.location = (-300, 0)
    group_node.width = 300

    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "Material Output"
    output.location = (150, 0)

    links.new(
        group_node.outputs["Shader"],
        output.inputs["Surface"],
    )

    return material


def create_preview_plane(material):
    """Create a UV-mapped preview plane."""

    old = bpy.data.objects.get(PREVIEW_NAME)

    if old:
        bpy.data.objects.remove(
            old,
            do_unlink=True,
        )

    bpy.ops.mesh.primitive_plane_add(
        size=2.0,
        location=(0.0, 0.0, 0.0),
    )

    obj = bpy.context.object
    obj.name = PREVIEW_NAME

    obj.data.materials.append(material)

    return obj


def main():
    """create the procedural crosswalk decal."""

    material = create_crosswalk_material()

    obj = create_preview_plane(material)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    print("")
    print("=" * 72)
    print("PROCEDURAL CROSSWALK DECAL")
    print("=" * 72)
    print(f"Material : {material.name}")
    print(f"Node Group: {GROUP_NAME}")
    print(f"Preview  : {obj.name}")
    print("=" * 72)
    print("Generated successfully.")
    print("")
    print("Position X/Y and Edge Softness are now active.")
    print("")


if __name__ == "__main__":
    main()