import bpy
from bpy.types import Panel, Node, NodeSocket

# Import the property group
from .properties import SequencedBakeProperties

# -----------------------------
# Node Socket
# -----------------------------
class SequencedBakeSocket(NodeSocket):
    """
    Custom NodeSocket for Sequenced Bake nodes.

    This socket is used within custom shader nodes to represent
    connections for the Sequenced Bake system. It displays a
    yellow color in the node editor.

    Attributes:
        bl_idname (str): Blender identifier for the socket type.
        bl_label (str): Human-readable label for the socket.
    """
    bl_idname = "SequencedBakeSocket"
    bl_label = "Sequenced Bake Socket"

    def draw(self, context, layout, node, text):
        """
        Draws the socket in the node UI.

        Args:
            context (bpy.types.Context): Blender context.
            layout (bpy.types.UILayout): The layout to draw into.
            node (bpy.types.Node): The node that owns this socket.
            text (str): The label text for the socket.
        """
        layout.label(text=text)

    def draw_color(self, context, node):
        """
        Returns the display color for the socket in the node editor.

        Args:
            context (bpy.types.Context): Blender context.
            node (bpy.types.Node): The node that owns this socket.

        Returns:
            tuple: RGBA color (yellow).
        """
        return (0.8, 0.8, 0.2, 1.0)  # Yellow


# -----------------------------
# Helper: Draw UI
# -----------------------------
def draw_sequenced_bake_ui(layout, props):
    """
    Draws the full Sequenced Bake UI for panels or nodes.

    This function renders the user interface for configuring
    Sequenced Bake settings, including:
    - Output path
    - Image size and format
    - Selected-to-active options
    - Image texture settings
    - Bake type toggles and lighting contributions
    - Color management options
    - Bake operator button

    Args:
        layout (bpy.types.UILayout): Blender UI layout object.
        props (SequencedBakeProperties): Property group containing
            all Sequenced Bake settings.
    """
    option_padding = 2.0

    # Output Path
    box = layout.box()
    col = box.column(align=True)
    col.label(text="Material Output Path:")
    col.prop(props, "sequenced_bake_output_path")

    col.separator(factor=3.0, type='LINE')

    # Image Size
    col.label(text="Generated Image Size:")
    row = col.row(align=True)
    row.prop(props, "sequenced_bake_width")
    row.prop(props, "sequenced_bake_height")

    col.separator()
    col.label(text="Baked Image Format:")
    col.prop(props, "sequenced_bake_image_format")

    col.separator()
    col.prop(props, "sequence_is_alpha")
    col.prop(props, "sequence_use_float")
    col.prop(props, "sequence_clear_baked_maps")

    col.separator(factor=3.0, type='LINE')

    # Selected to Active
    col.label(text="Selected to Active:")
    col.prop(props, "sequenced_selected_to_active")
    if props.sequenced_selected_to_active:
        col.label(text="Selected to Active Options:")
        row = col.row()
        row.separator(factor=option_padding)
        row.prop(props, "selected_to_active_cage")
        if props.selected_to_active_cage:
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(props, "selected_to_active_cage_object")
        row = col.row()
        row.separator(factor=option_padding)
        row.prop(props, "selected_to_active_extrusion")
        row = col.row()
        row.separator(factor=option_padding)
        row.prop(props, "selected_to_active_max_ray_distance")

    col.separator(factor=3.0, type='LINE')

    # Image Texture Settings
    col.label(text="Image Texture Settings:")
    col.prop(props, "interpolation")
    col.prop(props, "projection")
    col.prop(props, "extension")
    col.prop(props, "colorspace")

    col.separator(factor=3.0, type='LINE')

    # Bake Type Options
    col.label(text="Bake Type Options:")
    col.prop(props, "sequenced_bake_normal")
    if props.sequenced_bake_normal:
        col.label(text="Normal Map Options:")
        for ch in ["space", "red_channel", "green_channel", "blue_channel"]:
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(props, f"normal_map_{ch}")

    col.prop(props, "sequenced_bake_roughness")
    col.prop(props, "sequenced_bake_glossy")
    if props.sequenced_bake_glossy:
        col.label(text="Lighting Contributions:")
        for attr in ["glossy_lighting_direct", "glossy_lighting_indirect", "glossy_lighting_color"]:
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(props, attr, text=attr.split("_")[-1].capitalize())

    col.prop(props, "sequenced_bake_emission")
    col.prop(props, "sequenced_bake_ambient_occlusion")
    col.prop(props, "sequenced_bake_shadow")
    col.prop(props, "sequenced_bake_position")
    col.prop(props, "sequenced_bake_uv")
    col.prop(props, "sequenced_bake_environment")
    col.prop(props, "sequenced_bake_diffuse")
    if props.sequenced_bake_diffuse:
        col.label(text="Lighting Contributions:")
        for attr in ["diffuse_lighting_direct", "diffuse_lighting_indirect", "diffuse_lighting_color"]:
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(props, attr, text=attr.split("_")[-1].capitalize())

    col.prop(props, "sequenced_bake_transmission")
    if props.sequenced_bake_transmission:
        col.label(text="Lighting Contributions:")
        for attr in ["transmission_lighting_direct", "transmission_lighting_indirect", "transmission_lighting_color"]:
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(props, attr, text=attr.split("_")[-1].capitalize())

    col.prop(props, "sequenced_bake_combined")
    if props.sequenced_bake_combined:
        col.label(text="Lighting Contributions:")
        for attr in ["combined_lighting_direct", "combined_lighting_indirect",
                     "combined_contribution_deffuse", "combined_contribution_glossy",
                     "combined_contribution_transmission", "combined_contribution_emit"]:
            row = col.row()
            row.separator(factor=option_padding)
            row.prop(props, attr)

    col.prop(props, "sequenced_bake_metallic")

    col.separator(factor=3.0, type='LINE')

    # Color Management
    col.label(text="Color Management:")
    for attr in ["display_device", "view_transform", "look", "exposure", "gamma", "sequencer"]:
        col.prop(props, attr)

    col.separator(factor=3.0, type='LINE')
    col.operator("sequenced_bake.bake", text="Bake Material Sequence")


