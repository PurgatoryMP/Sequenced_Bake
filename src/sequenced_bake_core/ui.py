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
from bpy.types import Panel, Node, NodeSocket
from .properties import SequencedBakeProperties


def draw_material_manager_ui(layout, context):
    """
    Custom Material Manager UI.

    - Uses Blender material slots (MATERIAL_UL_matslots)
    - Removes redundant active_material selector
    - Empty slot → Add New Material button
    - Filled slot → Editable material name
    - Fake User toggle
    - Link data control
    - Bake actions dropdown
    """
    obj = context.object

    box = layout.box()
    col = box.column(align=True)
    col.label(text="Materials")

    if not obj or obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
        col.label(text="No compatible object selected")
        return

    # Material Slots List
    row = col.row()

    row.template_list(
        "MATERIAL_UL_matslots",
        "",
        obj,
        "material_slots",
        obj,
        "active_material_index",
        rows=4,
    )

    slot_ops = row.column(align=True)
    slot_ops.separator()
    slot_ops.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
    slot_ops.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
    slot_ops.separator()
    if hasattr(bpy.types, "OBJECT_MT_material_slot_specials"):
        slot_ops.menu(
            "OBJECT_MT_material_slot_specials",
            icon='DOWNARROW_HLT',
            text=""
        )

    # Slot Material Controls
    slot = (
        obj.material_slots[obj.active_material_index]
        if obj.material_slots and obj.active_material_index >= 0
        else None
    )

    mat = slot.material if slot else None

    row = col.row(align=True)

    if mat is None:
        # Empty slot → create new material
        row.operator(
            "material.new",
            text="Add New Material",
            icon='ADD'
        )
    else:
        # Existing material → editable name
        row.prop(mat, "name", text="")

        # Fake user toggle
        row.prop(
            mat,
            "use_fake_user",
            text="",
            icon='FAKE_USER_ON' if mat.use_fake_user else 'FAKE_USER_OFF'
        )

    # Link data control (always available)
    row.prop(obj, "active_material", text="", icon='LINKED')


