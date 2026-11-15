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


GROUP_NAME = "Curvature Map"
GROUP_DESCRIPTION = (
    "Shader-only curvature approximation combining Cycles Pointiness, "
    "Bevel normal variation, and Ambient Occlusion. Provides independent "
    "convex, concave, signed, bevel-detail, pointiness, and crevice outputs."
)

# Keep the required legacy output names stable for existing materials.
REQUIRED_OUTPUTS = (
    "Convex",
    "Concave",
    "Combined",
    "Curvature Shader",
)

OPTIONAL_OUTPUTS = (
    "Bevel Detail",
    "Crevice",
    "Pointiness",
)


def _new_node(nodes, node_type, name, location, label=None):
    """Create a named node and assign its editor position.

    Args:
        nodes: Node collection that owns the new node.
        node_type: Blender node type identifier.
        name: Stable internal node name.
        location: Two-element editor coordinate.
        label: Optional visible node label.

    Returns:
        The newly created Blender node.

    Raises:
        RuntimeError: If Blender cannot create the requested node type.
    """
    try:
        node = nodes.new(node_type)
    except Exception as exc:
        raise RuntimeError(
            f"Could not create node type '{node_type}' for '{name}'."
        ) from exc

    node.name = name
    node.label = label or name
    node.location = location
    return node


def _socket(node, socket_name, is_output=False):
    """Return a named node socket or raise a descriptive error.

    Args:
        node: Node containing the socket.
        socket_name: Exact Blender socket display name.
        is_output: True to search outputs; otherwise search inputs.

    Returns:
        The matching socket.

    Raises:
        RuntimeError: If the requested socket does not exist.
    """
    collection = node.outputs if is_output else node.inputs
    result = collection.get(socket_name)

    if result is None:
        direction = "output" if is_output else "input"
        available = [item.name for item in collection]
        raise RuntimeError(
            f"Node '{node.name}' has no {direction} socket "
            f"'{socket_name}'. Available: {available}"
        )

    return result


def _link(tree, from_socket, to_socket):
    """Connect two sockets and return the created link.

    Args:
        tree: Node tree that owns the link.
        from_socket: Source output socket.
        to_socket: Destination input socket.

    Returns:
        The created node link.
    """
    return tree.links.new(from_socket, to_socket)


def _set_input(node, socket_name, value):
    """Set a node input's default value by its display name.

    Args:
        node: Node to configure.
        socket_name: Exact input socket name.
        value: Value accepted by the input socket.

    Raises:
        RuntimeError: If the named input is unavailable.
    """
    _socket(node, socket_name).default_value = value


def _math(nodes, name, operation, location, value_a=None, value_b=None):
    """Create a Shader Math node with optional default operands.

    Args:
        nodes: Node collection that owns the new node.
        name: Stable node name.
        operation: Blender ShaderNodeMath operation identifier.
        location: Two-element editor coordinate.
        value_a: Optional first operand default.
        value_b: Optional second operand default.

    Returns:
        The configured ShaderNodeMath node.
    """
    node = _new_node(
        nodes,
        "ShaderNodeMath",
        name,
        location,
    )
    node.operation = operation

    if value_a is not None:
        node.inputs[0].default_value = value_a

    if value_b is not None:
        node.inputs[1].default_value = value_b

    return node


def _float_socket(
    group,
    name,
    default,
    minimum,
    maximum,
    description,
    parent=None,
):
    """Add a bounded float input socket to the node-group interface.

    Args:
        group: Shader node group being constructed.
        name: Interface socket name.
        default: Default socket value.
        minimum: Minimum permitted value.
        maximum: Maximum permitted value.
        description: Tooltip description.
        parent: Optional interface panel.

    Returns:
        The created interface socket.
    """
    socket = group.interface.new_socket(
        name=name,
        in_out="INPUT",
        socket_type="NodeSocketFloat",
        description=description,
        parent=parent,
    )
    socket.default_value = default
    socket.min_value = minimum
    socket.max_value = maximum
    return socket


def _float_output(group, name, description):
    """Add a float output socket to the node-group interface.

    Args:
        group: Shader node group being constructed.
        name: Interface socket name.
        description: Tooltip description.

    Returns:
        The created interface socket.
    """
    return group.interface.new_socket(
        name=name,
        in_out="OUTPUT",
        socket_type="NodeSocketFloat",
        description=description,
    )


