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
from bpy.types import Panel, Node, NodeSocket


# ------------------------------------------------------------------------
# Node Socket
# ------------------------------------------------------------------------

class SpriteSheetCreatorSocket(NodeSocket):
    bl_idname = "SpriteSheetCreatorSocket"
    bl_label = "Sprite Sheet Creator Socket"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.2, 1.0)


# ------------------------------------------------------------------------
# Node
# ------------------------------------------------------------------------

class SpriteSheetCreatorNode(Node):
    bl_idname = "ShaderNodeSpriteSheetCreatorNode"
    bl_label = "Sprite Sheet Creator"
    bl_description = "Create Sprite Sheets"
    bl_icon = "NODE"

    def init(self, context):
        self.width = 300

    def draw_buttons(self, context, layout):
        self._draw_sprite_sheet_ui(context, layout)

    # ------------------------------------------------------------------
    # Shared UI Drawer
    # ------------------------------------------------------------------

    def _draw_sprite_sheet_ui(self, context, layout):
        scene = context.scene
        props = scene.sprite_sheet_props

        box = layout.box()
        col = box.column(align=True)

        # -------------------- Source --------------------

        col.label(text="Source:")
        col.prop(props, "source_type")

        if props.source_type == 'DIRECTORY':
            col.separator()
            col.label(text="Image Sequence Directory:")
            col.prop(props, "directory")

        if props.source_type == 'VSE':
            col.separator()
            col.prop(props, "use_all_vse_channels")
            if not props.use_all_vse_channels:
                col.prop(props, "vse_channel")

        col.separator(factor=3.0, type='LINE')

        # -------------------- Layout --------------------

        col.label(text="Sprite Sheet Properties:")
        col.prop(props, "columns")
        col.prop(props, "rows")

        col.separator()
        col.prop(props, "image_width")
        col.prop(props, "image_height")

        col.separator()
        col.prop(props, "start_frame")
        col.prop(props, "end_frame")

        col.separator()
        col.prop(props, "is_reversed")

        col.separator(factor=3.0, type='LINE')

        # -------------------- Output --------------------

        col.label(text="Output File Name:")
        row = col.row(align=True)
        row.prop(props, "file_name")
        row.prop(props, "sprite_sheet_image_format")

        col.separator()

        if props.source_type == 'VSE':
            col.label(text="VSE Output Directory:")
            col.prop(props, "vse_output_path")

        if props.source_type == 'COMPOSITOR':
            col.separator()
            col.label(text="Compositor Output Directory:")
            col.prop(props, "compositor_output_path")

        col.separator()
        col.prop(props, "file_overwrite")

        col.separator(factor=3.0, type='LINE')

        # -------------------- Options --------------------

        col.prop(props, "sprite_sheet_is_alpha")
        col.prop(props, "open_images")
        col.prop(props, "open_output_directory")
        col.prop(props, "clear_generated_images")

        col.separator(factor=3.0, type='LINE')

        # -------------------- Execute --------------------

        col.operator("object.create_sprite_sheet", text="Generate Sprite Sheet")


# ------------------------------------------------------------------------
# Viewport Panel
# ------------------------------------------------------------------------

class SpriteSheetCreatorPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VIEW3D_PT_Sprite_Sheet_Creator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sprite Sheet Creator"

    def draw(self, context):
        SpriteSheetCreatorNode._draw_sprite_sheet_ui(self, context, self.layout)


# ------------------------------------------------------------------------
# VSE Panel
# ------------------------------------------------------------------------

class SpriteSheetCreatorVSEPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VSE_PT_Sprite_Sheet_Creator"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Sprite Sheet Creator"

    def draw(self, context):
        SpriteSheetCreatorNode._draw_sprite_sheet_ui(self, context, self.layout)
