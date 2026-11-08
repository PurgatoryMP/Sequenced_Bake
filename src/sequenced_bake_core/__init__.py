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

# NOTE:
# This package intentionally does NOT register or unregister Blender classes.
# All registration is handled by the root add-on __init__.py.

from .properties import (
    SequencedBakeUDIMTile,
    SequencedBakeProperties,
)

from .ui import (
    SEQUENCED_BAKE_UL_udim_tiles,
    SequencedBakePanel,
    SequencedBakeNode,
    SequencedBakeSocket,
)
from .operator import (
    SEQUENCED_BAKE_OT_udim_add,
    SEQUENCED_BAKE_OT_udim_remove,
    SequencedBakeOperator,
)
from .sculpt_map import (
    MESH_OT_add_sculpt_mesh,
    VIEW3D_MT_mesh_sculpties_add,
    menu_func_add_sculpties,
)

__all__ = (
    "SequencedBakeUDIMTile",
    "SequencedBakeProperties",
    "SEQUENCED_BAKE_UL_udim_tiles",
    "SequencedBakePanel",
    "SequencedBakeNode",
    "SequencedBakeSocket",
    "SEQUENCED_BAKE_OT_udim_add",
    "SEQUENCED_BAKE_OT_udim_remove",
    "SequencedBakeOperator",
    "MESH_OT_add_sculpt_mesh",
    "VIEW3D_MT_mesh_sculpties_add",
    "menu_func_add_sculpties",
)