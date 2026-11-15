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

GROUP_NAME = "Procedural Concrete"


def new_node(nodes, node_type, name, location):
    """Create and position a named shader node."""
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
    """Connect two node sockets."""
    tree.links.new(output_socket, input_socket)


def math_node(nodes, name, operation, location):
    """Create a ShaderNodeMath node."""
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
    """
    Construct the interface mimicking multi-scale 3D roughness quantification,
    fractal/multifractal characteristics of pavement macrotexture, and
    surface treatments like diamond grinding and tining.
    """
    # Placement Controls
    float_input(group, "Position X", 0.0, -100.0, 100.0, "X Offset")
    float_input(group, "Position Y", 0.0, -100.0, 100.0, "Y Offset")
    float_input(group, "Rotation", 0.0, -180.0, 180.0, "Global Rotation")
    float_input(group, "Scale", 1.0, 0.001, 100.0, "Global Scale")

    # Microtexture (Cement Paste / Asphalt Binder Matrix)
    float_input(group, "Microtexture Fractal Dimension", 16.0, 1.0, 32.0, "High-frequency roughness detail")
    float_input(group, "Microtexture Roughness", 0.85, 0.0, 1.0, "Paste/Binder surface roughness")
    float_input(group, "Microtexture Amplitude", 0.08, 0.0, 1.0, "Influence of fine paste grain on height")

    # Macrotexture (Aggregates)
    float_input(group, "Macrotexture Scale", 25.0, 1.0, 200.0, "Size of aggregate stones")
    float_input(group, "Aggregate Exposure", 0.45, 0.0, 1.0, "Wear level revealing aggregates through the binder")
    float_input(group, "Aggregate Distortion", 1.2, 0.0, 10.0, "Irregularity of aggregate shapes")
    float_input(group, "Volumetric Peak Flattening", 0.6, 0.0, 1.0, "Simulates tire-polishing on macrotexture peaks")

    # Surface Treatment (Tining / Diamond Grinding)
    float_input(group, "Grooving Strength", 0.15, 0.0, 1.0, "Depth of longitudinal/transverse cuts")
    float_input(group, "Grooving Spacing", 85.0, 1.0, 500.0, "Frequency of diamond grinding or tining")
    float_input(group, "Grooving Angle", 0.0, -90.0, 90.0, "0 for longitudinal, 90 for transverse")
    float_input(group, "Grooving Wear", 0.3, 0.0, 1.0, "Erosion of grooving in wheel paths")
    float_input(group, "Grooving Distortion", 0.0, 0.0, 100.0, "Distortion of the bands")
    float_input(group, "Grooving Detail", 2.0, 0.0, 15.0, "Detail level of the band distortion")
    float_input(group, "Grooving Detail Scale", 1.0, 0.0, 100.0, "Scale of the distortion detail")
    float_input(group, "Grooving Phase Offset", 0.0, -100.0, 100.0, "Phase offset of the bands")

    # Pitting / Defect Distribution
    float_input(group, "Void Density", 12.0, 1.0, 50.0, "Density of surface pitting and air voids")
    float_input(group, "Void Depth", 0.4, 0.0, 2.0, "Severity of local pitting")

    # Material Properties
    color_input(group, "Base Binder Color", (0.22, 0.22, 0.21, 1.0), "Color of cement paste or asphalt binder")
    color_input(group, "Aggregate Color", (0.35, 0.34, 0.32, 1.0), "Color of exposed stone aggregates")
    float_input(group, "Surface Specularity", 0.15, 0.0, 1.0, "Base specularity for dry concrete")
    
    # Required Normals & Height Outputs
    float_input(group, "Normal Strength", 0.8, 0.0, 5.0, "Overall normal map intensity")
    float_input(group, "Normal Distance", 0.02, 0.0, 1.0, "Ray distance for bump evaluation")

    output_socket(group, "Shader", "NodeSocketShader")
    output_socket(group, "Surface Height", "NodeSocketFloat")
    output_socket(group, "Aggregate Mask", "NodeSocketFloat")
    output_socket(group, "Surface Normal", "NodeSocketVector")


