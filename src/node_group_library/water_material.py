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


GROUP_NAME = "Procedural Water"
TAU = math.tau


def get_socket(sockets, name, socket_type=None):
    """Find a node socket by name or identifier."""

    for socket in sockets:
        if (
            socket.name == name
            or socket.identifier == name
        ):
            if (
                socket_type is None
                or socket.type == socket_type
            ):
                return socket

    if "_" in name:
        base_name, suffix = name.rsplit("_", 1)

        if suffix.isdigit():
            matches = [
                socket
                for socket in sockets
                if socket.name == base_name
                and (
                    socket_type is None
                    or socket.type == socket_type
                )
            ]

            index = int(suffix)

            if index < len(matches):
                return matches[index]

    raise KeyError(
        f"Socket not found: '{name}'. "
        f"Available sockets: "
        f"{[(socket.name, socket.identifier) for socket in sockets]}"
    )


def set_input(node, name, value):
    """Set a node input's default value."""
    socket = get_socket(node.inputs, name)
    socket.default_value = value
    return socket


def connect(tree, source, source_socket, target, target_socket):
    """Create a node link using socket names."""
    output_socket = get_socket(source.outputs, source_socket)
    input_socket = get_socket(target.inputs, target_socket)
    tree.links.new(output_socket, input_socket)


def create_node(tree, node_type, name, location, label=None):
    """Create and position a node."""
    node = tree.nodes.new(node_type)
    node.name = name
    node.label = label or name
    node.location = location
    return node


def create_math(tree, name, operation, location, value1=None, value2=None):
    """Create a Math node and optionally set its first two inputs."""
    node = create_node(
        tree,
        "ShaderNodeMath",
        name,
        location,
    )
    node.operation = operation

    if value1 is not None:
        node.inputs[0].default_value = value1

    if value2 is not None:
        node.inputs[1].default_value = value2

    return node


def create_map_range(
    tree,
    name,
    location,
    from_min,
    from_max,
    to_min,
    to_max,
):
    """Create a clamped Map Range node."""
    node = create_node(
        tree,
        "ShaderNodeMapRange",
        name,
        location,
    )

    node.clamp = True
    node.inputs["From Min"].default_value = from_min
    node.inputs["From Max"].default_value = from_max
    node.inputs["To Min"].default_value = to_min
    node.inputs["To Max"].default_value = to_max

    return node


def create_interface_socket(
    group,
    name,
    in_out,
    socket_type,
    default=None,
    minimum=None,
    maximum=None,
    description="",
):
    """Create an interface socket and configure its default and limits."""
    socket = group.interface.new_socket(
        name=name,
        in_out=in_out,
        socket_type=socket_type,
    )

    if default is not None and hasattr(socket, "default_value"):
        socket.default_value = default

    if minimum is not None and hasattr(socket, "min_value"):
        socket.min_value = minimum

    if maximum is not None and hasattr(socket, "max_value"):
        socket.max_value = maximum

    if description:
        socket.description = description

    return socket


