# This file is part of Sequence Bake.
#
# Sequence Bake is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or any later version.
#
# Sequence Bake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.


import bpy
import os
import re
import sys
from bpy.types import (
    Operator,
    Panel,
    Node,
    NodeSocket,
    PropertyGroup,
)

IMAGE_FORMAT_ITEMS = [
    ("PNG", "PNG", "Save as PNG"),
    ("JPEG", "JPEG", "Save as JPEG"),
    ("BMP", "BMP", "Save as BMP"),
    ("TIFF", "TIFF", "Save as TIFF"),
    ("TGA", "TGA", "Save as TGA"),
    ("EXR", "OpenEXR", "Save as OpenEXR"),
    ("HDR", "Radiance HDR", "Save as Radiance HDR"),
    ("CINEON", "Cineon", "Save as Cineon"),
    ("DPX", "DPX", "Save as DPX"),
]

NORMAL_MAP_SPACE_ITEMS = [
    ('OBJECT', "Object", "Use object space for the normal map"),
    ('TANGENT', "Tangent", "Use tangent space for the normal map"),
]

NORMAL_MAP_SWIZZLE_ITEMS = [
    ("POS_X", '+X', "Positive X axis"),
    ("POS_Y", '+Y', "Positive Y axis"),
    ("POS_Z", '+Z', "Positive Z axis"),
    ("NEG_X", '-X', "Negative X axis"),
    ("NEG_Y", '-Y', "Negative Y axis"),
    ("NEG_Z", '-Z', "Negative Z axis"),
]

SEQUENCER_COLORSPACE_ITEMS = [
    (
        "ACES2065-1",
        "ACES2065-1",
        "ACES interchange colorspace (scene-linear, archival and exchange)"
    ),
    (
        "ACEScg",
        "ACEScg",
        "ACES scene-linear working space for CG rendering and compositing"
    ),
    (
        "AgX Base_Display_P3",
        "AgX Base Display P3",
        "AgX base working space targeting Display P3 gamut"
    ),
    (
        "AgX Base_Rec_1886",
        "AgX Base Rec.1886",
        "AgX base working space targeting Rec.1886 broadcast displays"
    ),
    (
        "AgX Base_Rec_2020",
        "AgX Base Rec.2020",
        "AgX base working space targeting wide-gamut Rec.2020"
    ),
    (
        "AgX Base_sRGB",
        "AgX Base sRGB",
        "AgX base working space targeting standard sRGB displays"
    ),
    (
        "AgX Log",
        "AgX Log",
        "AgX logarithmic colorspace for grading and tone mapping"
    ),
    (
        "Display P3",
        "Display P3",
        "Display-referred P3 colorspace (non-linear)"
    ),
    (
        "Filmic Log",
        "Filmic Log",
        "Logarithmic Filmic colorspace for grading workflows"
    ),
    (
        "Filmic sRGB",
        "Filmic sRGB",
        "Filmic tone-mapped output in sRGB display space"
    ),
    (
        "Khronos PBR Neutral sRGB",
        "Khronos PBR Neutral sRGB",
        "Khronos PBR Neutral display-referred colorspace in sRGB"
    ),
    (
        "Linear CIE XYZ D65",
        "Linear CIE-XYZ D65",
        "Scene-linear CIE XYZ colorspace using D65 white point"
    ),
    (
        "Linear CIE XYZ E",
        "Linear CIE-XYZ E",
        "Scene-linear CIE XYZ colorspace using equal-energy white point"
    ),
    (
        "Linear DCI P3 D65",
        "Linear DCI-P3 D65",
        "Scene-linear DCI-P3 colorspace with D65 white point"
    ),
    (
        "Linear FilmLight E Gamut",
        "Linear FilmLight E-Gamut",
        "Scene-linear FilmLight E-Gamut colorspace (high-end VFX)"
    ),
    (
        "Linear Rec.2020",
        "Linear Rec.2020",
        "Scene-linear Rec.2020 wide-gamut working space"
    ),
    (
        "Linear Rec.709",
        "Linear Rec.709",
        "Scene-linear Rec.709 working space (linear sRGB primaries)"
    ),
    (
        "Non-Color",
        "Non-Color",
        "Data colorspace (no color transform; masks, mattes, data)"
    ),
    (
        "Rec.1886",
        "Rec.1886",
        "Display-referred Rec.1886 broadcast colorspace"
    ),
    (
        "Rec.2020",
        "Rec.2020",
        "Display-referred Rec.2020 wide-gamut colorspace"
    ),
    (
        "sRGB",
        "sRGB",
        "Standard display-referred sRGB colorspace (default)"
    ),
]