def create_node_group():
    """Build and return the procedural concrete/asphalt shader node group."""
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is None:
        group = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
    else:
        group.nodes.clear()
        group.interface.clear()

    group.description = (
        "Volumetric multi-scale concrete and asphalt shader implementing macrotexture aggregates, "
        "microtexture binder matrix, pitting voids, and diamond grinding/tining surface treatments."
    )

    create_group_interface(group)

    nodes = group.nodes

    group_input = new_node(nodes, "NodeGroupInput", "Concrete Controls", (-2500, 0))
    group_output = new_node(nodes, "NodeGroupOutput", "Concrete Output", (2500, 0))
    group_output.is_active_output = True

    texcoord = new_node(nodes, "ShaderNodeTexCoord", "Global Coordinates", (-2500, -300))
    mapping = new_node(nodes, "ShaderNodeMapping", "Transform Matrix", (-2200, -300))
    
    position = new_node(nodes, "ShaderNodeCombineXYZ", "Position Vector", (-2500, -450))
    link(group, group_input.outputs["Position X"], position.inputs["X"])
    link(group, group_input.outputs["Position Y"], position.inputs["Y"])
    
    rotation = new_node(nodes, "ShaderNodeCombineXYZ", "Rotation Vector", (-2500, -600))
    rad_conv = math_node(nodes, "Deg to Rad", "MULTIPLY", (-2700, -600))
    set_socket(rad_conv, "Value_001", math.pi / 180.0)
    link(group, group_input.outputs["Rotation"], rad_conv.inputs["Value"])
    link(group, rad_conv.outputs["Value"], rotation.inputs["Z"])

    scale = new_node(nodes, "ShaderNodeCombineXYZ", "Scale Vector", (-2500, -750))
    link(group, group_input.outputs["Scale"], scale.inputs["X"])
    link(group, group_input.outputs["Scale"], scale.inputs["Y"])
    link(group, group_input.outputs["Scale"], scale.inputs["Z"])

    link(group, texcoord.outputs["Object"], mapping.inputs["Vector"])
    link(group, position.outputs["Vector"], mapping.inputs["Location"])
    link(group, rotation.outputs["Vector"], mapping.inputs["Rotation"])
    link(group, scale.outputs["Vector"], mapping.inputs["Scale"])

    micro_noise = new_node(nodes, "ShaderNodeTexNoise", "Microtexture Matrix", (-1800, 200))
    set_socket(micro_noise, "Scale", 150.0)
    link(group, mapping.outputs["Vector"], micro_noise.inputs["Vector"])
    link(group, group_input.outputs["Microtexture Fractal Dimension"], micro_noise.inputs["Detail"])
    link(group, group_input.outputs["Microtexture Roughness"], micro_noise.inputs["Roughness"])

    micro_height = math_node(nodes, "Micro Height Influence", "MULTIPLY", (-1500, 200))
    link(group, micro_noise.outputs["Fac"], micro_height.inputs["Value"])
    link(group, group_input.outputs["Microtexture Amplitude"], micro_height.inputs["Value_001"])

    agg_distort = new_node(nodes, "ShaderNodeTexNoise", "Aggregate Distortion Field", (-1800, -100))
    set_socket(agg_distort, "Scale", 15.0)
    set_socket(agg_distort, "Detail", 4.0)
    link(group, mapping.outputs["Vector"], agg_distort.inputs["Vector"])

    distort_mix = new_node(nodes, "ShaderNodeMix", "Apply Distortion", (-1500, -100))
    distort_mix.data_type = 'VECTOR'
    distort_mix.clamp_factor = False
    link(group, group_input.outputs["Aggregate Distortion"], distort_mix.inputs["Factor"])
    link(group, mapping.outputs["Vector"], distort_mix.inputs[4]) # A
    link(group, agg_distort.outputs["Color"], distort_mix.inputs[5]) # B

    agg_voronoi = new_node(nodes, "ShaderNodeTexVoronoi", "Aggregate Cell Structure", (-1200, -100))
    agg_voronoi.feature = 'F1'
    agg_voronoi.distance = 'EUCLIDEAN'
    link(group, distort_mix.outputs[1], agg_voronoi.inputs["Vector"])
    link(group, group_input.outputs["Macrotexture Scale"], agg_voronoi.inputs["Scale"])

    agg_polish = new_node(nodes, "ShaderNodeMapRange", "Peak Flattening Curve", (-900, -100))
    agg_polish.clamp = True
    set_socket(agg_polish, "From Min", 0.0)
    set_socket(agg_polish, "To Min", 1.0)
    set_socket(agg_polish, "To Max", 0.0) # Invert distance for height (center is highest)
    link(group, agg_voronoi.outputs["Distance"], agg_polish.inputs["Value"])
    
    flatten_math = math_node(nodes, "Apply Polishing", "SUBTRACT", (-1200, -350))
    set_socket(flatten_math, "Value", 1.0)
    link(group, group_input.outputs["Volumetric Peak Flattening"], flatten_math.inputs["Value_001"])
    link(group, flatten_math.outputs["Value"], agg_polish.inputs["From Max"])

    agg_exposure_mix = math_node(nodes, "Aggregate Exposure Multiplier", "MULTIPLY", (-600, -100))
    link(group, agg_polish.outputs["Result"], agg_exposure_mix.inputs["Value"])
    link(group, group_input.outputs["Aggregate Exposure"], agg_exposure_mix.inputs["Value_001"])

    agg_mask = new_node(nodes, "ShaderNodeMapRange", "Aggregate Color Mask", (-600, -300))
    agg_mask.clamp = True
    set_socket(agg_mask, "From Min", 0.1)
    set_socket(agg_mask, "From Max", 0.4)
    link(group, agg_exposure_mix.outputs["Value"], agg_mask.inputs["Value"])

    tining_rot = new_node(nodes, "ShaderNodeMapping", "Tining Rotation", (-1800, -600))
    tining_rad = math_node(nodes, "Angle to Rad", "MULTIPLY", (-2000, -750))
    set_socket(tining_rad, "Value_001", math.pi / 180.0)
    link(group, group_input.outputs["Grooving Angle"], tining_rad.inputs["Value"])
    link(group, tining_rad.outputs["Value"], tining_rot.inputs["Rotation"]) 
    link(group, mapping.outputs["Vector"], tining_rot.inputs["Vector"])

    tining_wave = new_node(nodes, "ShaderNodeTexWave", "Diamond Grinding Bands", (-1500, -600))
    tining_wave.wave_type = 'BANDS'
    tining_wave.wave_profile = 'SIN'
    link(group, tining_rot.outputs["Vector"], tining_wave.inputs["Vector"])
    link(group, group_input.outputs["Grooving Spacing"], tining_wave.inputs["Scale"])
    link(group, group_input.outputs["Grooving Distortion"], tining_wave.inputs["Distortion"])
    link(group, group_input.outputs["Grooving Detail"], tining_wave.inputs["Detail"])
    link(group, group_input.outputs["Grooving Detail Scale"], tining_wave.inputs["Detail Scale"])
    link(group, group_input.outputs["Grooving Phase Offset"], tining_wave.inputs["Phase Offset"])

    tining_wear_noise = new_node(nodes, "ShaderNodeTexNoise", "Grooving Wear Field", (-1500, -800))
    set_socket(tining_wear_noise, "Scale", 2.0)
    link(group, mapping.outputs["Vector"], tining_wear_noise.inputs["Vector"])

    wear_amount = math_node(nodes, "Wear Amount", "MULTIPLY", (-1300, -800))
    link(group, tining_wear_noise.outputs["Fac"], wear_amount.inputs["Value"])
    link(group, group_input.outputs["Grooving Wear"], wear_amount.inputs["Value_001"])

    tining_mask = math_node(nodes, "Apply Grooving Wear", "SUBTRACT", (-1100, -650))
    link(group, tining_wave.outputs["Color"], tining_mask.inputs["Value"])
    link(group, wear_amount.outputs["Value"], tining_mask.inputs["Value_001"])

    tining_mult = math_node(nodes, "Grooving Strength Mix", "MULTIPLY", (-900, -600))
    link(group, tining_mask.outputs["Value"], tining_mult.inputs["Value"])
    link(group, group_input.outputs["Grooving Strength"], tining_mult.inputs["Value_001"])
    
    # Invert grooving (cuts go down)
    tining_depth = math_node(nodes, "Negative Grooving", "MULTIPLY", (-700, -600))
    set_socket(tining_depth, "Value_001", -1.0)
    link(group, tining_mult.outputs["Value"], tining_depth.inputs["Value"])

    void_noise = new_node(nodes, "ShaderNodeTexNoise", "Void Distribution", (-1500, -1000))
    set_socket(void_noise, "Detail", 12.0)
    set_socket(void_noise, "Roughness", 0.9)
    link(group, mapping.outputs["Vector"], void_noise.inputs["Vector"])
    link(group, group_input.outputs["Void Density"], void_noise.inputs["Scale"])

    void_ramp = new_node(nodes, "ShaderNodeMapRange", "Isolate Pits", (-1200, -1000))
    void_ramp.clamp = True
    set_socket(void_ramp, "From Min", 0.65)
    set_socket(void_ramp, "From Max", 0.85)
    set_socket(void_ramp, "To Min", 0.0)
    set_socket(void_ramp, "To Max", 1.0)
    link(group, void_noise.outputs["Fac"], void_ramp.inputs["Value"])

    void_depth_mult = math_node(nodes, "Apply Void Depth", "MULTIPLY", (-900, -1000))
    link(group, void_ramp.outputs["Result"], void_depth_mult.inputs["Value"])
    link(group, group_input.outputs["Void Depth"], void_depth_mult.inputs["Value_001"])

    # Invert voids (pits go down)
    void_final = math_node(nodes, "Negative Voids", "MULTIPLY", (-700, -1000))
    set_socket(void_final, "Value_001", -1.0)
    link(group, void_depth_mult.outputs["Value"], void_final.inputs["Value"])

    comp_base = math_node(nodes, "Combine Micro/Macro", "ADD", (-300, -200))
    link(group, micro_height.outputs["Value"], comp_base.inputs["Value"])
    link(group, agg_exposure_mix.outputs["Value"], comp_base.inputs["Value_001"])

    comp_tine = math_node(nodes, "Subtract Grooving", "ADD", (-100, -350))
    link(group, comp_base.outputs["Value"], comp_tine.inputs["Value"])
    link(group, tining_depth.outputs["Value"], comp_tine.inputs["Value_001"])

    final_height = math_node(nodes, "Subtract Voids (Final Height)", "ADD", (100, -500))
    link(group, comp_tine.outputs["Value"], final_height.inputs["Value"])
    link(group, void_final.outputs["Value"], final_height.inputs["Value_001"])

    base_color_mix = new_node(nodes, "ShaderNodeMixRGB", "Aggregate/Binder Blend", (500, 200))
    base_color_mix.blend_type = 'MIX'
    link(group, agg_mask.outputs["Result"], base_color_mix.inputs["Fac"])
    link(group, group_input.outputs["Base Binder Color"], base_color_mix.inputs["Color1"])
    link(group, group_input.outputs["Aggregate Color"], base_color_mix.inputs["Color2"])

    # Add slight noise variation to base color
    color_var_noise = new_node(nodes, "ShaderNodeTexNoise", "Color Variation", (200, 400))
    set_socket(color_var_noise, "Scale", 5.0)
    link(group, mapping.outputs["Vector"], color_var_noise.inputs["Vector"])
    
    final_color_mix = new_node(nodes, "ShaderNodeMixRGB", "Apply Color Variation", (800, 200))
    final_color_mix.blend_type = 'MULTIPLY'
    set_socket(final_color_mix, "Fac", 0.25)
    link(group, base_color_mix.outputs["Color"], final_color_mix.inputs["Color1"])
    link(group, color_var_noise.outputs["Color"], final_color_mix.inputs["Color2"])

    # Dynamic Roughness based on pitting and aggregates
    rough_mix = math_node(nodes, "Dynamic Roughness Map", "ADD", (800, 0))
    link(group, final_height.outputs["Value"], rough_mix.inputs["Value"])
    set_socket(rough_mix, "Value_001", 0.6) # Base roughness offset

    bump = new_node(nodes, "ShaderNodeBump", "Surface Displacement Normal", (800, -400))
    link(group, final_height.outputs["Value"], bump.inputs["Height"])
    link(group, group_input.outputs["Normal Strength"], bump.inputs["Strength"])
    link(group, group_input.outputs["Normal Distance"], bump.inputs["Distance"])

    principled = new_node(nodes, "ShaderNodeBsdfPrincipled", "Concrete Surface", (1300, -100))
    link(group, final_color_mix.outputs["Color"], principled.inputs["Base Color"])
    link(group, rough_mix.outputs["Value"], principled.inputs["Roughness"])
    link(group, group_input.outputs["Surface Specularity"], principled.inputs["Specular IOR Level"])
    link(group, bump.outputs["Normal"], principled.inputs["Normal"])

    link(group, principled.outputs["BSDF"], group_output.inputs["Shader"])
    link(group, final_height.outputs["Value"], group_output.inputs["Surface Height"])
    link(group, agg_mask.outputs["Result"], group_output.inputs["Aggregate Mask"])
    link(group, bump.outputs["Normal"], group_output.inputs["Surface Normal"])

    for node in nodes:
        node.width = 220

    return group

if __name__ == "__main__":
    create_node_group()