def create_group_interface(group):
    """Create all public inputs and outputs for the water material."""
    group.interface.clear()

    # Water profile
    create_interface_socket(
        group, "Water Type", "INPUT", "NodeSocketFloat",
        1.0, 0.0, 3.0,
        "0 = Puddle, 1 = Lake, 2 = River, 3 = Sea",
    )

    # Surface transform
    create_interface_socket(
        group, "Position X", "INPUT", "NodeSocketFloat",
        0.0, -100.0, 100.0,
    )
    create_interface_socket(
        group, "Position Y", "INPUT", "NodeSocketFloat",
        0.0, -100.0, 100.0,
    )
    create_interface_socket(
        group, "Rotation", "INPUT", "NodeSocketFloat",
        0.0, -math.tau, math.tau,
    )

    # Primary wave
    create_interface_socket(
        group, "Wave Scale", "INPUT", "NodeSocketFloat",
        0.5, -100.0, 100.0,
    )
    create_interface_socket(
        group, "Wave Height", "INPUT", "NodeSocketFloat",
        2.0, -5.0, 5.0,
    )
    create_interface_socket(
        group, "Wave Distortion", "INPUT", "NodeSocketFloat",
        5.0, 0.0, 10.0,
    )
    create_interface_socket(
        group, "Wave Detail", "INPUT", "NodeSocketFloat",
        4.0, 0.0, 15.0,
    )
    create_interface_socket(
        group, "Wave Phase", "INPUT", "NodeSocketFloat",
        0.0, -1000.0, 1000.0,
        "Looping primary wave phase. Animate from 0 to 1.",
    )

    # Secondary wave
    create_interface_socket(
        group, "Secondary Wave Scale", "INPUT", "NodeSocketFloat",
        2.0, -100.0, 100.0,
    )
    create_interface_socket(
        group, "Secondary Wave Strength", "INPUT", "NodeSocketFloat",
        0.035, 0.0, 50.0,
    )
    create_interface_socket(
        group, "Secondary Wave Phase", "INPUT", "NodeSocketFloat",
        0.0, -1000.0, 1000.0,
        "Looping secondary wave phase. Animate independently from 0 to 1.",
    )

    # Fine surface detail
    create_interface_socket(
        group, "Ripple Scale", "INPUT", "NodeSocketFloat",
        60.0, -200.0, 200.0,
    )
    create_interface_socket(
        group, "Ripple Strength", "INPUT", "NodeSocketFloat",
        0.6, 0.0, 5.0,
    )
    create_interface_socket(
        group, "Ripple Detail", "INPUT", "NodeSocketFloat",
        0.7, 0.0, 15.0,
    )
    create_interface_socket(
        group, "Surface Distortion", "INPUT", "NodeSocketFloat",
        0.6, 0.0, 10.0,
    )
    create_interface_socket(
        group, "Flow Stretch", "INPUT", "NodeSocketFloat",
        1.0, 0.01, 10.0,
    )

    # Foam
    create_interface_socket(
        group, "Foam Amount", "INPUT", "NodeSocketFloat",
        0.15, 0.0, 5.0,
    )
    create_interface_socket(
        group, "Foam Scale", "INPUT", "NodeSocketFloat",
        8.0, 0.01, 100.0,
    )
    create_interface_socket(
        group, "Foam Threshold", "INPUT", "NodeSocketFloat",
        0.7, 0.0, 1.0,
    )
    create_interface_socket(
        group, "Foam Variation", "INPUT", "NodeSocketFloat",
        0.25, 0.0, 1.0,
    )
    create_interface_socket(
        group, "Foam Phase", "INPUT", "NodeSocketFloat",
        0.0, -1000.0, 1000.0,
        "Looping foam phase. Animate independently from 0 to 1.",
    )

    # Water colors
    create_interface_socket(
        group, "Shallow Water Color", "INPUT", "NodeSocketColor",
        (0.08, 0.35, 0.38, 1.0),
    )
    create_interface_socket(
        group, "Deep Water Color", "INPUT", "NodeSocketColor",
        (0.008, 0.045, 0.09, 1.0),
    )
    create_interface_socket(
        group, "Foam Color", "INPUT", "NodeSocketColor",
        (0.82, 0.92, 0.96, 1.0),
    )

    # Material properties
    create_interface_socket(
        group, "Roughness", "INPUT", "NodeSocketFloat",
        0.05, 0.0, 1.0,
    )
    create_interface_socket(
        group, "IOR", "INPUT", "NodeSocketFloat",
        1.333, 1.0, 2.0,
    )
    create_interface_socket(
        group, "Transmission", "INPUT", "NodeSocketFloat",
        0.85, 0.0, 1.0,
    )
    create_interface_socket(
        group, "Opacity", "INPUT", "NodeSocketFloat",
        1.0, 0.0, 1.0,
    )

    # Normal controls
    create_interface_socket(
        group, "Normal Strength", "INPUT", "NodeSocketFloat",
        0.5, 0.0, 5.0,
    )
    create_interface_socket(
        group, "Wave Normal Distance", "INPUT", "NodeSocketFloat",
        0.12, 0.001, 2.0,
    )
    create_interface_socket(
        group, "Secondary Normal Distance", "INPUT", "NodeSocketFloat",
        0.045, 0.001, 2.0,
    )
    create_interface_socket(
        group, "Ripple Normal Distance", "INPUT", "NodeSocketFloat",
        0.018, 0.001, 2.0,
    )

    # Outputs
    create_interface_socket(
        group, "Shader", "OUTPUT", "NodeSocketShader",
    )
    create_interface_socket(
        group, "Water Height", "OUTPUT", "NodeSocketFloat",
    )
    create_interface_socket(
        group, "Foam Mask", "OUTPUT", "NodeSocketFloat",
    )
    create_interface_socket(
        group, "Surface Normal", "OUTPUT", "NodeSocketVector",
    )