def _create_interface(group):
    """Create the complete public control and output interface.

    The original four output names are retained for compatibility.
    Additional outputs expose the independent approximation sources.

    Args:
        group: Shader node group being constructed.
    """
    geometry_panel = group.interface.new_panel(
        "Geometry Sources",
        description="Cycles geometry and ray-traced approximation sources.",
        default_closed=False,
    )
    _float_socket(
        group, "Pointiness Pivot", 0.50, 0.01, 0.99,
        "Threshold separating darker concave and brighter convex Pointiness.",
        geometry_panel,
    )
    _float_socket(
        group, "Pointiness Weight", 0.65, 0.0, 1.0,
        "Contribution of the topology-dependent Pointiness approximation.",
        geometry_panel,
    )
    _float_socket(
        group, "Bevel Radius", 0.025, 0.0001, 10.0,
        "World-space radius used by the Cycles Bevel node.",
        geometry_panel,
    )
    _float_socket(
        group, "Bevel Threshold", 0.01, 0.0, 1.0,
        "Normal-variance response below this value is suppressed.",
        geometry_panel,
    )
    _float_socket(
        group, "Bevel Softness", 0.20, 0.001, 2.0,
        "Width of the Bevel normal-variance transition.",
        geometry_panel,
    )
    _float_socket(
        group, "Bevel Weight", 0.35, 0.0, 1.0,
        "Contribution of unsigned Bevel detail to the convex output.",
        geometry_panel,
    )
    _float_socket(
        group, "AO Distance", 0.25, 0.001, 100.0,
        "World-space distance used by the Cycles Ambient Occlusion node.",
        geometry_panel,
    )
    _float_socket(
        group, "AO Threshold", 0.02, 0.0, 1.0,
        "Crevice response below this occlusion amount is suppressed.",
        geometry_panel,
    )
    _float_socket(
        group, "AO Softness", 0.35, 0.001, 2.0,
        "Width of the Ambient Occlusion crevice transition.",
        geometry_panel,
    )
    _float_socket(
        group, "AO Weight", 0.50, 0.0, 1.0,
        "Contribution of the AO crevice approximation to the concave output.",
        geometry_panel,
    )

    processing_panel = group.interface.new_panel(
        "Mask Processing",
        description="Shared thresholding and independent channel strengths.",
        default_closed=False,
    )
    _float_socket(
        group, "Mask Threshold", 0.0, 0.0, 0.999,
        "Suppresses weak responses after source blending.",
        processing_panel,
    )
    _float_socket(
        group, "Mask Softness", 0.35, 0.001, 1.0,
        "Transition width above the mask threshold.",
        processing_panel,
    )
    _float_socket(
        group, "Convex Strength", 1.0, 0.0, 5.0,
        "Independent intensity multiplier for the convex mask.",
        processing_panel,
    )
    _float_socket(
        group, "Concave Strength", 1.0, 0.0, 5.0,
        "Independent intensity multiplier for the concave mask.",
        processing_panel,
    )
    _float_socket(
        group, "Crevice Strength", 1.0, 0.0, 5.0,
        "Independent intensity multiplier for the crevice mask.",
        processing_panel,
    )
    _float_socket(
        group, "Contrast", 1.0, 0.1, 5.0,
        "Midpoint-centered contrast multiplier for processed masks.",
        processing_panel,
    )
    _float_socket(
        group, "Output Min", 0.0, 0.0, 1.0,
        "Lower bound of the final mask output range.",
        processing_panel,
    )
    _float_socket(
        group, "Output Max", 1.0, 0.0, 1.0,
        "Upper bound of the final mask output range. Keep >= Output Min.",
        processing_panel,
    )
    
    group.interface.new_socket(
        name="Curvature Shader",
        in_out="OUTPUT",
        socket_type="NodeSocketShader",
        description="Emission shader carrying the Combined grayscale result.",
    )
    _float_output(
        group, "Convex",
        "Processed convex approximation mask. White indicates convex response.",
    )
    _float_output(
        group, "Concave",
        "Processed concave approximation mask. White indicates concave response.",
    )
    _float_output(
        group, "Combined",
        "Signed-style mask: 0.5 neutral, brighter convex, darker concave.",
    )
    _float_output(
        group, "Bevel Detail",
        "Unsigned Bevel normal-variance detail mask; not signed curvature.",
    )
    _float_output(
        group, "Crevice",
        "Independent Ambient Occlusion-derived crevice mask.",
    )
    _float_output(
        group, "Pointiness",
        "Raw Cycles Geometry Pointiness signal, remapped to a 0-1 output.",
    )


