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

GROUP_NAME = "Procedural Magma"
TAU = math.tau

# Solid things (crust, plates, stones) change this much slower than the melt.
SOLID_EVOLUTION = 0.4

DEBRIS = (
    # label,          amount, scale, size, clustering, phase offset
    ("Crystal",       0.20,  18.0,  0.22,  0.35,       0.12),
    ("Rock",          0.12,   7.0,  0.45,  0.35,       0.20),
    ("Scoria",        0.15,  12.0,  0.32,  0.35,       0.18),
    ("Crust Debris",  0.10,   5.0,  0.50,  0.35,       0.24),
)

OUTPUTS = (
    ("Shader", "NodeSocketShader"),
    ("Flow Mask", "NodeSocketFloat"),
    ("Debris Mask", "NodeSocketFloat"),
    ("Emission Mask", "NodeSocketFloat"),
    ("Rock Mask", "NodeSocketFloat"),
    ("Height", "NodeSocketFloat"),
    ("Surface Normal", "NodeSocketVector"),
    ("Displacement", "NodeSocketVector"),
)


def _socket(sockets, name):
    """Return a socket by identifier or name, never a hidden duplicate.

    Several nodes carry many sockets with the same name (the Mix node has
    four called "A"; Math has three called "Value").  Only one of each is
    active for the node's current mode, so:
      1. an exact identifier wins ("Value_001", "A_Color", "Fac"),
      2. otherwise the *enabled* socket with that name,
      3. otherwise any socket with that name.
    """
    for candidate in sockets:
        if candidate.identifier == name:
            return candidate
    named = [s for s in sockets if s.name == name]
    for candidate in named:
        if candidate.enabled:
            return candidate
    if named:
        return named[0]
    raise KeyError(
        f"Socket '{name}' not found. Available: "
        f"{[(s.name, s.identifier) for s in sockets]}"
    )


def _is_source(spec):
    """True when spec is a (node, output name) pair rather than a constant."""
    return (
        isinstance(spec, tuple) and len(spec) == 2
        and isinstance(spec[0], bpy.types.Node)
    )


class _Builder:
    """Small helper that creates nodes and wires them by socket name.

    Every method that makes a value returns a (node, output name) pair, which
    can be passed straight in as an operand of the next node.
    """

    def __init__(self, tree):
        self.tree = tree

    def node(self, node_type, name):
        node = self.tree.nodes.new(node_type)
        node.name = name
        node.label = name
        return node

    def feed(self, node, input_name, spec):
        """Link a source into an input, or set the input's constant value."""
        socket = _socket(node.inputs, input_name)
        if not socket.enabled:
            raise RuntimeError(
                f"{node.name}: input '{input_name}' is not active for this "
                f"node's current mode."
            )
        if _is_source(spec):
            source = _socket(spec[0].outputs, spec[1])
            if not source.enabled:
                raise RuntimeError(
                    f"{spec[0].name}: output '{spec[1]}' is not active for "
                    f"this node's current mode."
                )
            self.tree.links.new(source, socket)
        else:
            socket.default_value = spec

    def math(self, name, operation, *operands, clamp=False):
        node = self.node("ShaderNodeMath", name)
        node.operation = operation
        node.use_clamp = clamp
        for index, operand in enumerate(operands):
            identifier = "Value" if index == 0 else f"Value_{index:03d}"
            self.feed(node, identifier, operand)
        return (node, "Value")

    def smoothstep(self, name, value, edge_low, edge_high, invert=False):
        """0 below edge_low, 1 above edge_high, smooth between (or inverse)."""
        node = self.node("ShaderNodeMapRange", name)
        node.data_type = "FLOAT"
        node.interpolation_type = "SMOOTHSTEP"
        self.feed(node, "Value", value)
        self.feed(node, "From Min", edge_low)
        self.feed(node, "From Max", edge_high)
        self.feed(node, "To Min", 1.0 if invert else 0.0)
        self.feed(node, "To Max", 0.0 if invert else 1.0)
        return (node, "Result")

    def mix(self, name, data_type, factor, a, b):
        """Mix node.  data_type is set first so the right sockets are live."""
        node = self.node("ShaderNodeMix", name)
        node.data_type = data_type
        if data_type == "RGBA":
            node.blend_type = "MIX"
            node.clamp_result = False
        node.clamp_factor = True
        suffix = {"RGBA": "Color", "FLOAT": "Float"}[data_type]
        self.feed(node, "Factor_Float", factor)
        self.feed(node, f"A_{suffix}", a)
        self.feed(node, f"B_{suffix}", b)
        return (node, f"Result_{suffix}")

    def combine(self, name, x=0.0, y=0.0, z=0.0):
        node = self.node("ShaderNodeCombineXYZ", name)
        self.feed(node, "X", x)
        self.feed(node, "Y", y)
        self.feed(node, "Z", z)
        return (node, "Vector")

    def noise(self, name, coords, scale, detail, roughness):
        """4D noise sampled on looping coordinates."""
        vector, w = coords
        node = self.node("ShaderNodeTexNoise", name)
        node.noise_dimensions = "4D"
        self.feed(node, "Vector", vector)
        self.feed(node, "W", w)
        self.feed(node, "Scale", scale)
        self.feed(node, "Detail", detail)
        self.feed(node, "Roughness", roughness)
        return (node, "Fac")

    def voronoi(self, name, coords, scale, feature):
        vector, w = coords
        node = self.node("ShaderNodeTexVoronoi", name)
        node.voronoi_dimensions = "4D"
        node.feature = feature
        node.distance = "EUCLIDEAN"
        self.feed(node, "Vector", vector)
        self.feed(node, "W", w)
        self.feed(node, "Scale", scale)
        return node