class SequencedBakeSocket(NodeSocket):
    """
    Custom NodeSocket for Sequenced Bake nodes.

    This socket is used within custom shader nodes to represent
    connections for the Sequenced Bake system. It displays a
    yellow color in the node editor.

    Class Attributes:
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


def draw_sequenced_bake_ui(layout, props):
    """
    Draws the full Sequenced Bake UI for panels or nodes using boxed sections.

    Sections:
    - Material Output
    - Image Size & Format
    - Selected to Active
    - Image Texture Settings
    - Bake Type Options
    - Color Management
    - Bake Operator Button

    Args:
        layout (bpy.types.UILayout): Blender UI layout object.
        props (SequencedBakeProperties): Property group containing
            all Sequenced Bake settings.
    """
    option_padding = 2.0

    # Material Manager
    if hasattr(props, "show_material_manager") and props.show_material_manager:
        draw_material_manager_ui(layout, bpy.context)

    # Image Size & Format
    box = layout.box()
    header = box.row()
    header.prop(
        props,
        "ui_show_image_settings",
        text="Generated Image Settings",
        emboss=False,
        icon='TRIA_DOWN' if props.ui_show_image_settings else 'TRIA_RIGHT'
    )

    if props.ui_show_image_settings:
        col = box.column(align=True)
        scene = bpy.context.scene

        # frame range
        frame_box = col.box()
        frame_box.label(
            text=f"Frame Range: {scene.frame_start} : {scene.frame_end} : {scene.frame_end - scene.frame_start + 1}"
        )

        row = frame_box.row(align=True)
        row.prop(scene, "frame_start", text="Start")
        row.prop(scene, "frame_end", text="End")
        row.prop(scene, "frame_current", text="Current")

        row = frame_box.row(align=True)

        row.prop(props, "sequenced_bake_width")
        row.prop(props, "sequenced_bake_height")

        col.prop(props, "sequenced_bake_image_format")
        col.prop(props, "sequence_is_alpha")
        col.prop(props, "sequence_use_float")
        col.prop(props, "sequence_clear_baked_maps")

    # Selected to Active
    box = layout.box()
    header = box.row()
    header.prop(
        props,
        "ui_show_selected_to_active",
        text="Selected to Active",
        emboss=False,
        icon='TRIA_DOWN' if props.ui_show_selected_to_active else 'TRIA_RIGHT'
    )

    if props.ui_show_selected_to_active:
        col = box.column(align=True)
        col.prop(props, "sequenced_selected_to_active")

        if props.sequenced_selected_to_active:
            col.prop(props, "selected_to_active_cage")
            if props.selected_to_active_cage:
                col.prop(props, "selected_to_active_cage_object")
            col.prop(props, "selected_to_active_extrusion")
            col.prop(props, "selected_to_active_max_ray_distance")

    # Image Texture Settings
    box = layout.box()
    header = box.row()
    header.prop(
        props,
        "ui_show_texture_settings",
        text="Image Texture Settings",
        emboss=False,
        icon='TRIA_DOWN' if props.ui_show_texture_settings else 'TRIA_RIGHT'
    )

    if props.ui_show_texture_settings:
        col = box.column(align=True)
        col.prop(props, "interpolation")
        col.prop(props, "projection")
        col.prop(props, "extension")
        col.prop(props, "colorspace")

    # Bake Type Options
    box = layout.box()
    header = box.row()
    header.prop(
        props,
        "ui_show_bake_types",
        text="Bake Type Options",
        emboss=False,
        icon='TRIA_DOWN' if props.ui_show_bake_types else 'TRIA_RIGHT'
    )
    if props.ui_show_bake_types:
        col = box.column(align=True)

        col.prop(props, "sequenced_bake_normal")
        if props.sequenced_bake_normal:
            col.label(text="Normal Map Options:")

            for ch in ["preset", "space", "red_channel", "green_channel", "blue_channel"]:
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
            for attr in ["transmission_lighting_direct", "transmission_lighting_indirect",
                         "transmission_lighting_color"]:
                row = col.row()
                row.separator(factor=option_padding)
                row.prop(props, attr, text=attr.split("_")[-1].capitalize())

        col.prop(props, "sequenced_bake_combined")
        if props.sequenced_bake_combined:
            col.label(text="Lighting Contributions:")
            for attr in ["combined_lighting_direct", "combined_lighting_indirect",
                         "combined_contribution_diffuse", "combined_contribution_glossy",
                         "combined_contribution_transmission", "combined_contribution_emit"]:
                row = col.row()
                row.separator(factor=option_padding)
                row.prop(props, attr)

        col.prop(props, "sequenced_bake_metallic")

        col.prop(props, "sequenced_bake_occlusion")

        col.prop(props, "sequenced_bake_sculpt")

        if props.sequenced_bake_sculpt:
            col.label(text="Sculpt Map Bounds:")

            for attr in [
                "sequenced_sculpt_show_bbox",
                "sequenced_sculpt_bbox_dynamic",
                "sequenced_sculpt_bbox_scale",
            ]:
                row = col.row()
                row.separator(factor=option_padding)
                row.prop(props, attr)

            col.label(text="Sculpt Map Transforms:")

            for attr in [
                "sequenced_sculpt_offset_x",
                "sequenced_sculpt_offset_y",
                "sequenced_sculpt_offset_z",
            ]:
                row = col.row()
                row.separator(factor=option_padding)
                row.prop(props, attr)

    # Color Management
    box = layout.box()
    header = box.row()
    header.prop(
        props,
        "ui_show_color_management",
        text="Color Management",
        emboss=False,
        icon='TRIA_DOWN' if props.ui_show_color_management else 'TRIA_RIGHT'
    )
    if props.ui_show_color_management:
        col = box.column(align=True)
        for attr in ["display_device", "view_transform", "look", "exposure", "gamma", "sequencer"]:
            col.prop(props, attr)

    # Material Output
    box = layout.box()
    header = box.row()
    header.prop(
        props,
        "ui_show_bake_controls",
        text="Bake Controls",
        emboss=False,
        icon='TRIA_DOWN' if getattr(props, "ui_show_bake_controls", True)
        else 'TRIA_RIGHT'
    )

    if getattr(props, "ui_show_bake_controls", True):
        col = box.column(align=True)

        col.label(text="Bake Controls:")
        col.label(text="Bake Scope:")
        col.prop(props, "material_mode")
        col.prop(props, "frame_mode")

        if props.frame_mode == 'SEQUENCE':
            col.prop(props, "frame_step")

        if props.frame_mode == 'CURRENT':
            col.label(text="Only current frame will be baked", icon='INFO')
        else:
            col.label(
                text=f"Frames: {bpy.context.scene.frame_start} → {bpy.context.scene.frame_end} (step {props.frame_step})",
                icon='TIME'
            )

        col.label(text="Material Output Path:")
        col.prop(props, "sequenced_bake_output_path")

        col.separator(factor=1.0)

        col.operator(
            "sequenced_bake.bake",
            text="Bake Material Sequence",
            icon='RENDER_STILL'
        )

        col.separator()

        col.label(text="Bake Progress:")

        row = col.row(align=True)
        row.prop(props, "bake_progress", text="")
        row.enabled = False

    # Bake Details
    box = layout.box()

    header = box.row()
    header.prop(
        props,
        "ui_show_bake_details",
        text="Bake Details",
        emboss=False,
        icon='TRIA_DOWN' if props.ui_show_bake_details else 'TRIA_RIGHT'
    )

    if props.ui_show_bake_details:
        col = box.column(align=True)

        col.label(text=f"Status: {props.bake_status}")
        col.label(text=f"Material: {props.bake_current_material}")
        col.label(text=f"Bake Type: {props.bake_current_type}")
        col.label(text=f"Frame#: {props.bake_frame_info}")
        col.label(text="FPS: %.3f" % props.bake_fps)
        col.label(text=f"Time Remaining: {props.bake_estimated_time}")


class SequencedBakePanel(Panel):
    """
    UI Panel for the Sequenced Bake add-on.

    Displays the Sequenced Bake settings in the 3D View's UI
    sidebar. Uses the draw_sequenced_bake_ui helper to render
    the full configuration interface.

    Class Attributes:
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


class SequencedBakeNode(Node):
    """
    Custom Shader Node for Sequenced Bake.

    Provides a node-based interface in the Shader Editor for controlling
    material baking sequences. Mirrors the settings available in the
    UI panel.

    Class Attributes:
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
