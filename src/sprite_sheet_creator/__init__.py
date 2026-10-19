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


from .properties import SpriteSheetProperties
from .operators import OBJECT_OT_CreateSpriteSheet
from .ui import (
    SpriteSheetCreatorPanel,
    SpriteSheetCreatorVSEPanel,
    SpriteSheetCreatorNode,
    SpriteSheetCreatorSocket,
)

__all__ = (
    "SpriteSheetProperties",
    "OBJECT_OT_CreateSpriteSheet",
    "SpriteSheetCreatorPanel",
    "SpriteSheetCreatorVSEPanel",
    "SpriteSheetCreatorNode",
    "SpriteSheetCreatorSocket",
)