def create_node_group():
    """Build and return the procedural water material node group."""
    
    group = bpy.data.node_groups.get(GROUP_NAME)

    if group is None:
        group = bpy.data.node_groups.new(
            name=GROUP_NAME,
            type="ShaderNodeTree",
        )
    else:
        group.nodes.clear()
        group.interface.clear()

    create_group_interface(group)

    nodes = group.nodes
    links = group.links

    group_input = create_node(
        group,
        "NodeGroupInput",
        "Water Controls",
        (-1500, 0),
    )
    group_output = create_node(
        group,
        "NodeGroupOutput",
        "Water Outputs",
        (1900, 0),
    )
    
    group_output.is_active_output = True

    texcoord = create_node(
        group,
        "ShaderNodeTexCoord",
        "Water Coordinates",
        (-1500, 900),
    )

    mapping = create_node(
        group,
        "ShaderNodeMapping",
        "Water Mapping",
        (-1250, 900),
    )

    connect(group, texcoord, "UV", mapping, "Vector")
    # connect(group, group_input, "Position X", mapping, "Location")
    # connect(group, group_input, "Position Y", mapping, "Location")
    
    position = create_node(
        group,
        "ShaderNodeCombineXYZ",
        "Surface Position",
        (-1500, 650),
    )
    connect(group, group_input, "Position X", position, "X")
    connect(group, group_input, "Position Y", position, "Y")
    connect(group, position, "Vector", mapping, "Location")

    rotation = create_node(
        group,
        "ShaderNodeCombineXYZ",
        "Surface Rotation",
        (-1250, 650),
    )
    connect(group, group_input, "Rotation", rotation, "Z")
    connect(group, rotation, "Vector", mapping, "Rotation")
    
    flow_scale = create_node(
        group,
        "ShaderNodeCombineXYZ",
        "Directional Flow Scale",
        (-1000, 650),
    )

    set_input(flow_scale, "X", 1.0)
    set_input(flow_scale, "Y", 1.0)
    set_input(flow_scale, "Z", 1.0)

    connect(group, flow_scale, "Vector", mapping, "Scale")

    profile_specs = {
        "Profile Wave Scale": (0.0, 3.0, 0.55, 1.35),
        "Profile Wave Height": (0.0, 3.0, 0.20, 1.70),
        "Profile Flow": (0.0, 3.0, 1.0, 2.8),
        "Profile Roughness": (0.0, 3.0, 0.025, 0.16),
        "Profile Ripple": (0.0, 3.0, 0.25, 1.35),
        "Profile Foam": (0.0, 3.0, 0.0, 1.0),
    }

    profile_nodes = {}

    profile_y = 400

    for index, (name, values) in enumerate(profile_specs.items()):
        node = create_map_range(
            group,
            name,
            (-1000, profile_y - index * 190),
            *values,
        )
        connect(group, group_input, "Water Type", node, "Value")
        profile_nodes[name] = node
        
    flow_profile = create_math(
        group,
        "Apply Flow Profile",
        "MULTIPLY",
        (-650, 650),
    )

    connect(
        group,
        group_input,
        "Flow Stretch",
        flow_profile,
        "Value",
    )

    connect(
        group,
        profile_nodes["Profile Flow"],
        "Result",
        flow_profile,
        "Value_001",
    )

    connect(
        group,
        flow_profile,
        "Value",
        flow_scale,
        "X",
    )

    wave_scale_profile = create_math(
        group, "Apply Wave Scale Profile", "MULTIPLY",
        (-650, 450),
    )
    connect(group, group_input, "Wave Scale", wave_scale_profile, "Value")
    connect(
        group,
        profile_nodes["Profile Wave Scale"],
        "Result",
        wave_scale_profile,
        "Value_001",
    )

    wave_height_profile = create_math(
        group, "Apply Wave Height Profile", "MULTIPLY",
        (-650, 250),
    )
    connect(group, group_input, "Wave Height", wave_height_profile, "Value")
    connect(
        group,
        profile_nodes["Profile Wave Height"],
        "Result",
        wave_height_profile,
        "Value_001",
    )

    wave_phase = create_math(
        group, "Primary Phase Radians", "MULTIPLY",
        (-650, -100),
        value2=TAU,
    )
    connect(group, group_input, "Wave Phase", wave_phase, "Value")

    secondary_phase = create_math(
        group, "Secondary Phase Radians", "MULTIPLY",
        (-650, -250),
        value2=TAU,
    )
    connect(
        group,
        group_input,
        "Secondary Wave Phase",
        secondary_phase,
        "Value",
    )

    foam_phase = create_math(
        group, "Foam Phase Radians", "MULTIPLY",
        (-650, -450),
        value2=TAU,
    )
    
    connect(group, group_input, "Foam Phase", foam_phase, "Value")

    distortion_noise = create_node(
        group,
        "ShaderNodeTexNoise",
        "Surface Distortion Noise",
        (-650, 1000),
    )
    distortion_noise.noise_dimensions = "3D"
    set_input(distortion_noise, "Scale", 3.0)
    set_input(distortion_noise, "Detail", 4.0)
    set_input(distortion_noise, "Roughness", 0.65)
    connect(group, mapping, "Vector", distortion_noise, "Vector")

    distortion_center = create_node(
        group,
        "ShaderNodeVectorMath",
        "Center Distortion",
        (-400, 1000),
    )
    distortion_center.operation = "SUBTRACT"
    set_input(distortion_center, "Vector_001", (0.5, 0.5, 0.5))
    connect(group, distortion_noise, "Color", distortion_center, "Vector")

    distortion_strength = create_math(
        group, "Surface Distortion Strength", "MULTIPLY",
        (-150, 1000),
    )
    connect(
        group,
        group_input,
        "Surface Distortion",
        distortion_strength,
        "Value",
    )
    set_input(distortion_strength, "Value_001", 0.15)

    distortion_scale = create_node(
        group,
        "ShaderNodeVectorMath",
        "Scale Surface Distortion",
        (100, 1000),
    )
    distortion_scale.operation = "SCALE"
    connect(
        group,
        distortion_center,
        "Vector",
        distortion_scale,
        "Vector",
    )
    connect(
        group,
        distortion_strength,
        "Value",
        distortion_scale,
        "Scale",
    )

    distorted_coordinates = create_node(
        group,
        "ShaderNodeVectorMath",
        "Distorted Water Coordinates",
        (350, 1000),
    )
    distorted_coordinates.operation = "ADD"
    connect(
        group,
        mapping,
        "Vector",
        distorted_coordinates,
        "Vector",
    )
    connect(
        group,
        distortion_scale,
        "Vector",
        distorted_coordinates,
        "Vector_001",
    )

    primary_wave = create_node(
        group,
        "ShaderNodeTexWave",
        "Primary Water Wave",
        (600, 800),
    )
    primary_wave.wave_type = "BANDS"
    primary_wave.bands_direction = "X"
    primary_wave.wave_profile = "SIN"

    connect(
        group,
        distorted_coordinates,
        "Vector",
        primary_wave,
        "Vector",
    )
    connect(
        group,
        wave_scale_profile,
        "Value",
        primary_wave,
        "Scale",
    )
    connect(
        group,
        group_input,
        "Wave Distortion",
        primary_wave,
        "Distortion",
    )
    connect(
        group,
        group_input,
        "Wave Detail",
        primary_wave,
        "Detail",
    )
    connect(
        group,
        wave_phase,
        "Value",
        primary_wave,
        "Phase Offset",
    )

    secondary_wave = create_node(
        group,
        "ShaderNodeTexWave",
        "Secondary Water Wave",
        (600, 400),
    )
    secondary_wave.wave_type = "BANDS"
    secondary_wave.bands_direction = "Y"
    secondary_wave.wave_profile = "SIN"

    secondary_scale = create_math(
        group, "Secondary Wave Scale", "MULTIPLY",
        (350, 400),
    )
    connect(
        group,
        group_input,
        "Secondary Wave Scale",
        secondary_scale,
        "Value",
    )
    set_input(secondary_scale, "Value_001", 1.0)

    connect(
        group,
        distorted_coordinates,
        "Vector",
        secondary_wave,
        "Vector",
    )
    connect(
        group,
        secondary_scale,
        "Value",
        secondary_wave,
        "Scale",
    )
    connect(
        group,
        group_input,
        "Wave Distortion",
        secondary_wave,
        "Distortion",
    )
    connect(
        group,
        group_input,
        "Wave Detail",
        secondary_wave,
        "Detail",
    )
    connect(
        group,
        secondary_phase,
        "Value",
        secondary_wave,
        "Phase Offset",
    )


    ripple_noise = create_node(
        group,
        "ShaderNodeTexNoise",
        "Fine Water Ripples",
        (600, 50),
    )
    ripple_noise.noise_dimensions = "3D"

    connect(
        group,
        distorted_coordinates,
        "Vector",
        ripple_noise,
        "Vector",
    )
    connect(
        group,
        group_input,
        "Ripple Scale",
        ripple_noise,
        "Scale",
    )
    connect(
        group,
        group_input,
        "Ripple Detail",
        ripple_noise,
        "Detail",
    )
    set_input(ripple_noise, "Roughness", 0.55)

    # Center the ripple noise around zero.
    ripple_center = create_math(
        group, "Center Ripple Noise", "SUBTRACT",
        (850, 50),
        value2=0.5,
    )
    connect(group, ripple_noise, "Fac", ripple_center, "Value")
        
    ripple_amplitude = create_math(
        group,
        "Ripple Amplitude",
        "MULTIPLY",
        (1100, 50),
    )

    connect(
        group,
        ripple_center,
        "Value",
        ripple_amplitude,
        "Value",
    )

    # Apply the water-type ripple profile.
    ripple_profile = create_math(
        group,
        "Apply Ripple Profile",
        "MULTIPLY",
        (850, -150),
    )

    connect(
        group,
        group_input,
        "Ripple Strength",
        ripple_profile,
        "Value",
    )

    connect(
        group,
        profile_nodes["Profile Ripple"],
        "Result",
        ripple_profile,
        "Value_001",
    )

    connect(
        group,
        ripple_profile,
        "Value",
        ripple_amplitude,
        "Value_001",
    )

    primary_center = create_math(
        group, "Center Primary Wave", "SUBTRACT",
        (850, 800),
        value2=0.5,
    )
    connect(group, primary_wave, "Fac", primary_center, "Value")

    primary_amplitude = create_math(
        group, "Primary Wave Amplitude", "MULTIPLY",
        (1100, 800),
    )
    connect(
        group,
        primary_center,
        "Value",
        primary_amplitude,
        "Value",
    )
    connect(
        group,
        wave_height_profile,
        "Value",
        primary_amplitude,
        "Value_001",
    )

    secondary_center = create_math(
        group, "Center Secondary Wave", "SUBTRACT",
        (850, 450),
        value2=0.5,
    )
    connect(
        group,
        secondary_wave,
        "Fac",
        secondary_center,
        "Value",
    )

    secondary_amplitude = create_math(
        group, "Secondary Wave Amplitude", "MULTIPLY",
        (1100, 450),
    )
    connect(
        group,
        secondary_center,
        "Value",
        secondary_amplitude,
        "Value",
    )
    connect(
        group,
        group_input,
        "Secondary Wave Strength",
        secondary_amplitude,
        "Value_001",
    )

    height_primary_secondary = create_math(
        group, "Combine Primary and Secondary Waves", "ADD",
        (1350, 700),
    )
    connect(
        group,
        primary_amplitude,
        "Value",
        height_primary_secondary,
        "Value",
    )
    connect(
        group,
        secondary_amplitude,
        "Value",
        height_primary_secondary,
        "Value_001",
    )

    combined_height = create_math(
        group, "Final Water Height", "ADD",
        (1550, 600),
    )
    connect(
        group,
        height_primary_secondary,
        "Value",
        combined_height,
        "Value",
    )
    connect(
        group,
        ripple_amplitude,
        "Value",
        combined_height,
        "Value_001",
    )
    
    foam_separate = create_node(
        group,
        "ShaderNodeSeparateXYZ",
        "Separate Foam Coordinates",
        (-350, -800),
    )

    connect(
        group,
        mapping,
        "Vector",
        foam_separate,
        "Vector",
    )

    foam_sine = create_math(
        group,
        "Foam Phase Sine",
        "SINE",
        (-400, -1050),
    )

    foam_cosine = create_math(
        group,
        "Foam Phase Cosine",
        "COSINE",
        (-400, -1250),
    )

    connect(
        group,
        foam_phase,
        "Value",
        foam_sine,
        "Value",
    )

    connect(
        group,
        foam_phase,
        "Value",
        foam_cosine,
        "Value",
    )

    foam_coordinates = create_node(
        group,
        "ShaderNodeCombineXYZ",
        "Animated Foam Coordinates",
        (-100, -800),
    )

    connect(
        group,
        foam_separate,
        "X",
        foam_coordinates,
        "X",
    )

    connect(
        group,
        foam_separate,
        "Y",
        foam_coordinates,
        "Y",
    )

    connect(
        group,
        foam_sine,
        "Value",
        foam_coordinates,
        "Z",
    )

    foam_noise = create_node(
        group,
        "ShaderNodeTexNoise",
        "Animated Foam Noise",
        (150, -800),
    )

    foam_noise.noise_dimensions = "4D"

    connect(
        group,
        foam_coordinates,
        "Vector",
        foam_noise,
        "Vector",
    )

    connect(
        group,
        foam_cosine,
        "Value",
        foam_noise,
        "W",
    )

    connect(
        group,
        group_input,
        "Foam Scale",
        foam_noise,
        "Scale",
    )

    set_input(foam_noise, "Detail", 3.0)
    set_input(foam_noise, "Roughness", 0.55)

    foam_wave_max = create_math(
        group,
        "Maximum Wave Crest",
        "MAXIMUM",
        (900, -750),
    )

    connect(
        group,
        primary_wave,
        "Fac",
        foam_wave_max,
        "Value",
    )

    connect(
        group,
        secondary_wave,
        "Fac",
        foam_wave_max,
        "Value_001",
    )

    foam_crest = create_math(
        group,
        "Detect Foam Crests",
        "GREATER_THAN",
        (1150, -750),
    )

    connect(
        group,
        foam_wave_max,
        "Value",
        foam_crest,
        "Value",
    )

    connect(
        group,
        group_input,
        "Foam Threshold",
        foam_crest,
        "Value_001",
    )
    
    foam_variation_center = create_math(
        group, "Center Foam Variation", "SUBTRACT",
        (400, -500),
        value2=0.5,
    )
    connect(
        group,
        foam_noise,
        "Fac",
        foam_variation_center,
        "Value",
    )

    foam_variation_strength = create_math(
        group, "Foam Variation Strength", "MULTIPLY",
        (650, -500),
    )
    connect(
        group,
        foam_variation_center,
        "Value",
        foam_variation_strength,
        "Value",
    )
    connect(
        group,
        group_input,
        "Foam Variation",
        foam_variation_strength,
        "Value_001",
    )

    foam_field = create_math(
        group, "Foam Field", "ADD",
        (900, -500),
    )
    connect(
        group,
        foam_crest,
        "Value",
        foam_field,
        "Value",
    )
    connect(
        group,
        foam_variation_strength,
        "Value",
        foam_field,
        "Value_001",
    )

    foam_profile = create_math(
        group, "Apply Foam Profile", "MULTIPLY",
        (1150, -500),
    )
    connect(
        group,
        foam_field,
        "Value",
        foam_profile,
        "Value",
    )
    connect(
        group,
        profile_nodes["Profile Foam"],
        "Result",
        foam_profile,
        "Value_001",
    )

    foam_amount = create_math(
        group, "Foam Amount Control", "MULTIPLY",
        (1400, -500),
    )
    connect(
        group,
        foam_profile,
        "Value",
        foam_amount,
        "Value",
    )
    connect(
        group,
        group_input,
        "Foam Amount",
        foam_amount,
        "Value_001",
    )

    foam_mask = create_map_range(
        group,
        "Clamp Foam Mask",
        (1600, -500),
        0.0,
        1.0,
        0.0,
        1.0,
    )
    connect(
        group,
        foam_amount,
        "Value",
        foam_mask,
        "Value",
    )

    color_noise = create_node(
        group,
        "ShaderNodeTexNoise",
        "Water Color Variation",
        (600, -1000),
    )
    color_noise.noise_dimensions = "3D"
    set_input(color_noise, "Scale", 2.5)
    set_input(color_noise, "Detail", 4.0)
    set_input(color_noise, "Roughness", 0.55)
    connect(
        group,
        mapping,
        "Vector",
        color_noise,
        "Vector",
    )

    color_mix = create_node(
        group,
        "ShaderNodeMixRGB",
        "Shallow Deep Water Color",
        (900, -1000),
    )
    color_mix.blend_type = "MIX"
    connect(
        group,
        color_noise,
        "Fac",
        color_mix,
        "Fac",
    )
    connect(
        group,
        group_input,
        "Shallow Water Color",
        color_mix,
        "Color1",
    )
    connect(
        group,
        group_input,
        "Deep Water Color",
        color_mix,
        "Color2",
    )

    foam_color_mix = create_node(
        group,
        "ShaderNodeMixRGB",
        "Mix Foam into Water Color",
        (1350, -1000),
    )
    foam_color_mix.blend_type = "MIX"
    connect(
        group,
        foam_mask,
        "Result",
        foam_color_mix,
        "Fac",
    )
    connect(
        group,
        color_mix,
        "Color",
        foam_color_mix,
        "Color1",
    )
    connect(
        group,
        group_input,
        "Foam Color",
        foam_color_mix,
        "Color2",
    )

    primary_bump = create_node(
        group,
        "ShaderNodeBump",
        "Primary Wave Bump",
        (850, 1200),
    )
    connect(
        group,
        group_input,
        "Wave Normal Distance",
        primary_bump,
        "Distance",
    )
    connect(
        group,
        group_input,
        "Normal Strength",
        primary_bump,
        "Strength",
    )
    connect(
        group,
        primary_wave,
        "Fac",
        primary_bump,
        "Height",
    )

    secondary_bump = create_node(
        group,
        "ShaderNodeBump",
        "Secondary Wave Bump",
        (1150, 1200),
    )
    connect(
        group,
        group_input,
        "Secondary Normal Distance",
        secondary_bump,
        "Distance",
    )
    connect(
        group,
        group_input,
        "Normal Strength",
        secondary_bump,
        "Strength",
    )
    connect(
        group,
        secondary_wave,
        "Fac",
        secondary_bump,
        "Height",
    )
    connect(
        group,
        primary_bump,
        "Normal",
        secondary_bump,
        "Normal",
    )

    ripple_bump = create_node(
        group,
        "ShaderNodeBump",
        "Fine Ripple Bump",
        (1450, 1200),
    )
    connect(
        group,
        group_input,
        "Ripple Normal Distance",
        ripple_bump,
        "Distance",
    )
    connect(
        group,
        group_input,
        "Normal Strength",
        ripple_bump,
        "Strength",
    )
    connect(
        group,
        ripple_noise,
        "Fac",
        ripple_bump,
        "Height",
    )
    connect(
        group,
        secondary_bump,
        "Normal",
        ripple_bump,
        "Normal",
    )

    profile_roughness = create_math(
        group, "Water Type Roughness", "ADD",
        (900, 500),
    )
    connect(
        group,
        profile_nodes["Profile Roughness"],
        "Result",
        profile_roughness,
        "Value",
    )
    connect(
        group,
        group_input,
        "Roughness",
        profile_roughness,
        "Value_001",
    )

    roughness_clamp = create_map_range(
        group,
        "Clamp Water Roughness",
        (1150, 500),
        0.0,
        1.0,
        0.0,
        1.0,
    )
    connect(
        group,
        profile_roughness,
        "Value",
        roughness_clamp,
        "Value",
    )

    principled = create_node(
        group,
        "ShaderNodeBsdfPrincipled",
        "Water Principled BSDF",
        (1600, 500),
    )

    connect(
        group,
        foam_color_mix,
        "Color",
        principled,
        "Base Color",
    )
    connect(
        group,
        roughness_clamp,
        "Result",
        principled,
        "Roughness",
    )
    connect(
        group,
        group_input,
        "IOR",
        principled,
        "IOR",
    )
    connect(
        group,
        group_input,
        "Opacity",
        principled,
        "Alpha",
    )

    transmission_socket = principled.inputs.get("Transmission Weight")
    if transmission_socket is None:
        transmission_socket = principled.inputs.get("Transmission")

    if transmission_socket is not None:
        connect(
            group,
            group_input,
            "Transmission",
            principled,
            transmission_socket.name,
        )

    connect(
        group,
        ripple_bump,
        "Normal",
        principled,
        "Normal",
    )

    connect(
        group,
        principled,
        "BSDF",
        group_output,
        "Shader",
    )

    connect(
        group,
        combined_height,
        "Value",
        group_output,
        "Water Height",
    )
    connect(
        group,
        foam_mask,
        "Result",
        group_output,
        "Foam Mask",
    )
    connect(
        group,
        ripple_bump,
        "Normal",
        group_output,
        "Surface Normal",
    )

    print(
        f"\n[{GROUP_NAME}] GROUP OUTPUT DIAGNOSTICS"
    )

    for output_node in (
        node for node in group.nodes
        if node.bl_idname == "NodeGroupOutput"
    ):
        print(
            f"\n[{GROUP_NAME}] Output Node: {output_node.name}"
        )

        for index, socket in enumerate(output_node.inputs):

            print(
                f"\n[{GROUP_NAME}] Output Socket {index}"
            )
            print(f"    Name:       {socket.name!r}")
            print(f"    Identifier: {socket.identifier!r}")
            print(f"    Type:       {socket.type!r}")
            print(f"    Enabled:    {socket.enabled}")
            print(f"    Linked:     {socket.is_linked}")
            print(f"    Link Count: {len(socket.links)}")

            for link_index, link in enumerate(socket.links):
                print(
                    f"    Link {link_index}: "
                    f"{link.from_node.name} "
                    f"[{link.from_socket.name}] -> "
                    f"{link.to_node.name} "
                    f"[{link.to_socket.name}]"
                )

    print(
        f"\n[{GROUP_NAME}] TOTAL NODE LINKS: {len(group.links)}"
    )

    validate_node_group(group)
    return group