DISPLAY_DEVICE_ITEMS = [
    (
        "sRGB",
        "sRGB",
        "Standard dynamic range display device (default; OCIO standard)"
    ),
    (
        "Display P3",
        "Display P3",
        "Wide-gamut P3 display device (OCIO; typically Apple displays)"
    ),
    (
        "Rec.1886",
        "Rec.1886",
        "Broadcast SDR display device (gamma-based television standard)"
    ),
    (
        "Rec.2020",
        "Rec.2020",
        "Wide-gamut SDR display device (BT.2020 color primaries)"
    ),
    (
        "Rec.2100 PQ",
        "Rec.2100 PQ",
        "HDR display device using Perceptual Quantizer transfer function (OCIO-dependent)"
    ),
    (
        "Rec.2100 HLG",
        "Rec.2100 HLG",
        "HDR display device using Hybrid Log-Gamma transfer function (OCIO-dependent)"
    ),
]

VIEW_TRANSFORM_ITEMS = [
    (
        "Standard",
        "Standard",
        "Display-referred view with no tone mapping (linear to display conversion only)"
    ),
    (
        "Khronos PBR Neutral",
        "Khronos PBR Neutral",
        "Physically based neutral tone mapper for PBR workflows (Khronos reference)"
    ),
    (
        "AgX",
        "AgX",
        "Modern high-dynamic-range tone mapping view (default in Blender 5.0)"
    ),
    (
        "Filmic",
        "Filmic",
        "Legacy Filmic tone mapping for high dynamic range scenes"
    ),
    (
        "Filmic Log",
        "Filmic Log",
        "Logarithmic Filmic view for grading and compositing workflows"
    ),
    (
        "False Color",
        "False Color",
        "Diagnostic view showing exposure and luminance ranges"
    ),
    (
        "Raw",
        "Raw",
        "Unprocessed scene-linear values with no view transform applied"
    ),
]

LOOK_ITEMS = [
    ('None', 'None', 'No artistic look (AgX only)'),
    ('Punchy', 'Punchy',
     'AgX only — increased contrast and saturation'),
    ('Greyscale', 'Greyscale',
     'AgX only — monochrome output'),
    ('Very High Contrast', 'Very High Contrast',
     'AgX only — very strong contrast curve'),
    ('High Contrast', 'High Contrast',
     'AgX only — strong contrast curve'),
    ('Medium High Contrast', 'Medium High Contrast',
     'AgX only — moderately strong contrast'),
    ('Base Contrast', 'Base Contrast',
     'AgX only — default AgX contrast'),
    ('Medium Low Contrast', 'Medium Low Contrast',
     'AgX only — slightly reduced contrast'),
    ('Low Contrast', 'Low Contrast',
     'AgX only — low contrast look'),
    ('Very Low Contrast', 'Very Low Contrast',
     'AgX only — minimal contrast'),
]

INTERPOLATION_ITEMS = [
    ('Linear', "Linear", "Use linear interpolation"),
    ('Closest', "Closest", "Use nearest neighbor interpolation"),
    ('Cubic', "Cubic", "Use cubic interpolation"),
    ('Smart', "Smart", "Use smart interpolation"),
]

PROJECTION_ITEMS = [
    ('Flat', "Flat", "Flat projection"),
    ('Box', "Box", "Box projection"),
    ('Square', "Square", "Square projection"),
    ('Tube', "Tube", "Tube projection"),
]

