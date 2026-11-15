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

import math
import bpy
from bpy.types import Panel, Node, NodeSocket


class SPRITESHEET_UL_ImageList(bpy.types.UIList):
    """UIList displaying images found in the selected directory (filtered by active UDIM if present)."""

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        has_udims = bool(getattr(data, "detected_udim_tiles", ""))
        selected_udim = (
            int(data.selected_udim_tile)
            if has_udims and data.selected_udim_tile.isdigit()
            else 0
        )

        flt_flags = []
        for item in items:
            if not has_udims or item.udim == selected_udim:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, []

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Compute 1-based display index relative to the visible UDIM group
            has_udims = bool(getattr(data, "detected_udim_tiles", ""))
            if has_udims:
                display_num = sum(
                    1 for i in range(index + 1)
                    if data.directory_images[i].udim == item.udim
                )
            else:
                display_num = index + 1

            row = layout.row(align=True)
            row.label(text=f"{display_num}.", icon="IMAGE_DATA")
            row.label(text=item.name)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="IMAGE_DATA")


class SpriteSheetCreatorSocket(NodeSocket):
    bl_idname = "SpriteSheetCreatorSocket"
    bl_label = "Sprite Sheet Creator Socket"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.2, 1.0)


class SpriteSheetCreatorNode(Node):
    bl_idname = "ShaderNodeSpriteSheetCreatorNode"
    bl_label = "Sprite Sheet Creator"
    bl_description = "Create Sprite Sheets"
    bl_icon = "NODE"

    def init(self, context):
        self.width = 300

    def draw_buttons(self, context, layout):
        self._draw_sprite_sheet_ui(context, layout)

    # Shared UI Drawer
    def _draw_sprite_sheet_ui(self, context, layout):
        """
        Draws the full Sprite Sheet Creator UI using boxed sections.

        Sections:
        - Source
        - Layout (sprite sheet properties)
        - Output
        - Options
        - Execute (button)

        Args:
            context (bpy.types.Context): Blender context.
            layout (bpy.types.UILayout): UI layout to draw into.
        """
        scene = context.scene
        props = scene.sprite_sheet_props

        # Source
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Source:")
        col.prop(props, "source_type")

        if props.source_type == 'DIRECTORY':
            col.label(text="Image Directory:")
            col.prop(props, "directory")

            has_udims = bool(props.detected_udim_tiles)
            if has_udims:
                col.separator(factor=0.5)
                col.prop(props, "selected_udim_tile", text="UDIM Tile")
                selected_udim = int(props.selected_udim_tile) if props.selected_udim_tile.isdigit() else 0
                visible_count = sum(1 for item in props.directory_images if item.udim == selected_udim)
            else:
                visible_count = len(props.directory_images)

            col.separator(factor=0.5)
            header_row = col.row(align=True)
            header_row.label(text=f"Images ({visible_count}):")
            header_row.operator("spritesheet.list_action", text="", icon="FILE_REFRESH").action = "REFRESH"

            list_row = col.row()
            list_row.template_list(
                "SPRITESHEET_UL_ImageList",
                "",
                props,
                "directory_images",
                props,
                "directory_images_index",
                rows=5,
            )

            btn_col = list_row.column(align=True)
            btn_col.operator("spritesheet.add_images", text="", icon="ADD")
            btn_col.operator("spritesheet.list_action", text="", icon="REMOVE").action = "REMOVE"
            btn_col.separator(factor=0.5)
            btn_col.operator("spritesheet.list_action", text="", icon="TRIA_UP_BAR").action = "TOP"
            btn_col.operator("spritesheet.list_action", text="", icon="TRIA_UP").action = "UP"
            btn_col.operator("spritesheet.list_action", text="", icon="TRIA_DOWN").action = "DOWN"
            btn_col.operator("spritesheet.list_action", text="", icon="TRIA_DOWN_BAR").action = "BOTTOM"
            btn_col.separator(factor=0.5)
            btn_col.operator("spritesheet.list_action", text="", icon="ARROW_LEFTRIGHT").action = "REVERSE"

        if props.source_type == 'VSE':
            col.prop(props, "use_all_vse_channels")
            if not props.use_all_vse_channels:
                col.prop(props, "vse_channel")

        # Layout
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Sprite Sheet Properties:")
        
        col.separator(factor=0.5)
        
        row = col.row(align=True)
        row.enabled = not props.use_fixed_resolution
        row.prop(props, "columns")
        row.prop(props, "rows")
        
        col.separator(factor=0.5)
        
        row = col.row(align=True)
        row.prop(props, "image_width")
        row.prop(props, "image_height")
        
        col.separator(factor=0.5)
        
        row = col.row(align=True)
        row.prop(props, "start_frame")
        row.prop(props, "end_frame")
        
        col.separator(factor=0.5)
        col.prop(props, "use_fixed_resolution")

        if props.use_fixed_resolution:
            col.separator(factor=0.5)
            row = col.row(align=True)
            row.prop(props, "output_width")
            row.prop(props, "output_height")

            cols_per_sheet = max(1, props.output_width // props.image_width)
            rows_per_sheet = max(1, props.output_height // props.image_height)
            out_w = props.output_width
            out_h = props.output_height
        else:
            cols_per_sheet = props.columns
            rows_per_sheet = props.rows
            out_w = props.columns * props.image_width
            out_h = props.rows * props.image_height

        cells_per_sheet = max(1, cols_per_sheet * rows_per_sheet)
        total_frames = max(0, props.end_frame - props.start_frame + 1)
        sheet_count = math.ceil(total_frames / cells_per_sheet) if total_frames > 0 else 0

        col.separator(factor=0.5)
        col.label(text=f"Output Resolution: {out_w} x {out_h} px")
        col.label(text=f"Sprite Sheets to Create: {sheet_count}")
 
        # Output
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Output File Name:")
        
        col.separator(factor=1.0)
        
        row = col.row(align=True)
        row.prop(props, "file_name")
        row.prop(props, "sprite_sheet_image_format")

        if props.source_type == 'VSE':
            col.label(text="VSE Output Directory:")
            col.prop(props, "vse_output_path")

        if props.source_type == 'COMPOSITOR':
            col.label(text="Compositor Output Directory:")
            col.prop(props, "compositor_output_path")

        col.separator(factor=1.0)
        col.prop(props, "file_overwrite")

        # Options
        box = layout.box()
        col = box.column(align=True)
        col.prop(props, "sprite_sheet_is_alpha")
        col.prop(props, "open_images")
        col.prop(props, "open_output_directory")
        col.prop(props, "clear_generated_images")

        # Execute
        box = layout.box()
        col = box.column(align=True)
        col.operator("object.create_sprite_sheet", text="Generate Sprite Sheet")

# Viewport Panel
class SpriteSheetCreatorPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VIEW3D_PT_Sprite_Sheet_Creator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sprite Sheet Creator"

    def draw(self, context):
        SpriteSheetCreatorNode._draw_sprite_sheet_ui(self, context, self.layout)

# VSE Panel
class SpriteSheetCreatorVSEPanel(Panel):
    bl_label = "Sprite Sheet Creator"
    bl_idname = "VSE_PT_Sprite_Sheet_Creator"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Sprite Sheet Creator"

    def draw(self, context):
        SpriteSheetCreatorNode._draw_sprite_sheet_ui(self, context, self.layout)