def _interface(group, name, in_out, socket_type, default=None,
               minimum=None, maximum=None, description="", subtype=None):
    """Create and configure one node-group interface socket."""
    socket = group.interface.new_socket(
        name=name, in_out=in_out, socket_type=socket_type
    )
    if subtype is not None:
        try:
            socket.subtype = subtype
        except (TypeError, AttributeError):
            pass
    if default is not None and hasattr(socket, "default_value"):
        socket.default_value = default
    if minimum is not None and hasattr(socket, "min_value"):
        socket.min_value = minimum
    if maximum is not None and hasattr(socket, "max_value"):
        socket.max_value = maximum
    if description:
        socket.description = description
    return socket


def _add_float(group, name, default, minimum, maximum, description="",
               subtype=None):
    return _interface(group, name, "INPUT", "NodeSocketFloat",
                      default, minimum, maximum, description, subtype)


def _add_color(group, name, default, description=""):
    return _interface(group, name, "INPUT", "NodeSocketColor",
                      default, description=description)


def create_group_interface(group):
    """Build all controls and outputs exposed by Procedural Magma."""
    group.interface.clear()

    # Placement.
    _add_float(group, "Position X", 0.0, -100.0, 100.0)
    _add_float(group, "Position Y", 0.0, -100.0, 100.0)
    _add_float(group, "Rotation", 0.0, -TAU, TAU,
               "Turns the whole pattern.", "ANGLE")
    _add_float(group, "Flow Stretch", 2.0, 0.05, 20.0,
               "How far the pattern is drawn out along the flow.")
    _add_float(group, "Flow Direction", 0.0, -TAU, TAU,
               "Added to Rotation; the channels run along this heading.",
               "ANGLE")

    # Animation.
    _add_float(group, "Flow Phase", 0.0, -1000.0, 1000.0,
               "Animate by exactly one whole number over one loop.")
    _add_float(group, "Flow Speed", 1.0, -20.0, 20.0,
               "Keep this a whole number for a seamless loop. "
               "Negative reverses the flow.")
    _add_float(group, "Evolution", 0.25, 0.0, 5.0,
               "How much the pattern changes over one loop. "
               "Low is thick and slow, high is boiling.")

    # Molten flow.
    _add_float(group, "Flow Scale", 2.0, 0.01, 100.0)
    _add_float(group, "Flow Distortion", 0.35, 0.0, 5.0,
               "How much the channels wander.")
    _add_float(group, "Flow Detail", 5.0, 0.0, 15.0)
    _add_float(group, "Flow Fold Scale", 5.0, 0.01, 100.0,
               "Size of the ropy folds across the flow.")
    _add_float(group, "Flow Fold Strength", 0.35, 0.0, 2.0)
    _add_float(group, "Flow Width", 0.55, 0.01, 1.0,
               "Width of the hot channels.")

    # Cooling and crust.
    _add_float(group, "Cooling", 0.3, 0.0, 1.0,
               "0 is fresh and bright, 1 is mostly crusted over and dim.")
    _add_float(group, "Crust Amount", 0.3, 0.0, 1.0)
    _add_float(group, "Crust Scale", 7.0, 0.01, 100.0,
               "Size of the crust plates.")
    _add_float(group, "Crust Fragmentation", 0.4, 0.0, 2.0,
               "Width of the glowing cracks between crust plates.")
    _add_float(group, "Clump Amount", 0.35, 0.0, 1.0,
               "Extra solid islands of crust.")
    _add_float(group, "Clump Scale", 3.0, 0.01, 100.0)

    # Four independent debris systems.
    for label, amount, scale, size, clustering, phase in DEBRIS:
        _add_float(group, f"{label} Amount", amount, 0.0, 1.0,
                   "Share of cells that hold a stone.")
        _add_float(group, f"{label} Scale", scale, 0.1, 100.0)
        _add_float(group, f"{label} Size", size, 0.005, 0.8)
        _add_float(group, f"{label} Clustering", clustering, 0.0, 1.0,
                   "0 scatters stones evenly, 1 gathers them in patches.")
        _add_float(group, f"{label} Phase Offset", phase, -1000.0, 1000.0,
                   "Shifts this layer's timing; whole numbers change nothing.")

    # Colours, coolest to hottest.
    _add_color(group, "Molten Color", (1.0, 0.075, 0.006, 1.0),
               "Glow of ordinary flowing melt.")
    _add_color(group, "Hot Core Color", (1.0, 0.62, 0.08, 1.0),
               "Glow of the hottest melt.")
    _add_color(group, "Cooling Color", (0.22, 0.012, 0.003, 1.0),
               "Glow of melt that is nearly solid.")
    _add_color(group, "Rock Color", (0.018, 0.012, 0.009, 1.0))
    _add_color(group, "Crystal Color", (0.11, 0.075, 0.045, 1.0))
    _add_color(group, "Scoria Color", (0.035, 0.022, 0.016, 1.0))

    # Surface response.
    _add_float(group, "Metallic", 0.0, 0.0, 1.0)
    _add_float(group, "Debris Metallic", 0.05, 0.0, 1.0)
    _add_float(group, "Roughness", 0.32, 0.0, 1.0,
               "Roughness of the glassy patches on fresh crust.")
    _add_float(group, "Molten Roughness", 0.18, 0.0, 1.0)
    _add_float(group, "Rock Roughness", 0.88, 0.0, 1.0,
               "Roughness of the dull patches on crust.")
    _add_float(group, "Debris Roughness", 0.78, 0.0, 1.0)
    _add_float(group, "Emission Strength", 8.0, 0.0, 100.0)
    _add_float(group, "Emission Contrast", 0.65, 0.0, 1.0,
               "How steeply brightness rises with heat.")
    _add_float(group, "Hot Core Amount", 0.35, 0.0, 1.0)

    # Relief.
    _add_float(group, "Normal Strength", 0.65, 0.0, 5.0)
    _add_float(group, "Normal Distance", 0.12, 0.0, 5.0)
    _add_float(group, "Fine Normal Distance", 0.035, 0.0, 2.0)
    _add_float(group, "Displacement Strength", 0.18, 0.0, 5.0)
    _add_float(group, "Displacement Midlevel", 0.5, 0.0, 1.0)
    _add_float(group, "Surface Detail Scale", 35.0, 0.01, 300.0)
    _add_float(group, "Surface Detail Strength", 0.25, 0.0, 2.0)

    for name, socket_type in OUTPUTS:
        _interface(group, name, "OUTPUT", socket_type)