EXTENSION_ITEMS = [
    ('Repeat', "Repeat", "Repeat the texture"),
    ('Extend', "Extend", "Extend the texture edges"),
    ('Clip', "Clip", "Clip the texture to the image bounds"),
    ('Mirror', "Mirror", "Mirror the texture"),
]

COLOR_SPACE_ITEMS = [
    (
        "ACES2065-1",
        "ACES2065-1",
        "ACES interchange color space for archival and data exchange (very wide gamut)"
    ),
    (
        "ACEScg",
        "ACEScg",
        "ACES scene-linear working space optimized for CG rendering and compositing"
    ),
    (
        "AgX Base_Display_P3",
        "AgX Base Display P3",
        "AgX base rendering space targeting Display P3 primaries"
    ),
    (
        "AgX Base_Rec_1886",
        "AgX Base Rec.1886",
        "AgX base rendering space targeting Rec.1886 display characteristics"
    ),
    (
        "AgX Base_Rec_2020",
        "AgX Base Rec.2020",
        "AgX base rendering space targeting Rec.2020 wide-gamut displays"
    ),
    (
        "AgX Base_sRGB",
        "AgX Base sRGB",
        "AgX base rendering space targeting standard sRGB displays"
    ),
    (
        "AgX Log",
        "AgX Log",
        "Logarithmic AgX space intended for grading and intermediate color work"
    ),
    (
        "Display P3",
        "Display P3",
        "Display-referred P3 color space commonly used by Apple devices"
    ),
    (
        "Filmic Log",
        "Filmic Log",
        "Logarithmic Filmic space for color grading and compositing workflows"
    ),
    (
        "Filmic sRGB",
        "Filmic sRGB",
        "Filmic tone-mapped output encoded to sRGB primaries"
    ),
    (
        "Khronos PBR Neutral sRGB",
        "Khronos PBR Neutral sRGB",
        "Neutral PBR display-referred space aligned with Khronos material standards"
    ),
    (
        "Linear CIE XYZ D65",
        "Linear CIE-XYZ D65",
        "Scene-linear CIE XYZ color space using D65 white point"
    ),
    (
        "Linear CIE XYZ E",
        "Linear CIE-XYZ E",
        "Scene-linear CIE XYZ color space using equal-energy white point"
    ),
    (
        "Linear DCI P3 D65",
        "Linear DCI-P3 D65",
        "Scene-linear DCI-P3 color space with D65 white point"
    ),
    (
        "Linear FilmLight E Gamut",
        "Linear FilmLight E-Gamut",
        "Scene-linear FilmLight E-Gamut used in professional VFX pipelines"
    ),
    (
        "Linear Rec.2020",
        "Linear Rec.2020",
        "Scene-linear Rec.2020 wide-gamut color space"
    ),
    (
        "Linear Rec.709",
        "Linear Rec.709",
        "Scene-linear Rec.709 color space (legacy broadcast standard)"
    ),
    (
        "Non-Color",
        "Non-Color",
        "Data-only space with no color transform (normals, roughness, masks)"
    ),
    (
        "Rec.1886",
        "Rec.1886",
        "Display-referred Rec.1886 color space for legacy video systems"
    ),
    (
        "Rec.2020",
        "Rec.2020",
        "Display-referred Rec.2020 color space for HDR and wide-gamut displays"
    ),
    (
        "sRGB",
        "sRGB",
        "Standard display-referred sRGB color space"
    ),
]