def validate_node_group(group):
    """Validate interface links and detect disconnected internal nodes.

    This performs structural graph checks. It does not render the material
    or prove that the resulting water appearance is physically accurate.
    """
    errors = []
    warnings = []

    nodes = list(group.nodes)
    links = list(group.links)

    group_inputs = [
        node for node in nodes
        if node.bl_idname == "NodeGroupInput"
    ]
    group_outputs = [
        node for node in nodes
        if node.bl_idname == "NodeGroupOutput"
    ]

    if len(group_inputs) != 1:
        errors.append(
            f"Expected one Group Input node; found {len(group_inputs)}."
        )

    if len(group_outputs) != 1:
        errors.append(
            f"Expected one Group Output node; found {len(group_outputs)}."
        )

    if errors:
        raise RuntimeError(
            "Water node group validation failed:\n- "
            + "\n- ".join(errors)
        )

    group_input = group_inputs[0]
    group_output = group_outputs[0]

    for socket in group_input.outputs:
        if not socket.is_linked:
            warnings.append(
                f"Unused group input: {socket.name}"
            )

    declared_outputs = [
        item
        for item in group.interface.items_tree
        if (
            item.item_type == "SOCKET"
            and item.in_out == "OUTPUT"
        )
    ]

    actual_sockets = [
        socket for socket in group_output.inputs
        if socket.identifier != "__extend__"
    ]

    if len(declared_outputs) != len(actual_sockets):
        errors.append(
            "Group output interface mismatch: "
            f"{len(declared_outputs)} declared output(s), "
            f"{len(actual_sockets)} Group Output socket(s)."
        )

    for index, socket in enumerate(actual_sockets):
        if not socket.is_linked:
            errors.append(
                "Unconnected group output: "
                f"index={index}, "
                f"name={socket.name!r}, "
                f"identifier={socket.identifier!r}, "
                f"type={socket.type!r}"
            )

    for node in nodes:
        if node in (group_input, group_output):
            continue

        has_linked_input = any(
            socket.is_linked for socket in node.inputs
        )
        has_linked_output = any(
            socket.is_linked for socket in node.outputs
        )

        # Nodes without inputs are valid procedural sources.
        if len(node.inputs) > 0 and not has_linked_input:
            errors.append(
                f"Node has no connected input: {node.name}"
            )

        if len(node.outputs) > 0 and not has_linked_output:
            errors.append(
                f"Node has no connected output: {node.name}"
            )

    for link in links:
        if link.from_node not in nodes:
            errors.append(
                f"Invalid source node in link: {link.from_node}"
            )
        if link.to_node not in nodes:
            errors.append(
                f"Invalid destination node in link: {link.to_node}"
            )

    if errors:
        message = (
            "Water node group validation failed:\n- "
            + "\n- ".join(errors)
        )
        raise RuntimeError(message)

    print(
        f"[{GROUP_NAME}] Structural validation passed: "
        f"{len(nodes)} nodes, {len(links)} links."
    )

    if warnings:
        for warning in warnings:
            print(f"[{GROUP_NAME}] WARNING: {warning}")

    return True


def add_water_group_to_material(material):
    """Add the water node group to a material and connect its shader output."""
    if material is None:
        raise ValueError("A valid material is required.")

    material.use_nodes = True
    node_tree = material.node_tree

    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is None:
        group = create_node_group()

    group_node = node_tree.nodes.new("ShaderNodeGroup")
    group_node.node_tree = group
    group_node.label = GROUP_NAME
    group_node.location = (0, 0)

    output = node_tree.nodes.get("Material Output")
    if output is None:
        output = node_tree.nodes.new("ShaderNodeOutputMaterial")
        output.location = (300, 0)

    node_tree.links.new(
        group_node.outputs["Shader"],
        output.inputs["Surface"],
    )

    return group_node


def register():
    """Create or update the procedural water node group."""
    create_node_group()


def unregister():
    """No persistent classes are registered by this module."""
    pass


if __name__ == "__main__":
    register()