def _phase_ring(b, name, phase, speed, radius):
    """Turn a phase into a point on a circle: (sine, cosine) * radius.

    Moving a 4D texture around a circle brings it back exactly where it
    started, which is what makes the animation loop.
    """
    turns = b.math(f"{name} Turns", "MULTIPLY", phase, speed)
    angle = b.math(f"{name} Angle", "MULTIPLY", turns, TAU)
    sine = b.math(f"{name} Sine", "SINE", angle)
    cosine = b.math(f"{name} Cosine", "COSINE", angle)
    return (
        b.math(f"{name} Circle X", "MULTIPLY", sine, radius),
        b.math(f"{name} Circle Y", "MULTIPLY", cosine, radius),
        angle,
    )


def _loop_coords(b, name, xy, ring, scale):
    """4D coordinates for one texture: surface XY plus the loop circle.

    A texture multiplies every coordinate by its Scale, so the circle is
    divided by the same Scale first.  That keeps the amount of change per
    loop equal for every texture, whatever its scale.
    """
    z = b.math(f"{name} Loop Z", "DIVIDE", ring[0], scale)
    w = b.math(f"{name} Loop W", "DIVIDE", ring[1], scale)
    vector = b.combine(f"{name} Coordinates", (xy, "X"), (xy, "Y"), z)
    return vector, w


def _debris_layer(b, gi, label, xy, solid_radius):
    """One layer of stones.  Returns its mask (soft-edged, 0..1)."""
    phase = b.math(f"{label} Phase", "ADD",
                   (gi, "Flow Phase"), (gi, f"{label} Phase Offset"))
    ring = _phase_ring(b, label, phase, (gi, "Flow Speed"), solid_radius)
    coords = _loop_coords(b, label, xy, ring, (gi, f"{label} Scale"))

    cells = b.voronoi(f"{label} Cells", coords, (gi, f"{label} Scale"), "F1")

    # Two independent random numbers per cell.
    random = b.node("ShaderNodeSeparateXYZ", f"{label} Cell Random")
    b.feed(random, "Vector", (cells, "Color"))

    # Each stone gets its own radius: 0.6x to 1.4x of half the Size.
    radius_factor = b.math(f"{label} Size Variation", "MULTIPLY_ADD",
                           (random, "Y"), 0.4, 0.3)
    radius = b.math(f"{label} Radius", "MULTIPLY",
                    (gi, f"{label} Size"), radius_factor)
    inner = b.math(f"{label} Inner Radius", "MULTIPLY", radius, 0.55)
    stone = b.smoothstep(f"{label} Stone Shape", (cells, "Distance"),
                         inner, radius, invert=True)

    # Clustering noise is read at the cell centre, so a stone is never cut
    # in half by the edge of a patch.
    patch_noise = b.node("ShaderNodeTexNoise", f"{label} Patch Noise")
    patch_noise.noise_dimensions = "4D"
    b.feed(patch_noise, "Vector", (cells, "Position"))
    b.feed(patch_noise, "W", (cells, "W"))
    b.feed(patch_noise, "Scale", (gi, "Clump Scale"))
    b.feed(patch_noise, "Detail", 2.0)
    b.feed(patch_noise, "Roughness", 0.7)
    patch = b.smoothstep(f"{label} Patches", (patch_noise, "Fac"), 0.3, 0.7)

    chance = b.mix(f"{label} Scatter Or Cluster", "FLOAT",
                   (gi, f"{label} Clustering"), (random, "X"), patch)
    present = b.math(f"{label} Present", "LESS_THAN",
                     chance, (gi, f"{label} Amount"))
    return b.math(f"{label} Mask", "MULTIPLY", stone, present)