def _map_range(
    nodes,
    tree,
    name,
    source,
    from_min,
    from_max,
    location,
):
    """Create a clamped smoothstep Map Range operation.

    Args:
        nodes: Node collection.
        tree: Owning node tree.
        name: Node name.
        source: Source value socket.
        from_min: Socket or numeric lower input bound.
        from_max: Socket or numeric upper input bound.
        location: Two-element editor coordinate.

    Returns:
        The Map Range Result output socket.
    """
    node = _new_node(
        nodes,
        "ShaderNodeMapRange",
        name,
        location,
    )
    node.interpolation_type = "SMOOTHSTEP"
    node.clamp = True

    _link(tree, source, node.inputs["Value"])

    if hasattr(from_min, "bl_idname"):
        _link(tree, from_min, node.inputs["From Min"])
    else:
        node.inputs["From Min"].default_value = from_min

    if hasattr(from_max, "bl_idname"):
        _link(tree, from_max, node.inputs["From Max"])
    else:
        node.inputs["From Max"].default_value = from_max

    node.inputs["To Min"].default_value = 0.0
    node.inputs["To Max"].default_value = 1.0
    return node.outputs["Result"]


def _weighted_blend(
    nodes,
    tree,
    name,
    weighted_sources,
    location,
):
    """Blend scalar sources using normalized non-negative weights.

    A small denominator floor prevents division by zero when all weights
    are zero. In that case, the numerator is also zero and the result is zero.

    Args:
        nodes: Node collection.
        tree: Owning node tree.
        name: Prefix used for generated node names.
        weighted_sources: Sequence of (signal_socket, weight_socket) pairs.
        location: Two-element editor coordinate.

    Returns:
        The normalized blended scalar output socket.
    """
    x, y = location
    weighted_values = []
    weight_sockets = []

    for index, (signal, weight) in enumerate(weighted_sources):
        multiply = _math(
            nodes,
            f"{name} - Source {index + 1} Weight",
            "MULTIPLY",
            (x, y - index * 170),
        )
        _link(tree, signal, multiply.inputs[0])
        _link(tree, weight, multiply.inputs[1])
        weighted_values.append(multiply.outputs[0])
        weight_sockets.append(weight)

    numerator = weighted_values[0]
    denominator = weight_sockets[0]

    for index in range(1, len(weighted_values)):
        add_value = _math(
            nodes,
            f"{name} - Sum Signal {index + 1}",
            "ADD",
            (x + 220, y - index * 170),
        )
        _link(tree, numerator, add_value.inputs[0])
        _link(tree, weighted_values[index], add_value.inputs[1])
        numerator = add_value.outputs[0]

        add_weight = _math(
            nodes,
            f"{name} - Sum Weight {index + 1}",
            "ADD",
            (x + 220, y - 900 - index * 170),
        )
        _link(tree, denominator, add_weight.inputs[0])
        _link(tree, weight_sockets[index], add_weight.inputs[1])
        denominator = add_weight.outputs[0]

    safe_denominator = _math(
        nodes,
        f"{name} - Safe Weight Sum",
        "MAXIMUM",
        (x + 460, y - 250),
        value_b=0.000001,
    )
    _link(tree, denominator, safe_denominator.inputs[0])

    divide = _math(
        nodes,
        f"{name} - Normalized Blend",
        "DIVIDE",
        (x + 680, y - 100),
    )
    _link(tree, numerator, divide.inputs[0])
    _link(tree, safe_denominator.outputs[0], divide.inputs[1])
    return divide.outputs[0]


