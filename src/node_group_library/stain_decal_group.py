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

GROUP_NAME = "Stain Decal"


def new_node(nodes, node_type, name, location):
    """Create and position a named shader node."""
    node = nodes.new(node_type)
    node.name = name
    node.label = name
    node.location = location
    return node


def set_socket(node, name, value):
    """Set a node input by name and report incompatible Blender APIs."""
    socket = node.inputs.get(name)
    if socket is None:
        raise RuntimeError(f"Node '{node.name}' has no input '{name}'.")
    socket.default_value = value


def link(tree, output_socket, input_socket):
    """Connect two node sockets."""
    tree.links.new(output_socket, input_socket)


def math_node(nodes, name, operation, location):
    """Create a configured ShaderNodeMath node."""
    node = new_node(nodes, "ShaderNodeMath", name, location)
    node.operation = operation
    return node


def vector_node(nodes, name, operation, location):
    """Create a configured ShaderNodeVectorMath node."""
    node = new_node(nodes, "ShaderNodeVectorMath", name, location)
    node.operation = operation
    return node


def float_input(group, name, default, minimum, maximum, description=""):
    """Add a bounded float input to the group interface."""
    socket = group.interface.new_socket(
        name=name, in_out="INPUT", socket_type="NodeSocketFloat"
    )
    socket.default_value = default
    socket.min_value = minimum
    socket.max_value = maximum
    if description:
        socket.description = description
    return socket


def color_input(group, name, default, description=""):
    """Add a color input to the group interface."""
    socket = group.interface.new_socket(
        name=name, in_out="INPUT", socket_type="NodeSocketColor"
    )
    socket.default_value = default
    if description:
        socket.description = description
    return socket


def output_socket(group, name, socket_type):
    """Add an output to the group interface."""
    return group.interface.new_socket(
        name=name, in_out="OUTPUT", socket_type=socket_type
    )


def create_group_interface(group):
    """Expose placement, runoff morphology, drips, boundary, and surface response."""
    float_input(group, "Position X", 0.0, -1.0, 1.0)
    float_input(group, "Position Y", 0.0, -1.0, 1.0)
    float_input(group, "Rotation", 0.0, -180.0, 180.0)

    float_input(group, "Streak Density", 8.0, 1.0, 40.0)
    float_input(group, "Streak Length", 0.22, 0.03, 1.0)
    float_input(group, "Streak Width", 0.28, 0.03, 1.0)
    float_input(group, "Flow Distortion", 0.32, 0.0, 1.0)
    float_input(group, "Streak Variation", 0.55, 0.0, 1.0)
    
    float_input(group, "Runoff Field Scale", 1.0, 0.0, 100.0)
    float_input(group, "Runoff Field Distortion", 0.0, 0.0, 10.0)
    float_input(group, "Runoff Threshold 1", 0.72, 0.0, 1.0)
    float_input(group, "Runoff Threshold 2", 0.5, 0.0, 1.0)

    float_input(group, "Drip Strength", 0.7, 0.0, 1.0)
    float_input(group, "Number of Drips", 15.0, 1.0, 100.0)
    float_input(group, "Drip Length Variation", 0.5, 0.0, 1.0)
    float_input(group, "Drip Width Variation", 0.3, 0.0, 1.0)
    float_input(group, "Drip Distortion", 1.2, 0.0, 10.0)

    float_input(group, "Mineral Density", 0.62, 0.0, 1.0)
    float_input(group, "Deposit Grain", 0.65, 0.0, 1.0)
    float_input(group, "Mineral Grain W", 0.0, -1000.0, 1000.0)
    float_input(group, "Mineral Grain Scale", 42.0, 0.0, 1000.0)
    float_input(group, "Mineral Grain Distortion", 0.0, 0.0, 10.0)
    
    color_input(group, "Stain Color", (0.34, 0.30, 0.22, 1.0))
    color_input(group, "Mineral Color", (0.78, 0.75, 0.66, 1.0))
    float_input(group, "Roughness", 0.82, 0.0, 1.0)
    float_input(group, "Mineral Roughness", 0.94, 0.0, 1.0)
    float_input(group, "Normal Strength", 0.35, 0.0, 1.0)
    float_input(group, "Normal Distance", 0.025, 0.0, 0.25)

    float_input(group, "Decal Radius", 0.45, 0.0, 1.0)
    float_input(group, "Edge Breakup", 0.15, 0.0, 1.0)
    float_input(group, "Edge Detail", 4.0, 0.0, 15.0)
    float_input(group, "Edge Erosion", 0.3, 0.0, 1.0)
    float_input(group, "Decal Fade", 0.12, 0.0, 0.5)
    
    float_input(group, "Opacity", 0.85, 0.0, 1.0)

    output_socket(group, "Shader", "NodeSocketShader")
    output_socket(group, "Stain Mask", "NodeSocketFloat")
    output_socket(group, "Mineral Mask", "NodeSocketFloat")