def create_node_group():
    """Create or rebuild the complete Procedural Magma shader node group."""
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is None:
        group = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
    else:
        group.nodes.clear()

    create_group_interface(group)
    b = _Builder(group)

    gi = b.node("NodeGroupInput", "Magma Controls")
    go = b.node("NodeGroupOutput", "Magma Outputs")
    go.is_active_output = True

    # UV, moved and turned, then drawn out along the flow.  The stretch is
    # applied after the rotation so it always follows the flow heading.
    texcoord = b.node("ShaderNodeTexCoord", "Magma Coordinates")
    mapping = b.node("ShaderNodeMapping", "Move And Turn")
    mapping.vector_type = "POINT"
    b.feed(mapping, "Vector", (texcoord, "UV"))
    b.feed(mapping, "Location", b.combine(
        "Position Offset", (gi, "Position X"), (gi, "Position Y"), 0.0))
    heading = b.math("Flow Heading", "ADD",
                     (gi, "Rotation"), (gi, "Flow Direction"))
    b.feed(mapping, "Rotation", b.combine("Heading Rotation", 0.0, 0.0, heading))

    along_flow = b.math("Stretch Along Flow", "DIVIDE", 1.0, (gi, "Flow Stretch"))
    stretch = b.node("ShaderNodeVectorMath", "Apply Flow Stretch")
    stretch.operation = "MULTIPLY"
    b.feed(stretch, "Vector", (mapping, "Vector"))
    b.feed(stretch, "Vector_001", b.combine("Stretch Factors", 1.0, along_flow, 1.0))
    surface = (stretch, "Vector")

    # Melt patterns use the stretched coordinates, Plates, Stones and Grain
    # use the unstretched ones so they are not drawn out into streaks.
    xy = b.node("ShaderNodeSeparateXYZ", "Flow XY")
    b.feed(xy, "Vector", surface)
    solid_xy = b.node("ShaderNodeSeparateXYZ", "Solid XY")
    b.feed(solid_xy, "Vector", (mapping, "Vector"))

    # Loop circles:
    melt_ring = _phase_ring(b, "Melt", (gi, "Flow Phase"), (gi, "Flow Speed"),
                            (gi, "Evolution"))
    solid_radius = b.math("Solid Evolution", "MULTIPLY",
                          (gi, "Evolution"), SOLID_EVOLUTION)
    solid_ring = (
        b.math("Solid Circle X", "MULTIPLY", melt_ring[0], SOLID_EVOLUTION),
        b.math("Solid Circle Y", "MULTIPLY", melt_ring[1], SOLID_EVOLUTION),
    )
    flow_angle = melt_ring[2]

    # Molten flow:
    flow_noise = b.noise(
        "Flow Noise",
        _loop_coords(b, "Flow", xy, melt_ring, (gi, "Flow Scale")),
        (gi, "Flow Scale"), 5.0, 0.68)
    flow_field = b.smoothstep("Flow Field", flow_noise, 0.35, 0.62)

    # Channels: Meandering streams running along the flow, Hottest down the middle.
    # They hold still, The motion comes from the heat pulses.
    channels = b.node("ShaderNodeTexWave", "Flow Channels")
    channels.wave_type = "BANDS"
    channels.bands_direction = "X"
    channels.wave_profile = "SIN"
    b.feed(channels, "Vector", surface)
    b.feed(channels, "Scale", b.math("Channel Scale", "MULTIPLY",
                                     (gi, "Flow Scale"), 0.5))
    b.feed(channels, "Distortion", b.math("Channel Meander", "MULTIPLY",
                                          (gi, "Flow Distortion"), 14.0))
    b.feed(channels, "Detail", (gi, "Flow Detail"))
    b.feed(channels, "Detail Scale", 0.7)
    channel_low = b.math("Channel Edge", "SUBTRACT", 1.0, (gi, "Flow Width"))
    channel_high = b.math("Channel Centre", "ADD", channel_low, 0.3)
    channel = b.smoothstep("Channel Mask", (channels, "Fac"),
                           channel_low, channel_high)

    # Heat pulses: Surges that travel down the channels, One band per loop.
    pulses = b.node("ShaderNodeTexWave", "Heat Pulses")
    pulses.wave_type = "BANDS"
    pulses.bands_direction = "Y"
    pulses.wave_profile = "SIN"
    b.feed(pulses, "Vector", surface)
    b.feed(pulses, "Scale", b.math("Pulse Scale", "MULTIPLY", (gi, "Flow Scale"), 0.5))
    b.feed(pulses, "Distortion", b.math("Pulse Distortion", "MULTIPLY",
                                        (gi, "Flow Distortion"), 10.0))
    b.feed(pulses, "Detail", 2.0)
    b.feed(pulses, "Phase Offset", flow_angle)
    pulse = b.math("Pulse Strength", "MULTIPLY_ADD", (pulses, "Fac"), 0.4, 0.6)

    flow = b.math("Flow", "MULTIPLY",
                  b.math("Flow In Channels", "MULTIPLY", flow_field, channel),
                  pulse)

    # Coverage: Broad patches, Thinner where the melt is moving fast.
    coverage_scale = b.math("Crust Coverage Scale", "MULTIPLY",
                            (gi, "Crust Scale"), 0.35)
    coverage_noise = b.noise(
        "Crust Coverage Noise",
        _loop_coords(b, "Crust Coverage", xy, solid_ring, coverage_scale),
        coverage_scale, 4.0, 0.72)
    coverage_field = b.math("Flow Thins Crust", "MULTIPLY_ADD",
                            flow, -0.25, coverage_noise)

    # More Crust Amount or more Cooling lowers the threshold -> more crust.
    crust_drive = b.math(
        "Crust Drive", "MULTIPLY_ADD", (gi, "Cooling"), 0.6,
        b.math("Crust Amount Share", "MULTIPLY", (gi, "Crust Amount"), 0.6),
        clamp=True)
    crust_low = b.math("Crust Threshold", "MULTIPLY_ADD", crust_drive, -0.5, 0.66)
    crust_high = b.math("Crust Threshold Top", "ADD", crust_low, 0.08)
    coverage = b.smoothstep("Crust Coverage", coverage_field, crust_low, crust_high)

    # Clumps: extra solid islands.
    clump_noise = b.noise(
        "Clump Noise",
        _loop_coords(b, "Clump", solid_xy, solid_ring, (gi, "Clump Scale")),
        (gi, "Clump Scale"), 3.0, 0.75)
    clump_high = b.math("Clump Threshold", "MULTIPLY_ADD",
                        (gi, "Clump Amount"), 0.35, 0.22)
    clump_low = b.math("Clump Threshold Bottom", "SUBTRACT", clump_high, 0.06)
    clumps = b.smoothstep("Clumps", clump_noise, clump_low, clump_high, invert=True)
    crust_area = b.math("Crust Area", "MAXIMUM", coverage, clumps)

    # Plates: the crust is broken along Voronoi edges.  A finer noise makes
    # the cracks ragged instead of ruler-straight.
    plates = b.voronoi(
        "Crust Plates",
        _loop_coords(b, "Crust Plates", solid_xy, solid_ring, (gi, "Crust Scale")),
        (gi, "Crust Scale"), "DISTANCE_TO_EDGE")
    ragged_scale = b.math("Crack Raggedness Scale", "MULTIPLY",
                          (gi, "Crust Scale"), 3.0)
    ragged_noise = b.noise(
        "Crack Raggedness Noise",
        _loop_coords(b, "Crack Raggedness", solid_xy, solid_ring, ragged_scale),
        ragged_scale, 3.0, 0.8)
    ragged = b.math("Centre Raggedness", "SUBTRACT", ragged_noise, 0.5)
    edge_distance = b.math("Ragged Edge Distance", "MULTIPLY_ADD",
                           ragged, 0.08, (plates, "Distance"))
                           
    # Cracks narrow as the surface cools.  The small constant keeps the
    # smoothstep edges apart when Crust Fragmentation is zero.
    crack_width = b.math(
        "Crack Width", "MULTIPLY_ADD", (gi, "Crust Fragmentation"),
        b.math("Cooling Narrows Cracks", "MULTIPLY_ADD", (gi, "Cooling"), -0.06, 0.1),
        0.002)
    plate = b.smoothstep("Plate Mask", edge_distance, 0.0, crack_width)
    rock_mask = b.math("Rock Mask", "MULTIPLY", crust_area, plate)
    
    # Debris:
    debris = {
        label: _debris_layer(b, gi, label, solid_xy, solid_radius)
        for label, *_ in DEBRIS
    }
    debris_mask = b.math(
        "Debris Mask", "MAXIMUM",
        b.math("Crystal Or Rock", "MAXIMUM", debris["Crystal"], debris["Rock"]),
        b.math("Scoria Or Crust Debris", "MAXIMUM",
               debris["Scoria"], debris["Crust Debris"]),
        clamp=True)

    solid = b.math("Solid Cover", "MAXIMUM", rock_mask, debris_mask)
    exposed = b.math("Exposed Melt", "SUBTRACT", 1.0, solid, clamp=True)
    flow_mask = b.math("Flow Mask", "MULTIPLY", flow, exposed)

    # Temperature:
    # Exposed melt idles at a dull red, runs hotter in the channels, and is
    # hottest in the cores.  Cooling pulls everything down.
    core_low = b.math("Hot Core Threshold", "MULTIPLY_ADD",
                      (gi, "Hot Core Amount"), -1.25, 1.0)
    core_high = b.math("Hot Core Threshold Top", "ADD", core_low, 0.25)
    core = b.smoothstep("Hot Cores", flow, core_low, core_high)
    melt_heat = b.math(
        "Melt Heat", "MULTIPLY_ADD", core, 0.25,
        b.math("Channel Heat", "MULTIPLY_ADD", flow, 0.3,
               b.math("Mottled Idle Heat", "MULTIPLY_ADD",
                      b.smoothstep("Melt Mottling", flow_noise, 0.3, 0.7),
                      0.3, 0.2)))
    cooled_heat = b.math(
        "Cooled Heat", "MULTIPLY", melt_heat,
        b.math("Cooling Factor", "MULTIPLY_ADD", (gi, "Cooling"), -0.5, 1.0))
    temperature = b.math("Temperature", "MULTIPLY", cooled_heat, exposed, clamp=True)

    # Brightness climbs steeply with temperature.
    steepness = b.math("Emission Steepness", "MULTIPLY_ADD",
                       (gi, "Emission Contrast"), 3.0, 1.0)
    emission_mask = b.math("Emission Mask", "POWER", temperature, steepness)
    emission_strength = b.math("Emission Strength", "MULTIPLY",
                               emission_mask, (gi, "Emission Strength"))

    # Glow colour: cooling -> molten -> hot core.
    glow = b.mix(
        "Hot Core Glow", "RGBA",
        b.smoothstep("Molten To Hot", temperature, 0.6, 0.95),
        b.mix("Molten Glow", "RGBA",
              b.smoothstep("Cooling To Molten", temperature, 0.2, 0.55),
              (gi, "Cooling Color"), (gi, "Molten Color")),
        (gi, "Hot Core Color"))

    # Surface colour:
    color = b.mix("Crust Color Layer", "RGBA", rock_mask, glow, (gi, "Rock Color"))
    for label, tint in (("Crystal", "Crystal Color"), ("Rock", "Rock Color"),
                        ("Scoria", "Scoria Color"), ("Crust Debris", "Rock Color")):
        color = b.mix(f"{label} Color Layer", "RGBA",
                      debris[label], color, (gi, tint))

    # Roughness and metallic:
    # Fresh crust is partly glassy, partly dull.
    dull = b.smoothstep("Dull Crust Patches", ragged_noise, 0.4, 0.6)
    crust_roughness = b.mix("Crust Roughness", "FLOAT", dull,
                            (gi, "Roughness"), (gi, "Rock Roughness"))
    roughness = b.mix(
        "Debris Roughness Layer", "FLOAT", debris_mask,
        b.mix("Melt Or Crust Roughness", "FLOAT", rock_mask,
              (gi, "Molten Roughness"), crust_roughness),
        (gi, "Debris Roughness"))
    metallic = b.mix("Metallic Layer", "FLOAT", debris_mask,
                     (gi, "Metallic"), (gi, "Debris Metallic"))

    # Height:
    # Crust and stones stand above the melt; cracks are grooves.  Folds and
    # grain belong to solid surfaces, so the melt keeps only a trace of them.
    folds = b.node("ShaderNodeTexWave", "Ropy Folds")
    folds.wave_type = "BANDS"
    folds.bands_direction = "Y"
    folds.wave_profile = "TRI"
    b.feed(folds, "Vector", surface)
    b.feed(folds, "Scale", (gi, "Flow Fold Scale"))
    b.feed(folds, "Distortion", b.math("Fold Distortion", "MULTIPLY",
                                       (gi, "Flow Distortion"), 14.0))
    b.feed(folds, "Detail", 3.0)
    b.feed(folds, "Detail Scale", 0.6)
    fold_height = b.math("Fold Height", "MULTIPLY",
                         b.math("Centre Folds", "SUBTRACT", (folds, "Fac"), 0.5),
                         (gi, "Flow Fold Strength"))

    grain_noise = b.noise(
        "Surface Grain Noise",
        _loop_coords(b, "Surface Grain", solid_xy, solid_ring, (gi, "Surface Detail Scale")),
        (gi, "Surface Detail Scale"), 4.0, 0.72)
    grain = b.math("Centre Grain", "SUBTRACT", grain_noise, 0.5)
    grain_height = b.math("Grain Height", "MULTIPLY",
                          grain, (gi, "Surface Detail Strength"))

    solid_relief = b.math("Relief On Solids", "MULTIPLY_ADD", solid, 0.8, 0.2)
    texture_height = b.math(
        "Textured Relief", "MULTIPLY",
        b.math("Add Raggedness", "MULTIPLY_ADD", ragged, 0.3,
               b.math("Folds Plus Grain", "ADD", fold_height, grain_height)),
        solid_relief)
    height = b.math(
        "Height", "MULTIPLY_ADD", debris_mask, 0.35,
        b.math("Raise Crust", "MULTIPLY_ADD", rock_mask, 0.5, texture_height))

    bump = b.node("ShaderNodeBump", "Primary Bump")
    b.feed(bump, "Strength", (gi, "Normal Strength"))
    b.feed(bump, "Distance", (gi, "Normal Distance"))
    b.feed(bump, "Height", height)

    fine_bump = b.node("ShaderNodeBump", "Fine Bump")
    b.feed(fine_bump, "Strength", (gi, "Normal Strength"))
    b.feed(fine_bump, "Distance", (gi, "Fine Normal Distance"))
    b.feed(fine_bump, "Height",
           b.math("Fine Grain On Solids", "MULTIPLY", grain, solid_relief))
    b.feed(fine_bump, "Normal", (bump, "Normal"))

    displacement = b.node("ShaderNodeDisplacement", "Magma Displacement")
    b.feed(displacement, "Height", height)
    b.feed(displacement, "Midlevel", (gi, "Displacement Midlevel"))
    b.feed(displacement, "Scale", (gi, "Displacement Strength"))

    # Shader:
    principled = b.node("ShaderNodeBsdfPrincipled", "Magma Principled BSDF")
    b.feed(principled, "Base Color", color)
    b.feed(principled, "Roughness", roughness)
    b.feed(principled, "Metallic", metallic)
    b.feed(principled, "Normal", (fine_bump, "Normal"))
    b.feed(principled, "Emission Color", glow)
    b.feed(principled, "Emission Strength", emission_strength)

    # Outputs:
    b.feed(go, "Shader", (principled, "BSDF"))
    b.feed(go, "Flow Mask", flow_mask)
    b.feed(go, "Debris Mask", debris_mask)
    b.feed(go, "Emission Mask", emission_mask)
    b.feed(go, "Rock Mask", rock_mask)
    b.feed(go, "Height", height)
    b.feed(go, "Surface Normal", (fine_bump, "Normal"))
    b.feed(go, "Displacement", (displacement, "Displacement"))

    _auto_layout(group)
    validate_node_group(group)
    return group