def _clamp_0_1(nodes, tree, name, source, location):
    """Clamp a scalar signal to the normalized 0-1 range.

    Args:
        nodes: Node collection.
        tree: Owning node tree.
        name: Node-name prefix.
        source: Input scalar socket.
        location: Two-element editor coordinate.

    Returns:
        Clamped scalar output socket.
    """
    lower = _math(
        nodes, f"{name} - Lower Clamp", "MAXIMUM", location,
        value_b=0.0,
    )
    _link(tree, source, lower.inputs[0])

    upper = _math(
        nodes, f"{name} - Upper Clamp", "MINIMUM",
        (location[0] + 180, location[1]),
        value_b=1.0,
    )
    _link(tree, lower.outputs[0], upper.inputs[0])
    return upper.outputs[0]


def _process_mask(
    nodes,
    tree,
    group_input,
    name,
    source,
    strength_socket_name,
    location,
):
    """Apply threshold, strength, contrast, and output-range remapping.

    Args:
        nodes: Node collection.
        tree: Owning node tree.
        group_input: NodeGroupInput node.
        name: Channel name.
        source: Raw 0-1 source signal.
        strength_socket_name: Group input name for channel intensity.
        location: Two-element editor coordinate.

    Returns:
        Final processed mask output socket.
    """
    x, y = location

    threshold = _map_range(
        nodes,
        tree,
        f"{name} - Threshold and Softness",
        source,
        group_input.outputs["Mask Threshold"],
        _math(
            nodes,
            f"{name} - Threshold Plus Softness",
            "ADD",
            (x, y - 180),
        ).outputs[0],
        (x, y),
    )

    # Connect the threshold-plus-softness calculation after creating it.
    threshold_max_node = nodes.get(f"{name} - Threshold Plus Softness")
    _link(
        tree,
        group_input.outputs["Mask Threshold"],
        threshold_max_node.inputs[0],
    )
    _link(
        tree,
        group_input.outputs["Mask Softness"],
        threshold_max_node.inputs[1],
    )

    intensity = _math(
        nodes, f"{name} - Strength", "MULTIPLY", (x + 220, y)
    )
    _link(tree, threshold, intensity.inputs[0])
    _link(
        tree,
        group_input.outputs[strength_socket_name],
        intensity.inputs[1],
    )

    clamped_intensity = _clamp_0_1(
        nodes,
        tree,
        f"{name} - Intensity Clamp",
        intensity.outputs[0],
        (x + 440, y),
    )

    centered = _math(
        nodes, f"{name} - Center Around Half", "SUBTRACT",
        (x + 660, y),
        value_b=0.5,
    )
    _link(tree, clamped_intensity, centered.inputs[0])

    contrast = _math(
        nodes, f"{name} - Contrast", "MULTIPLY", (x + 860, y)
    )
    _link(tree, centered.outputs[0], contrast.inputs[0])
    _link(tree, group_input.outputs["Contrast"], contrast.inputs[1])

    restore_midpoint = _math(
        nodes, f"{name} - Restore Midpoint", "ADD", (x + 1060, y),
        value_b=0.5,
    )
    _link(tree, contrast.outputs[0], restore_midpoint.inputs[0])

    contrast_clamp = _clamp_0_1(
        nodes,
        tree,
        f"{name} - Contrast Clamp",
        restore_midpoint.outputs[0],
        (x + 1260, y),
    )

    range_width = _math(
        nodes, f"{name} - Output Range Width", "SUBTRACT",
        (x + 1480, y),
    )
    _link(tree, group_input.outputs["Output Max"], range_width.inputs[0])
    _link(tree, group_input.outputs["Output Min"], range_width.inputs[1])

    safe_range_width = _math(
        nodes, f"{name} - Nonnegative Range Width", "MAXIMUM",
        (x + 1660, y),
        value_b=0.0,
    )
    _link(tree, range_width.outputs[0], safe_range_width.inputs[0])

    scaled = _math(
        nodes, f"{name} - Scale Output Range", "MULTIPLY",
        (x + 1840, y),
    )
    _link(tree, contrast_clamp, scaled.inputs[0])
    _link(tree, safe_range_width.outputs[0], scaled.inputs[1])

    offset = _math(
        nodes, f"{name} - Apply Output Minimum", "ADD",
        (x + 2040, y),
    )
    _link(tree, scaled.outputs[0], offset.inputs[0])
    _link(tree, group_input.outputs["Output Min"], offset.inputs[1])

    return offset.outputs[0]


