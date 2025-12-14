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


bl_info = {
    "name": "Sequenced Bake",
    "author": "Anthony OConnell",
    "version": (1, 0, 14),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Sequenced Bake",
    "description": "Tools for baking material sequences and generating sprite sheets",
    "category": "3D View"
}

import bpy
from .sequenced_bake import (
    SequencedBakeProperties,
    SequencedBakePanel,
    SequencedBakeNode,
    SequencedBakeSocket,
    SequencedBakeOperator,
)
from .sprite_sheet_creator import (
    SpriteSheetProperties,
    SpriteSheetCreatorPanel,
    OBJECT_OT_CreateSpriteSheet,
)
from bpy.types import (
        Operator,
        AddonPreferences,
        Node,
        NodeSocket,
        )

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
        

def add_custom_node_category():
    bpy.types.NODE_MT_add.append(draw_custom_node_menu)

def remove_custom_node_category():
    bpy.types.NODE_MT_add.remove(draw_custom_node_menu)

def draw_custom_node_menu(self, context):
    layout = self.layout
    layout.operator("node.add_node", text="Sequenced Bake").type = "ShaderNodeSequencedBake"

def register():
    bpy.utils.register_class(SequencedBakeAddonProperties)
    
    # Register Sequence Bake components
    bpy.utils.register_class(SequencedBakePanel)
    bpy.utils.register_class(SequencedBakeOperator)
    bpy.utils.register_class(SequencedBakeProperties)
    bpy.utils.register_class(SequencedBakeSocket)
    bpy.utils.register_class(SequencedBakeNode)
    bpy.types.Scene.sequenced_bake_props = bpy.props.PointerProperty(type=SequencedBakeProperties)
    bpy.types.ShaderNode.sequenced_bake_props = bpy.props.PointerProperty(type=SequencedBakeProperties)
    
    # Register Sprite Sheet components
    bpy.utils.register_class(SpriteSheetCreatorPanel)
    bpy.utils.register_class(SpriteSheetProperties)
    bpy.types.Scene.sprite_sheet_props = bpy.props.PointerProperty(type=SpriteSheetProperties)
    bpy.utils.register_class(OBJECT_OT_CreateSpriteSheet)
    
    add_custom_node_category()

def unregister():
    remove_custom_node_category()

    bpy.utils.unregister_class(SequencedBakeAddonProperties)
    
    # Unregister Sequence Bake components
    bpy.utils.unregister_class(SequencedBakePanel)
    bpy.utils.unregister_class(SequencedBakeOperator)
    bpy.utils.unregister_class(SequencedBakeProperties)
    bpy.utils.unregister_class(SequencedBakeSocket)
    bpy.utils.unregister_class(SequencedBakeNode)
    del bpy.types.Scene.sequenced_bake_props
    
    # Unregister Sprite Sheet components
    bpy.utils.unregister_class(SpriteSheetCreatorPanel)
    bpy.utils.unregister_class(SpriteSheetProperties)
    bpy.utils.unregister_class(OBJECT_OT_CreateSpriteSheet)
    del bpy.types.Scene.sprite_sheet_props


if __name__ == "__main__":
    register()