def _auto_layout(group):
    """Arrange nodes left to right in columns by how far downstream they are."""
    depth = {}

    def node_depth(node):
        if node in depth:
            return depth[node]
        depth[node] = 0  # guards against a cycle
        upstream = [
            link.from_node
            for socket in node.inputs for link in socket.links
        ]
        depth[node] = 1 + max((node_depth(n) for n in upstream), default=-1)
        return depth[node]

    for node in group.nodes:
        node_depth(node)
    last = max(depth.values(), default=0)
    for node in group.nodes:
        if node.bl_idname == "NodeGroupOutput":
            depth[node] = last

    columns = {}
    for node in group.nodes:
        columns.setdefault(depth[node], []).append(node)
    for column, members in columns.items():
        members.sort(key=lambda n: n.name)
        y = 0.0
        for node in members:
            node.location = (column * 260.0, y)
            tall = node.bl_idname in {
                "ShaderNodeBsdfPrincipled", "NodeGroupInput",
                "ShaderNodeTexNoise", "ShaderNodeTexVoronoi",
                "ShaderNodeTexWave", "ShaderNodeMapRange", "ShaderNodeMapping",
            }
            y -= 900.0 if node.bl_idname == "ShaderNodeBsdfPrincipled" else (
                340.0 if tall else 200.0)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate_node_group(group, verbose=True):
    """Check that the graph is wired the way it is meant to be.

    Raises RuntimeError listing every problem found.  Checks:
      * exactly one Group Input and one Group Output;
      * the public outputs exist with the expected types and are all fed;
      * every public input is actually used;
      * every link is valid and joins two *active* sockets (a link into a
        hidden socket looks connected but does nothing);
      * every texture has its coordinates supplied;
      * every node contributes to an output (nothing dangling);
      * no node is fed only by constants unless it is a coordinate source.
    """
    errors = []
    nodes = list(group.nodes)
    inputs = [n for n in nodes if n.bl_idname == "NodeGroupInput"]
    outputs = [n for n in nodes if n.bl_idname == "NodeGroupOutput"]
    if len(inputs) != 1:
        errors.append(f"Expected one Group Input; found {len(inputs)}.")
    if len(outputs) != 1:
        errors.append(f"Expected one Group Output; found {len(outputs)}.")
    if errors:
        raise RuntimeError("Magma validation failed:\n- " + "\n- ".join(errors))
    input_node, output_node = inputs[0], outputs[0]

    # Public interface.
    declared = {
        item.name: item.socket_type
        for item in group.interface.items_tree
        if item.item_type == "SOCKET" and item.in_out == "OUTPUT"
    }
    for name, socket_type in OUTPUTS:
        if name not in declared:
            errors.append(f"Missing output: {name}")
        elif declared[name] != socket_type:
            errors.append(
                f"Output '{name}' is {declared[name]}, expected {socket_type}.")
    for socket in output_node.inputs:
        if socket.identifier != "__extend__" and not socket.is_linked:
            errors.append(f"Unconnected output: {socket.name}")
    for socket in input_node.outputs:
        if socket.identifier != "__extend__" and not socket.is_linked:
            errors.append(f"Control does nothing (not connected): {socket.name}")

    # Links.
    for link in group.links:
        where = (f"{link.from_node.name}.{link.from_socket.name} -> "
                 f"{link.to_node.name}.{link.to_socket.name}")
        if not link.is_valid:
            errors.append(f"Invalid link: {where}")
        if link.is_muted:
            errors.append(f"Muted link: {where}")
        if not link.from_socket.enabled:
            errors.append(f"Link starts at an inactive socket: {where} "
                          f"[{link.from_socket.identifier}]")
        if not link.to_socket.enabled:
            errors.append(f"Link ends at an inactive socket: {where} "
                          f"[{link.to_socket.identifier}]")
        shader_from = link.from_socket.type == "SHADER"
        shader_to = link.to_socket.type == "SHADER"
        if shader_from != shader_to:
            errors.append(f"Shader/value mismatch: {where}")

    # Per-node checks.
    sources = {"ShaderNodeTexCoord"}
    for node in nodes:
        if node in (input_node, output_node):
            continue
        if node.mute:
            errors.append(f"Node is muted: {node.name}")
        if node.bl_idname.startswith("ShaderNodeTex") and node.bl_idname not in sources:
            vector = node.inputs.get("Vector")
            if vector is not None and not vector.is_linked:
                errors.append(f"Texture has no coordinates: {node.name}")
            w = node.inputs.get("W")
            if w is not None and w.enabled and not w.is_linked:
                errors.append(f"4D texture has no W (will not animate): {node.name}")
        if node.bl_idname not in sources and node.inputs and not any(
                s.is_linked for s in node.inputs if s.enabled):
            errors.append(f"Node has no connected input: {node.name}")

    # Everything must lead to the outputs.
    reached = {output_node}
    stack = [output_node]
    while stack:
        node = stack.pop()
        for socket in node.inputs:
            for link in socket.links:
                if link.from_node not in reached:
                    reached.add(link.from_node)
                    stack.append(link.from_node)
    for node in nodes:
        if node not in reached:
            errors.append(f"Node does not reach any output: {node.name}")

    if errors:
        raise RuntimeError(
            "Procedural Magma validation failed:\n- " + "\n- ".join(errors)
        )

    if verbose:
        print(
            f"[{GROUP_NAME}] Validation passed: {len(nodes)} nodes, "
            f"{len(group.links)} links, "
            f"{len([s for s in input_node.outputs if s.is_linked])} controls in use, "
            f"{len([s for s in output_node.inputs if s.is_linked])} outputs fed."
        )
    return True