def _create_source_nodes(group, nodes, group_input):
    """Create and connect the three Cycles approximation sources.

    Args:
        group: Shader node tree.
        nodes: Node collection.
        group_input: Group input node.

    Returns:
        Dictionary containing raw source sockets.
    """
    geometry = _new_node(
        nodes,
        "ShaderNodeNewGeometry",
        "Source - Geometry",
        (-1800, 700),
    )

    pointiness = _socket(geometry, "Pointiness", is_output=True)

    # Pointiness is bright on convex regions and dark on concave regions.
    pivot = group_input.outputs["Pointiness Pivot"]

    pointiness_convex = _map_range(
        nodes,
        group,
        "Pointiness - Convex Extraction",
        pointiness,
        pivot,
        1.0,
        (-1450, 950),
    )

    invert_pointiness = _math(
        nodes,
        "Pointiness - Invert",
        "SUBTRACT",
        (-1450, 600),
        value_a=1.0,
    )
    _link(group, pointiness, invert_pointiness.inputs[1])

    inverse_pivot = _math(
        nodes,
        "Pointiness - Inverse Pivot",
        "SUBTRACT",
        (-1250, 450),
        value_a=1.0,
    )
    _link(group, pivot, inverse_pivot.inputs[1])

    pointiness_concave = _map_range(
        nodes,
        group,
        "Pointiness - Concave Extraction",
        invert_pointiness.outputs[0],
        inverse_pivot.outputs[0],
        1.0,
        (-1050, 550),
    )

    bevel = _new_node(
        nodes,
        "ShaderNodeBevel",
        "Source - Bevel Normal Variation",
        (-1800, 100),
    )
    bevel.samples = 4
    _link(
        group,
        group_input.outputs["Bevel Radius"],
        bevel.inputs["Radius"],
    )

    normal_dot = _new_node(
        nodes,
        "ShaderNodeVectorMath",
        "Bevel - Original Versus Bevel Normal",
        (-1450, 100),
    )
    normal_dot.operation = "DOT_PRODUCT"
    _link(group, geometry.outputs["Normal"], normal_dot.inputs[0])
    _link(group, bevel.outputs["Normal"], normal_dot.inputs[1])

    bevel_variance = _math(
        nodes,
        "Bevel - Angular Variance",
        "SUBTRACT",
        (-1200, 100),
        value_a=1.0,
    )
    _link(group, normal_dot.outputs["Value"], bevel_variance.inputs[1])

    bevel_threshold_max = _math(
        nodes,
        "Bevel - Threshold Plus Softness",
        "ADD",
        (-1000, -80),
    )
    _link(
        group,
        group_input.outputs["Bevel Threshold"],
        bevel_threshold_max.inputs[0],
    )
    _link(
        group,
        group_input.outputs["Bevel Softness"],
        bevel_threshold_max.inputs[1],
    )

    bevel_detail = _map_range(
        nodes,
        group,
        "Bevel - Detail Extraction",
        bevel_variance.outputs[0],
        group_input.outputs["Bevel Threshold"],
        bevel_threshold_max.outputs[0],
        (-800, 100),
    )

    ao = _new_node(
        nodes,
        "ShaderNodeAmbientOcclusion",
        "Source - Ambient Occlusion",
        (-1800, -350),
    )
    ao.samples = 16
    ao.inside = False
    ao.only_local = True
    _link(group, group_input.outputs["AO Distance"], ao.inputs["Distance"])

    ao_invert = _math(
        nodes,
        "AO - Convert Occlusion To Crevice",
        "SUBTRACT",
        (-1450, -350),
        value_a=1.0,
    )
    _link(group, ao.outputs["AO"], ao_invert.inputs[1])

    ao_threshold_max = _math(
        nodes,
        "AO - Threshold Plus Softness",
        "ADD",
        (-1200, -550),
    )
    _link(
        group,
        group_input.outputs["AO Threshold"],
        ao_threshold_max.inputs[0],
    )
    _link(
        group,
        group_input.outputs["AO Softness"],
        ao_threshold_max.inputs[1],
    )

    ao_crevice = _map_range(
        nodes,
        group,
        "AO - Crevice Extraction",
        ao_invert.outputs[0],
        group_input.outputs["AO Threshold"],
        ao_threshold_max.outputs[0],
        (-950, -350),
    )

    pointiness_display = _map_range(
        nodes,
        group,
        "Pointiness - Display Remap",
        pointiness,
        0.0,
        1.0,
        (-800, 650),
    )

    return {
        "pointiness_convex": pointiness_convex,
        "pointiness_concave": pointiness_concave,
        "bevel_detail": bevel_detail,
        "ao_crevice": ao_crevice,
        "pointiness_display": pointiness_display,
    }


