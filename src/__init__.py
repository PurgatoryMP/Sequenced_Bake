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


bl_info = {
    "name": "Sequenced Bake",
    "author": "Anthony OConnell",
    "version": (1, 2, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Sequenced Bake",
    "description": "Tools for baking material sequences and generating sprite sheets",
    "category": "3D View"
}

import bpy
from . import node_group_library
from .node_group_library import (
    SequencedBakeNodeGroupOperator,
    NODE_MT_sequenced_bake_group_library,
    register_node_group_library,
    unregister_node_group_library,
)
from .sequenced_bake_core import (
    SequencedBakeUDIMTile,
    SEQUENCED_BAKE_UL_udim_tiles,
    SEQUENCED_BAKE_OT_udim_add,
    SEQUENCED_BAKE_OT_udim_remove,
    SequencedBakeProperties,
    SequencedBakePanel,
    SequencedBakeNode,
    SequencedBakeSocket,
    SequencedBakeOperator,
    MESH_OT_add_sculpt_mesh,
    VIEW3D_MT_mesh_sculpties_add,
    menu_func_add_sculpties,
)
from .sprite_sheet_creator import (
    SpriteSheetCreatorPanel,
    SpriteSheetCreatorNode,
    SpriteSheetCreatorSocket,
    SpriteSheetCreatorVSEPanel,
    SpriteSheetProperties,
    OBJECT_OT_CreateSpriteSheet,
)
from bpy.types import AddonPreferences


class SequencedBakeAddonProperties(AddonPreferences):
    bl_idname = __name__

    website_url: bpy.props.StringProperty(
        name="Website URL",
        description="The Blender Extensions website.",
        default="https://extensions.blender.org/add-ons/sequenced-bake/"
    )
    
    github_url: bpy.props.StringProperty(
        name="GitHub URL",
        description="The GitHub repository for the Sequenced Bake add-on.",
        default="https://github.com/PurgatoryMP/Sequenced_Bake"
    )
    
    discord_url: bpy.props.StringProperty(
        name="Discord URL",
        description="The Discord Community Server",
        default="https://discord.gg/uyaq8CQwRk"
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Resources and Community.")
        row.operator("wm.url_open", text="Blender Extensions").url = self.website_url
        row.operator("wm.url_open", text="GitHub").url = self.github_url
        row.operator("wm.url_open", text="Discord Community").url = self.discord_url


_node_menu_registered = False


class NODE_MT_sequenced_bake_add_menu(bpy.types.Menu):
    """Organize all Sequenced Bake nodes under one Add-menu submenu."""

    bl_label = "Sequenced Bake"
    bl_idname = "NODE_MT_sequenced_bake_add_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            "node.add_node",
            text="Sequenced Bake",
            icon="NODE",
        ).type = "ShaderNodeSequencedBake"
        layout.operator(
            "node.add_node",
            text="Sprite Sheet Creator",
            icon="NODE",
        ).type = "ShaderNodeSpriteSheetCreatorNode"
        layout.separator()
        layout.menu(
            "NODE_MT_sequenced_bake_group_library",
            text="Node Group Library",
            icon="NODETREE",
        )


def draw_custom_node_menu(self, context):
    """Add the Sequenced Bake submenu to compatible Shader Editors."""
    space = getattr(context, "space_data", None)
    if not space or space.type != "NODE_EDITOR":
        return
    if getattr(space, "tree_type", "") != "ShaderNodeTree":
        return
    self.layout.menu(
        NODE_MT_sequenced_bake_add_menu.bl_idname,
        text="Sequenced Bake",
        icon="NODETREE",
    )


def add_custom_node_category():
    """Add custom node entries to Blender's Add menu."""
    global _node_menu_registered
    if not _node_menu_registered:
        bpy.types.NODE_MT_add.append(draw_custom_node_menu)
        _node_menu_registered = True


def remove_custom_node_category():
    """Remove custom node entries from Blender's Add menu."""
    global _node_menu_registered
    if _node_menu_registered:
        try:
            bpy.types.NODE_MT_add.remove(draw_custom_node_menu)
        except (ValueError, RuntimeError):
            pass
        _node_menu_registered = False


classes = (
    # Preferences
    SequencedBakeAddonProperties,

    # Sequenced Bake
    SequencedBakeUDIMTile,
    SEQUENCED_BAKE_UL_udim_tiles,
    SEQUENCED_BAKE_OT_udim_add,
    SEQUENCED_BAKE_OT_udim_remove,
    SequencedBakeProperties,
    SequencedBakeSocket,
    SequencedBakeNode,
    SequencedBakeOperator,
    SequencedBakePanel,

    # Sculpt Primitives
    MESH_OT_add_sculpt_mesh,
    VIEW3D_MT_mesh_sculpties_add,

    # Sprite Sheet
    SpriteSheetProperties,
    SpriteSheetCreatorSocket,
    SpriteSheetCreatorNode,
    OBJECT_OT_CreateSpriteSheet,
    SpriteSheetCreatorPanel,
    SpriteSheetCreatorVSEPanel,
    NODE_MT_sequenced_bake_group_library,
    SequencedBakeNodeGroupOperator,
    NODE_MT_sequenced_bake_add_menu,
)


def register():
    # Register all classes FIRST
    for cls in classes:
        bpy.utils.register_class(cls)

    # THEN create pointer properties
    bpy.types.Scene.sequenced_bake_props = bpy.props.PointerProperty(
        type=SequencedBakeProperties,
        name="Sequenced Bake Props",
    )

    bpy.types.Scene.sprite_sheet_props = bpy.props.PointerProperty(
        type=SpriteSheetProperties,
        name="Sprite Sheet Props",
    )

    # Build and register the procedural node-group library.
    register_node_group_library()

    # Append menus to Blender UI
    add_custom_node_category()
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func_add_sculpties)


def unregister():
    # Remove custom UI menus
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func_add_sculpties)
    remove_custom_node_category()
    unregister_node_group_library()

    if hasattr(bpy.types.Scene, "sprite_sheet_props"):
        del bpy.types.Scene.sprite_sheet_props

    if hasattr(bpy.types.Scene, "sequenced_bake_props"):
        del bpy.types.Scene.sequenced_bake_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()