def create_node_group():
    """Build and return the Stain Decal shader node group."""
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is None:
        group = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
    else:
        group.nodes.clear()
        group.interface.clear()

    group.description = "Procedural vertical mineral runoff with independent drips and broken decal bounds."
    create_group_interface(group)

    nodes = group.nodes
    inputs = new_node(nodes, "NodeGroupInput", "Stain Controls", (-2000, 0))
    outputs = new_node(nodes, "NodeGroupOutput", "Stain Outputs", (3000, 0))
    outputs.is_active_output = True

    texcoord = new_node(nodes, "ShaderNodeTexCoord", "UV Coordinates", (-1800, -500))
    separate = new_node(nodes, "ShaderNodeSeparateXYZ", "Separate UV", (-1600, -500))
    link(group, texcoord.outputs["UV"], separate.inputs["Vector"])

    px = math_node(nodes, "Math", "SUBTRACT", (-1400, -400))
    py = math_node(nodes, "Math", "SUBTRACT", (-1400, -550))
    link(group, separate.outputs["X"], px.inputs[0])
    link(group, inputs.outputs["Position X"], px.inputs[1])
    link(group, separate.outputs["Y"], py.inputs[0])
    link(group, inputs.outputs["Position Y"], py.inputs[1])

    cx = math_node(nodes, "Center X", "SUBTRACT", (-1200, -400))
    cy = math_node(nodes, "Center Y", "SUBTRACT", (-1200, -550))
    cx.inputs[1].default_value = 0.5
    cy.inputs[1].default_value = 0.5
    link(group, px.outputs[0], cx.inputs[0])
    link(group, py.outputs[0], cy.inputs[0])

    radians = math_node(nodes, "Degrees To Radians", "MULTIPLY", (-1400, -150))
    radians.inputs[1].default_value = math.pi / 180.0
    link(group, inputs.outputs["Rotation"], radians.inputs[0])
    cosine = math_node(nodes, "Rotation Cosine", "COSINE", (-1200, -100))
    sine = math_node(nodes, "Rotation Sine", "SINE", (-1200, -230))
    link(group, radians.outputs[0], cosine.inputs[0])
    link(group, radians.outputs[0], sine.inputs[0])

    xcos = math_node(nodes, "X Cosine", "MULTIPLY", (-1000, -300))
    ysin = math_node(nodes, "Y Sine", "MULTIPLY", (-1000, -430))
    xsin = math_node(nodes, "X Sine", "MULTIPLY", (-1000, -560))
    ycos = math_node(nodes, "Y Cosine", "MULTIPLY", (-1000, -690))
    for node, a, b in ((xcos, cx.outputs[0], cosine.outputs[0]), (ysin, cy.outputs[0], sine.outputs[0]), (xsin, cx.outputs[0], sine.outputs[0]), (ycos, cy.outputs[0], cosine.outputs[0])):
        link(group, a, node.inputs[0])
        link(group, b, node.inputs[1])

    rx = math_node(nodes, "Rotated X", "SUBTRACT", (-800, -350))
    ry = math_node(nodes, "Rotated Y", "ADD", (-800, -550))
    link(group, xcos.outputs[0], rx.inputs[0])
    link(group, ysin.outputs[0], rx.inputs[1])
    link(group, xsin.outputs[0], ry.inputs[0])
    link(group, ycos.outputs[0], ry.inputs[1])
    
    ux = math_node(nodes, "Restore UV X", "ADD", (-600, -350))
    uy = math_node(nodes, "Restore UV Y", "ADD", (-600, -550))
    ux.inputs[1].default_value = 0.5
    uy.inputs[1].default_value = 0.5
    link(group, rx.outputs[0], ux.inputs[0])
    link(group, ry.outputs[0], uy.inputs[0])
    uv = new_node(nodes, "ShaderNodeCombineXYZ", "Transformed UV", (-400, -450))
    link(group, ux.outputs[0], uv.inputs["X"])
    link(group, uy.outputs[0], uv.inputs["Y"])

    width_scale = math_node(nodes, "Horizontal Frequency", "MULTIPLY", (-200, -850))
    width_scale.inputs[1].default_value = 18.0
    link(group, inputs.outputs["Streak Density"], width_scale.inputs[0])
    width_factor = math_node(nodes, "Streak Width Factor", "DIVIDE", (-200, -1000))
    width_factor.inputs[0].default_value = 0.28
    link(group, inputs.outputs["Streak Width"], width_factor.inputs[1])
    adjusted_width = math_node(nodes, "Adjusted Streak Frequency", "MULTIPLY", (0, -700))
    link(group, width_scale.outputs[0], adjusted_width.inputs[0])
    link(group, width_factor.outputs[0], adjusted_width.inputs[1])
    length_inverse = math_node(nodes, "Vertical Stretch", "DIVIDE", (-200, -1150))
    length_inverse.inputs[0].default_value = 1.0
    link(group, inputs.outputs["Streak Length"], length_inverse.inputs[1])

    scaled_x = math_node(nodes, "Scale UV X", "MULTIPLY", (200, -800))
    scaled_y = math_node(nodes, "Scale UV Y", "MULTIPLY", (200, -950))
    link(group, ux.outputs[0], scaled_x.inputs[0])
    link(group, adjusted_width.outputs[0], scaled_x.inputs[1])
    link(group, uy.outputs[0], scaled_y.inputs[0])
    link(group, length_inverse.outputs[0], scaled_y.inputs[1])
    flow_uv = new_node(nodes, "ShaderNodeCombineXYZ", "Elongated Flow Coordinates", (400, -850))
    link(group, scaled_x.outputs[0], flow_uv.inputs["X"])
    link(group, scaled_y.outputs[0], flow_uv.inputs["Y"])

    warp = new_node(nodes, "ShaderNodeTexNoise", "Flow Distortion Noise", (200, -250))
    set_socket(warp, "Scale", 3.5)
    set_socket(warp, "Detail", 6.0)
    link(group, uv.outputs["Vector"], warp.inputs["Vector"])
    warp_center = vector_node(nodes, "Center Flow Noise", "SUBTRACT", (400, -250))
    warp_center.inputs[1].default_value = (0.5, 0.5, 0.5)
    link(group, warp.outputs["Color"], warp_center.inputs[0])
    warp_amount = vector_node(nodes, "Flow Warp Amount", "SCALE", (600, -250))
    link(group, warp_center.outputs["Vector"], warp_amount.inputs[0])
    link(group, inputs.outputs["Flow Distortion"], warp_amount.inputs[3])
    warped = vector_node(nodes, "Warped Flow Coordinates", "ADD", (800, -650))
    link(group, flow_uv.outputs["Vector"], warped.inputs[0])
    link(group, warp_amount.outputs["Vector"], warped.inputs[1])

    flow_noise = new_node(nodes, "ShaderNodeTexNoise", "Vertical Runoff Field", (1000, -650))
    link(group, warped.outputs["Vector"], flow_noise.inputs["Vector"])
    link(group, inputs.outputs["Runoff Field Scale"], flow_noise.inputs["Scale"])
    link(group, inputs.outputs["Runoff Field Distortion"], flow_noise.inputs["Distortion"])

    threshold = math_node(nodes, "Runoff Threshold", "SUBTRACT", (1200, -650))
    link(group, inputs.outputs["Runoff Threshold 1"], threshold.inputs[0])
    link(group, inputs.outputs["Runoff Threshold 2"], threshold.inputs[1])
    
    variation = math_node(nodes, "Variation Amount", "MULTIPLY", (800, -900))
    variation.inputs[1].default_value = 0.22
    link(group, inputs.outputs["Streak Variation"], variation.inputs[0])
    
    grain = new_node(nodes, "ShaderNodeTexNoise", "Mineral Grain", (600, -1100))
    grain.noise_dimensions = '4D'
    link(group, uv.outputs["Vector"], grain.inputs["Vector"])
    link(group, inputs.outputs["Mineral Grain W"], grain.inputs["W"])
    link(group, inputs.outputs["Mineral Grain Scale"], grain.inputs["Scale"])
    link(group, inputs.outputs["Mineral Grain Distortion"], grain.inputs["Distortion"])
    link(group, inputs.outputs["Deposit Grain"], grain.inputs["Roughness"])

    grain_center = math_node(nodes, "Center Grain", "ADD", (800, -1100))
    grain_center.inputs[1].default_value = 0.4
    link(group, grain.outputs["Fac"], grain_center.inputs[0])
    
    grain_variation = math_node(nodes, "Grain Edge Variation", "MULTIPLY", (1000, -1000))
    link(group, grain_center.outputs[0], grain_variation.inputs[0])
    link(group, variation.outputs[0], grain_variation.inputs[1])
    
    threshold_adjust = math_node(nodes, "Irregular Threshold", "ADD", (1200, -900))
    link(group, threshold.outputs[0], threshold_adjust.inputs[0])
    link(group, grain_variation.outputs[0], threshold_adjust.inputs[1])

    runoff_ramp = new_node(nodes, "ShaderNodeMapRange", "Runoff Mask", (1400, -650))
    runoff_ramp.clamp = True
    set_socket(runoff_ramp, "From Min", 0.0)
    set_socket(runoff_ramp, "From Max", 0.22)
    link(group, flow_noise.outputs["Fac"], runoff_ramp.inputs["Value"])
    link(group, threshold_adjust.outputs[0], runoff_ramp.inputs["From Min"])

    drip_uv_scale = vector_node(nodes, "Drip UV Scale", "MULTIPLY", (400, -1400))
    link(group, uv.outputs["Vector"], drip_uv_scale.inputs[0])
    link(group, inputs.outputs["Number of Drips"], drip_uv_scale.inputs[1])
    drip_uv_stretch = vector_node(nodes, "Drip UV Stretch", "MULTIPLY", (600, -1400))
    drip_uv_stretch.inputs[1].default_value = (1.0, 0.05, 1.0)
    link(group, drip_uv_scale.outputs[0], drip_uv_stretch.inputs[0])
    
    drip_voronoi = new_node(nodes, "ShaderNodeTexVoronoi", "Drip Generator", (800, -1400))
    drip_voronoi.feature = 'F1'
    drip_voronoi.distance = 'EUCLIDEAN'
    link(group, drip_uv_stretch.outputs[0], drip_voronoi.inputs["Vector"])
    link(group, inputs.outputs["Drip Length Variation"], drip_voronoi.inputs["Randomness"])

    drip_distort = math_node(nodes, "Drip Distortion Mix", "MULTIPLY", (1000, -1350))
    link(group, drip_voronoi.outputs["Distance"], drip_distort.inputs[0])
    link(group, inputs.outputs["Drip Distortion"], drip_distort.inputs[1])

    drip_ramp = new_node(nodes, "ShaderNodeMapRange", "Isolate Drips", (1200, -1400))
    drip_ramp.clamp = True
    set_socket(drip_ramp, "From Min", 0.1)
    set_socket(drip_ramp, "To Min", 1.0)
    set_socket(drip_ramp, "To Max", 0.0)
    link(group, drip_distort.outputs[0], drip_ramp.inputs["Value"])
    link(group, inputs.outputs["Drip Width Variation"], drip_ramp.inputs["From Max"])

    drip_strength_mix = math_node(nodes, "Drip Strength", "MULTIPLY", (1400, -1400))
    link(group, drip_ramp.outputs["Result"], drip_strength_mix.inputs[0])
    link(group, inputs.outputs["Drip Strength"], drip_strength_mix.inputs[1])

    combined_stain = math_node(nodes, "Combined Stain", "ADD", (1600, -850))
    combined_stain.use_clamp = True
    link(group, runoff_ramp.outputs["Result"], combined_stain.inputs[0])
    link(group, drip_strength_mix.outputs[0], combined_stain.inputs[1])

    mineral_threshold = math_node(nodes, "Mineral Threshold", "SUBTRACT", (1400, -1150))
    mineral_threshold.inputs[0].default_value = 0.58
    mineral_ramp = new_node(nodes, "ShaderNodeMapRange", "Mineral Deposit Mask", (1600, -1100))
    mineral_ramp.clamp = True
    set_socket(mineral_ramp, "From Max", 0.28)
    link(group, grain.outputs["Fac"], mineral_ramp.inputs["Value"])
    link(group, mineral_threshold.outputs[0], mineral_ramp.inputs["From Min"])

    mineral_density = math_node(nodes, "Mineral Density", "MULTIPLY", (1800, -1000))
    link(group, mineral_ramp.outputs["Result"], mineral_density.inputs[0])
    link(group, inputs.outputs["Mineral Density"], mineral_density.inputs[1])
    
    mineral_in_runoff = math_node(nodes, "Minerals Within Runoff", "MULTIPLY", (2000, -900))
    link(group, mineral_density.outputs[0], mineral_in_runoff.inputs[0])
    link(group, combined_stain.outputs[0], mineral_in_runoff.inputs[1])

    center = new_node(nodes, "ShaderNodeCombineXYZ", "UV Center", (0, 300))
    set_socket(center, "X", 0.5)
    set_socket(center, "Y", 0.5)
    
    distance = vector_node(nodes, "Distance", "DISTANCE", (200, 300))
    link(group, uv.outputs["Vector"], distance.inputs[0])
    link(group, center.outputs["Vector"], distance.inputs[1])

    edge_noise = new_node(nodes, "ShaderNodeTexNoise", "Edge Noise", (200, 100))
    set_socket(edge_noise, "Scale", 5.0)
    link(group, inputs.outputs["Edge Detail"], edge_noise.inputs["Detail"])
    link(group, uv.outputs["Vector"], edge_noise.inputs["Vector"])

    center_noise = math_node(nodes, "Center Noise", "SUBTRACT", (400, 100))
    center_noise.inputs[1].default_value = 0.5
    link(group, edge_noise.outputs["Fac"], center_noise.inputs[0])

    breakup_mult = math_node(nodes, "Breakup Scale", "MULTIPLY", (600, 100))
    link(group, center_noise.outputs[0], breakup_mult.inputs[0])
    link(group, inputs.outputs["Edge Breakup"], breakup_mult.inputs[1])

    broken_distance = math_node(nodes, "Broken Distance", "ADD", (800, 200))
    link(group, distance.outputs["Value"], broken_distance.inputs[0])
    link(group, breakup_mult.outputs[0], broken_distance.inputs[1])

    edge_map = new_node(nodes, "ShaderNodeMapRange", "Boundary Mask", (1200, 200))
    edge_map.clamp = True
    set_socket(edge_map, "To Min", 1.0)
    set_socket(edge_map, "To Max", 0.0)
    link(group, broken_distance.outputs[0], edge_map.inputs["Value"])
    
    radius_erosion = math_node(nodes, "Erosion Subtraction", "SUBTRACT", (800, 0))
    link(group, inputs.outputs["Decal Radius"], radius_erosion.inputs[0])
    link(group, inputs.outputs["Edge Erosion"], radius_erosion.inputs[1])
    
    radius_fade = math_node(nodes, "Fade Addition", "ADD", (1000, -100))
    link(group, radius_erosion.outputs[0], radius_fade.inputs[0])
    link(group, inputs.outputs["Decal Fade"], radius_fade.inputs[1])
    
    link(group, radius_erosion.outputs[0], edge_map.inputs["From Min"])
    link(group, radius_fade.outputs[0], edge_map.inputs["From Max"])

    stain_mask = math_node(nodes, "Stain Mask With Boundary", "MULTIPLY", (2200, -400))
    link(group, combined_stain.outputs[0], stain_mask.inputs[0])
    link(group, edge_map.outputs["Result"], stain_mask.inputs[1])
    
    mineral_mask = math_node(nodes, "Mineral Mask With Boundary", "MULTIPLY", (2200, -600))
    link(group, mineral_in_runoff.outputs[0], mineral_mask.inputs[0])
    link(group, edge_map.outputs["Result"], mineral_mask.inputs[1])

    stain_bsdf = new_node(nodes, "ShaderNodeBsdfPrincipled", "Runoff Film", (2400, 250))
    link(group, inputs.outputs["Stain Color"], stain_bsdf.inputs["Base Color"])
    link(group, inputs.outputs["Roughness"], stain_bsdf.inputs["Roughness"])
    
    mineral_bsdf = new_node(nodes, "ShaderNodeBsdfPrincipled", "Calcium / Lime Deposit", (2400, -100))
    link(group, inputs.outputs["Mineral Color"], mineral_bsdf.inputs["Base Color"])
    link(group, inputs.outputs["Mineral Roughness"], mineral_bsdf.inputs["Roughness"])

    height = math_node(nodes, "Relief Height", "ADD", (2200, -1000))
    link(group, stain_mask.outputs[0], height.inputs[0])
    link(group, mineral_mask.outputs[0], height.inputs[1])
    bump = new_node(nodes, "ShaderNodeBump", "Mineral Relief Normal", (2400, -500))
    link(group, height.outputs[0], bump.inputs["Height"])
    link(group, inputs.outputs["Normal Strength"], bump.inputs["Strength"])
    link(group, inputs.outputs["Normal Distance"], bump.inputs["Distance"])
    link(group, bump.outputs["Normal"], stain_bsdf.inputs["Normal"])
    link(group, bump.outputs["Normal"], mineral_bsdf.inputs["Normal"])

    mineral_mix = new_node(nodes, "ShaderNodeMixShader", "Film / Mineral Blend", (2600, 100))
    link(group, mineral_mask.outputs[0], mineral_mix.inputs[0])
    link(group, stain_bsdf.outputs["BSDF"], mineral_mix.inputs[1])
    link(group, mineral_bsdf.outputs["BSDF"], mineral_mix.inputs[2])

    opacity = math_node(nodes, "Apply Opacity", "MULTIPLY", (2400, -800))
    link(group, stain_mask.outputs[0], opacity.inputs[0])
    link(group, inputs.outputs["Opacity"], opacity.inputs[1])
    
    transparent = new_node(nodes, "ShaderNodeBsdfTransparent", "Transparent Surface", (2600, -250))
    final_mix = new_node(nodes, "ShaderNodeMixShader", "Decal Transparency", (2800, 0))
    link(group, opacity.outputs[0], final_mix.inputs[0])
    link(group, transparent.outputs["BSDF"], final_mix.inputs[1])
    link(group, mineral_mix.outputs["Shader"], final_mix.inputs[2])

    link(group, final_mix.outputs["Shader"], outputs.inputs["Shader"])
    link(group, stain_mask.outputs[0], outputs.inputs["Stain Mask"])
    link(group, mineral_mask.outputs[0], outputs.inputs["Mineral Mask"])

    for node in nodes:
        node.width = 190

    return group

if __name__ == "__main__":
    create_node_group()