# -----------------------------
# Panel
# -----------------------------
class SequencedBakePanel(Panel):
    """
    UI Panel for the Sequenced Bake add-on.

    Displays the Sequenced Bake settings in the 3D View's UI
    sidebar. Uses the draw_sequenced_bake_ui helper to render
    the full configuration interface.

    Attributes:
        bl_label (str): Panel label shown in Blender.
        bl_idname (str): Blender identifier for the panel.
        bl_space_type (str): Space type where the panel is displayed.
        bl_region_type (str): Region type (sidebar).
        bl_description (str): Tooltip description of the panel.
        bl_category (str): Sidebar tab name.
    """
    bl_label = "Sequenced Bake"
    bl_idname = "VIEW3D_PT_sequenced_bake"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_description = "Bake a material sequence based on the defined settings and keyframed node settings."
    bl_category = 'Sequenced Bake'

    def draw(self, context):
        scene = context.scene
        if not hasattr(scene, "sequenced_bake_props"):
            self.layout.label(text="Sequenced Bake not initialized")
            return
        draw_sequenced_bake_ui(self.layout, scene.sequenced_bake_props)


# -----------------------------
# Node
# -----------------------------
class SequencedBakeNode(Node):
    """
    Custom Shader Node for Sequenced Bake.

    Provides a node-based interface in the Shader Editor for controlling
    material baking sequences. Mirrors the settings available in the
    UI panel.

    Attributes:
        bl_idname (str): Blender identifier for the node type.
        bl_label (str): Node label displayed in the editor.
        bl_description (str): Tooltip description.
        bl_icon (str): Node icon in the editor.
    """
    bl_idname = "ShaderNodeSequencedBake"
    bl_label = "Sequenced Bake"
    bl_description = "Bake a material sequence based on the defined settings and keyframed node settings."
    bl_icon = "NODE"

    def init(self, context):
        self.width = 300

    def draw_buttons(self, context, layout):
        scene = context.scene
        if not hasattr(scene, "sequenced_bake_props"):
            layout.label(text="Sequenced Bake not initialized")
            return
        draw_sequenced_bake_ui(layout, scene.sequenced_bake_props)

    def draw_buttons_ext(self, context, layout):
        layout.label(text="Extended Settings")

    def draw_label(self):
        return "Sequenced Bake"