def _create_processing_and_outputs(group, nodes, group_input, sources, group_output):
    """Blend source signals, process masks, and connect public outputs.

    Args:
        group: Shader node tree.
        nodes: Node collection.
        group_input: Group input node.
        sources: Source socket dictionary from _create_source_nodes().
        group_output: Group output node.
    """
    convex_raw = _weighted_blend(
        nodes,
        group,
        "Convex Source Blend",
        (
            (sources["pointiness_convex"], group_input.outputs["Pointiness Weight"]),
            (sources["bevel_detail"], group_input.outputs["Bevel Weight"]),
        ),
        (-350, 1050),
    )

    concave_raw = _weighted_blend(
        nodes,
        group,
        "Concave Source Blend",
        (
            (sources["pointiness_concave"], group_input.outputs["Pointiness Weight"]),
            (sources["ao_crevice"], group_input.outputs["AO Weight"]),
        ),
        (-350, 300),
    )

    convex_final = _process_mask(
        nodes,
        group,
        group_input,
        "Convex",
        convex_raw,
        "Convex Strength",
        (650, 1250),
    )

    concave_final = _process_mask(
        nodes,
        group,
        group_input,
        "Concave",
        concave_raw,
        "Concave Strength",
        (650, 250),
    )

    crevice_final = _process_mask(
        nodes,
        group,
        group_input,
        "Crevice",
        sources["ao_crevice"],
        "Crevice Strength",
        (650, -750),
    )

    # Signed-style output is generated from the independently processed masks.
    # Neutral regions remain at 0.5 when both masks are zero.
    signed_difference = _math(
        nodes,
        "Combined - Convex Minus Concave",
        "SUBTRACT",
        (3100, 500),
    )
    _link(group, convex_final, signed_difference.inputs[0])
    _link(group, concave_final, signed_difference.inputs[1])

    signed_half = _math(
        nodes,
        "Combined - Half Amplitude",
        "MULTIPLY",
        (3300, 500),
        value_b=0.5,
    )
    _link(group, signed_difference.outputs[0], signed_half.inputs[0])

    signed_neutral = _math(
        nodes,
        "Combined - Neutral Gray",
        "ADD",
        (3500, 500),
        value_b=0.5,
    )
    _link(group, signed_half.outputs[0], signed_neutral.inputs[0])

    combined_clamped = _clamp_0_1(
        nodes,
        group,
        "Combined - Clamp",
        signed_neutral.outputs[0],
        (3700, 500),
    )

    _link(group, convex_final, group_output.inputs["Convex"])
    _link(group, concave_final, group_output.inputs["Concave"])
    _link(group, combined_clamped, group_output.inputs["Combined"])
    _link(group, crevice_final, group_output.inputs["Crevice"])
    _link(group, sources["bevel_detail"], group_output.inputs["Bevel Detail"])
    _link(group, sources["pointiness_display"], group_output.inputs["Pointiness"])

    emission = _new_node(
        nodes,
        "ShaderNodeEmission",
        "Output - Combined Curvature Emission",
        (3950, 100),
    )
    emission.inputs["Strength"].default_value = 1.0
    _link(group, combined_clamped, emission.inputs["Color"])
    _link(group, emission.outputs["Emission"], group_output.inputs["Curvature Shader"])