# --------------------------------------------------------------------------
# Using the group
# --------------------------------------------------------------------------

def add_magma_group_to_material(material, use_displacement=False):
    """Insert Procedural Magma into a material and connect its shader.

    With use_displacement=True the Displacement output is connected as well
    and the material is set to true displacement (Cycles; the mesh needs
    enough subdivision to show it).
    """
    if material is None:
        raise ValueError("A valid material is required.")
    material.use_nodes = True
    tree = material.node_tree
    group = bpy.data.node_groups.get(GROUP_NAME) or create_node_group()

    group_node = tree.nodes.new("ShaderNodeGroup")
    group_node.node_tree = group
    group_node.label = GROUP_NAME
    group_node.location = (0, 0)
    group_node.width = 260

    # Find the output by type: node names change with the interface language.
    material_outputs = [n for n in tree.nodes if n.type == "OUTPUT_MATERIAL"]
    output = next((n for n in material_outputs if n.is_active_output),
                  material_outputs[0] if material_outputs else None)
    if output is None:
        output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (350, 0)

    tree.links.new(group_node.outputs["Shader"], output.inputs["Surface"])
    if use_displacement:
        tree.links.new(group_node.outputs["Displacement"],
                       output.inputs["Displacement"])
        try:
            material.displacement_method = "DISPLACEMENT"
        except (AttributeError, TypeError):
            pass
    return group_node


def register():
    """Create or rebuild the Procedural Magma node group."""
    create_node_group()


def unregister():
    """No persistent Blender classes are registered by this module."""
    return None


if __name__ == "__main__":
    register()