class SequencedBakeProperties(PropertyGroup):
    sequenced_bake_output_path: bpy.props.StringProperty(
        name="",
        default="",
        subtype='DIR_PATH',
        description='Define the output path for the rendered images'
    )
    sequenced_bake_width: bpy.props.IntProperty(
        name="Width",
        description='The width of the baked image',
        default=1024,
        min=1,
        max=8192
    )
    sequenced_bake_height: bpy.props.IntProperty(
        name="Height",
        description='The height of the baked image',
        default=1024,
        min=1,
        max=8192
    )
    sequenced_bake_image_format: bpy.props.EnumProperty(
        name="",
        description="Choose the image format",
        items=IMAGE_FORMAT_ITEMS,
        default="PNG"
    )
    sequence_is_alpha: bpy.props.BoolProperty(
        name="Use Alpha",
        description="Use alpha channel in the generated material maps",
        default=False
    )
    sequence_use_float: bpy.props.BoolProperty(
        name="32-bit Float",
        description="Create image with 32-bit floating-point bit depth\nControls the internal precision of the image during creation and baking.",
        default=False
    )
    sequence_clear_baked_maps: bpy.props.BoolProperty(
        name="Clear Baked Maps",
        description="Clears the baked maps from blenders image viewer list",
        default=True
    )
    sequenced_selected_to_active: bpy.props.BoolProperty(
        name="Selected to Active",
        description='Enable to bake from the selected object into the active one',
        default=False
    )

    # Selected to Active options.
    selected_to_active_cage: bpy.props.BoolProperty(
        name="Cage",
        description='Cast rays to active object from a cage',
        default=False
    )
    selected_to_active_cage_object: bpy.props.PointerProperty(
        name="Cage Object",
        description='Object to use as cage',
        type=bpy.types.Object
    )
    selected_to_active_extrusion: bpy.props.FloatProperty(
        name="Extrusion",
        description='Inflate the active object by the specified distance for baking',
        default=0.0,
        min=0.0,
        max=sys.float_info.max,
        unit='LENGTH'
    )
    selected_to_active_max_ray_distance: bpy.props.FloatProperty(
        name="Max Ray Distance",
        description='The maximum ray distance for matching points between the active and selected objects. If zero, there is no limit',
        default=0.0,
        min=0.0,
        max=sys.float_info.max,
        unit='LENGTH'
    )

    sequenced_bake_normal: bpy.props.BoolProperty(
        name="Normal",
        description='Enable to bake the normal map for the selected objects active material',
        default=False
    )

    # Normal map options.
    normal_map_space: bpy.props.EnumProperty(
        name="Space",
        description="Normal map coordinate space",
        items=NORMAL_MAP_SPACE_ITEMS,
        default='TANGENT'
    )
    normal_map_red_channel: bpy.props.EnumProperty(
        name="R",
        description="Swizzle for the R channel",
        items=NORMAL_MAP_SWIZZLE_ITEMS,
        default="POS_X"
    )
    normal_map_green_channel: bpy.props.EnumProperty(
        name="G",
        description="Swizzle for the G channel",
        items=NORMAL_MAP_SWIZZLE_ITEMS,
        default="POS_Y"
    )
    normal_map_blue_channel: bpy.props.EnumProperty(
        name="B",
        description="Swizzle for the B channel",
        items=NORMAL_MAP_SWIZZLE_ITEMS,
        default="POS_Z"
    )
    sequenced_bake_roughness: bpy.props.BoolProperty(
        name="Roughness",
        description='Enable to bake the roughness map for the selected objects active material',
        default=False
    )
    sequenced_bake_glossy: bpy.props.BoolProperty(
        name="Glossy",
        description='Enable to bake the glossy map for the selected objects active material',
        default=False
    )
    sequenced_bake_emission: bpy.props.BoolProperty(
        name="Emission",
        description='Enable to bake the emissive map for the selected objects active material',
        default=False
    )
    sequenced_bake_ambient_occlusion: bpy.props.BoolProperty(
        name="Ambient Occlusion",
        description='Enable to bake the ambient occlusion map for the selected objects active material',
        default=False
    )
    sequenced_bake_shadow: bpy.props.BoolProperty(
        name="Shadow",
        description='Enable to bake the shadow map for the selected objects active material',
        default=False
    )
    sequenced_bake_position: bpy.props.BoolProperty(
        name="Position",
        description='Enable to bake the position map for the selected objects active material',
        default=False
    )
    sequenced_bake_uv: bpy.props.BoolProperty(
        name="UV",
        description='Enable to bake the UV map for the selected objects active material',
        default=False
    )
    sequenced_bake_environment: bpy.props.BoolProperty(
        name="Environment",
        description='Enable to bake the environment map for the selected objects active material',
        default=False
    )
    sequenced_bake_diffuse: bpy.props.BoolProperty(
        name="Diffuse",
        description='Enable to bake the deffuse map for the selected objects active material',
        default=False
    )
    sequenced_bake_transmission: bpy.props.BoolProperty(
        name="Transmission",
        description='Enable to bake the transmission map for the selected objects active material',
        default=False
    )
    sequenced_bake_combined: bpy.props.BoolProperty(
        name="Combined",
        description='Enable to bake the combined map for the selected objects active material',
        default=False
    )
    sequenced_bake_metallic: bpy.props.BoolProperty(
        name="Metallic",
        description='Enable to bake the metallic map for the selected objects active material',
        default=False
    )

    # Lighting options.
    diffuse_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )
    diffuse_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )
    diffuse_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )
    glossy_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )
    glossy_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )
    glossy_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )
    transmission_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )
    transmission_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )
    transmission_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )
    combined_lighting_direct: bpy.props.BoolProperty(
        name="Direct",
        description="Include direct lighting in the bake",
        default=True
    )
    combined_lighting_indirect: bpy.props.BoolProperty(
        name="Indirect",
        description="Include indirect lighting in the bake",
        default=True
    )
    combined_lighting_color: bpy.props.BoolProperty(
        name="Color",
        description="Include color lighting contributions in the bake",
        default=True
    )
    combined_contribution_deffuse: bpy.props.BoolProperty(
        name="Diffuse",
        description="Include diffuse contributions in the bake",
        default=True
    )
    combined_contribution_glossy: bpy.props.BoolProperty(
        name="Glossy",
        description="Include glossy contributions in the bake",
        default=True
    )
    combined_contribution_transmission: bpy.props.BoolProperty(
        name="Transmission",
        description="Include transmission contributions in the bake",
        default=True
    )
    combined_contribution_emit: bpy.props.BoolProperty(
        name="Emit",
        description="Include emission contributions in the bake",
        default=True
    )

    # Color Management options.
    # Display Device
    display_device: bpy.props.EnumProperty(
        name="Display Device",
        description="Select the display device",
        items=DISPLAY_DEVICE_ITEMS,
        default="sRGB"
    )
    # View Transform
    view_transform: bpy.props.EnumProperty(
        name="View Transform",
        description="Select the view transform",
        items=VIEW_TRANSFORM_ITEMS,
        default="Standard"
    )
    # Look
    look: bpy.props.EnumProperty(
        name="Look",
        description="Select the look",
        items=LOOK_ITEMS,
        default="None"
    )
    # Exposure
    exposure: bpy.props.FloatProperty(
        name="Exposure",
        description="Adjust the exposure level",
        default=0.0,
        min=-10.0,
        max=10.0
    )

    # Gamma
    gamma: bpy.props.FloatProperty(
        name="Gamma",
        description="Adjust the gamma level",
        default=1.0,
        min=0.0,
        max=5.0
    )

    # Sequencer
    sequencer: bpy.props.EnumProperty(
        name="Sequencer",
        description="Select the sequencer color space",
        items=SEQUENCER_COLORSPACE_ITEMS,
        default="sRGB"
    )

    # Image texture settings.
    interpolation: bpy.props.EnumProperty(
        name="Interpolation",
        description="Set the texture interpolation method",
        items=INTERPOLATION_ITEMS,
        default='Linear'
    )
    projection: bpy.props.EnumProperty(
        name="Projection",
        description="Set the texture projection method",
        items=PROJECTION_ITEMS,
        default='Flat'
    )
    extension: bpy.props.EnumProperty(
        name="Extension",
        description="Set the texture extension method",
        items=EXTENSION_ITEMS,
        default='Repeat'
    )

    colorspace: bpy.props.EnumProperty(
        name="Colorspace",
        description="Select the color space",
        items=COLOR_SPACE_ITEMS,
        default="sRGB"
    )