def validate_node_group(group):
    """Validate required nodes, outputs, and critical internal connections.

    This is a structural validation. It verifies that the required outputs
    exist and that each output socket is linked. It does not render a scene
    or prove that Cycles produces a particular visual result.

    Args:
        group: Shader node group to validate.

    Returns:
        A list of human-readable validation errors. An empty list means
        structural validation passed.
    """
    errors = []

    if group is None:
        return ["Node group does not exist."]

    if group.bl_idname != "ShaderNodeTree":
        errors.append(
            f"Expected ShaderNodeTree, received '{group.bl_idname}'."
        )

    group_output = next(
        (node for node in group.nodes if node.bl_idname == "NodeGroupOutput"),
        None,
    )
    if group_output is None:
        return errors + ["NodeGroupOutput node is missing."]

    for output_name in REQUIRED_OUTPUTS + OPTIONAL_OUTPUTS:
        socket = group_output.inputs.get(output_name)
        if socket is None:
            errors.append(f"Group output socket '{output_name}' is missing.")
        elif not socket.is_linked:
            errors.append(f"Group output '{output_name}' is not connected.")

    required_nodes = (
        "ShaderNodeNewGeometry",
        "ShaderNodeBevel",
        "ShaderNodeAmbientOcclusion",
        "ShaderNodeEmission",
    )
    present_types = {node.bl_idname for node in group.nodes}

    for node_type in required_nodes:
        if node_type not in present_types:
            errors.append(f"Required source node '{node_type}' is missing.")

    # Verify the critical source connections, not just the final outputs.
    critical_connections = (
        ("Source - Geometry", "Pointiness", True),
        ("Source - Bevel Normal Variation", "Radius", False),
        ("Source - Ambient Occlusion", "Distance", False),
    )
    for node_name, socket_name, is_output in critical_connections:
        node = group.nodes.get(node_name)
        if node is None:
            errors.append(f"Critical node '{node_name}' is missing.")
            continue
        try:
            socket = _socket(node, socket_name, is_output=is_output)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        if is_output and not socket.is_linked:
            errors.append(
                f"Critical output '{node_name}.{socket_name}' is not connected."
            )
        elif not is_output and not socket.is_linked:
            errors.append(
                f"Critical input '{node_name}.{socket_name}' is not connected."
            )

    bevel_dot = group.nodes.get("Bevel - Original Versus Bevel Normal")
    if bevel_dot is not None:
        # Vector Math inputs can share the display name "Vector".
        # Validate them by index rather than relying on duplicate socket names.
        for socket_index in (0, 1):
            if len(bevel_dot.inputs) <= socket_index or not bevel_dot.inputs[socket_index].is_linked:
                errors.append(
                    f"Bevel normal comparison input {socket_index} is not connected."
                )

    ao_node = group.nodes.get("Source - Ambient Occlusion")
    if ao_node is not None and ao_node.outputs.get("AO") is None:
        errors.append("Ambient Occlusion node does not expose the 'AO' output.")

    return errors


def create_node_group():
    """Create or rebuild the Curvature Map shader node group.

    If a group named 'Curvature Map' already exists, its node contents and
    interface are rebuilt in place. Existing materials that reference the
    group therefore continue to reference the same datablock.

    Returns:
        The rebuilt Blender ShaderNodeTree.

    Raises:
        RuntimeError: If node creation, socket linking, or validation fails.
    """
    group = bpy.data.node_groups.get(GROUP_NAME)

    if group is None:
        group = bpy.data.node_groups.new(
            name=GROUP_NAME,
            type="ShaderNodeTree",
        )
    else:
        if group.bl_idname != "ShaderNodeTree":
            raise RuntimeError(
                f"An existing datablock named '{GROUP_NAME}' is not a "
                "ShaderNodeTree. Rename or remove that datablock first."
            )
        group.nodes.clear()
        group.interface.clear()

    group.description = GROUP_DESCRIPTION
    _create_interface(group)

    nodes = group.nodes
    group_input = _new_node(
        nodes,
        "NodeGroupInput",
        "Curvature Controls",
        (-2200, 300),
    )
    group_output = _new_node(
        nodes,
        "NodeGroupOutput",
        "Curvature Outputs",
        (4300, 300),
    )
    group_output.is_active_output = True

    sources = _create_source_nodes(group, nodes, group_input)
    _create_processing_and_outputs(
        group,
        nodes,
        group_input,
        sources,
        group_output,
    )

    for node in nodes:
        node.width = 210

    errors = validate_node_group(group)
    if errors:
        raise RuntimeError(
            "Curvature Map validation failed:\n- " + "\n- ".join(errors)
        )

    return group


if __name__ == "__main__":
    curvature_group = create_node_group()
    print(
        f"[Sequenced Bake] '{curvature_group.name}' created successfully. "
        f"Nodes: {len(curvature_group.nodes)}"
    )
    print("[Sequenced Bake] Structural node validation passed.")
