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

import sys
import importlib
import inspect
import pkgutil
import traceback

import bpy

from bpy.props import StringProperty
from bpy.types import Menu, Operator


_GROUPS = {}
_DISCOVERY_ERRORS = {}


def _log(message):
    """Print a consistently formatted library diagnostic."""
    print(f"[Sequenced Bake Node Library] {message}")


def _get_factory(module):
    """Find and validate a module's node-group factory."""
    factory = getattr(module, "create_node_group", None)

    if not callable(factory):
        candidates = [
            value
            for name, value in inspect.getmembers(
                module, inspect.isfunction
            )
            if name.startswith("create_")
            and name.endswith("_group")
            and value.__module__ == module.__name__
        ]

        if len(candidates) == 1:
            factory = candidates[0]

        elif len(candidates) > 1:
            raise RuntimeError(
                "Multiple factory functions found. "
                "Define an explicit create_node_group() function."
            )

    if not callable(factory):
        raise RuntimeError(
            "No valid create_node_group() factory was found."
        )

    if factory.__module__ != module.__name__:
        raise RuntimeError(
            "The factory must be defined inside its own module."
        )

    signature = inspect.signature(factory)

    required_parameters = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.default is inspect.Parameter.empty
        and parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]

    if required_parameters:
        raise RuntimeError(
            "Factory must be callable without arguments."
        )

    return factory


def _discover_group_factories():
    """Discover valid node-group factories independently."""
    discovered = []
    registered_names = {}

    for module_info in sorted(
        pkgutil.iter_modules(__path__),
        key=lambda item: item.name.lower(),
    ):
        module_name = module_info.name

        if module_name.startswith("_") or module_info.ispkg:
            continue

        full_module_name = f"{__name__}.{module_name}"

        try:
            if full_module_name in sys.modules:
                module = importlib.reload(
                sys.modules[full_module_name]
            )
            else:
                module = importlib.import_module(full_module_name)

            group_name = getattr(module, "GROUP_NAME", None)

            if not isinstance(group_name, str) or not group_name.strip():
                continue

            group_name = group_name.strip()

            if group_name in registered_names:
                raise RuntimeError(
                    f"Duplicate GROUP_NAME '{group_name}'. "
                    f"Already defined in '{registered_names[group_name]}'."
                )

            factory = _get_factory(module)

            registered_names[group_name] = module_name
            discovered.append((group_name, module_name, factory))

            _log(
                f"Discovered '{group_name}' "
                f"from {module_name}.py"
            )

        except Exception as exc:
            _DISCOVERY_ERRORS[module_name] = str(exc)

            _log(
                f"FAILED to discover {module_name}.py: {exc}"
            )
            traceback.print_exc()

    return discovered


def _initialize_node_groups():
    """Initialize all discovered node groups after add-on registration."""
    _GROUPS.clear()
    _DISCOVERY_ERRORS.clear()

    discovered = _discover_group_factories()

    for group_name, module_name, factory in discovered:
        try:
            _log(f"Creating or updating '{group_name}'...")
            group = factory()

            if group is None:
                raise RuntimeError(
                    f"Factory for '{group_name}' returned None."
                )

            _log(f"Validating '{group_name}'...")

            if getattr(group, "bl_idname", None) != "ShaderNodeTree":
                raise RuntimeError(
                    f"Factory returned an incompatible node tree: "
                    f"{getattr(group, 'bl_idname', 'Unknown')}"
                )

            if group.name != group_name:
                raise RuntimeError(
                    f"Expected group '{group_name}', "
                    f"but received '{group.name}'."
                )

            _GROUPS[group_name] = group

            _log(f"READY: {group_name}")

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: {exc}"
            )

            _DISCOVERY_ERRORS[module_name] = error_message

            _log(
                f"FAILED to initialize '{group_name}' "
                f"from {module_name}.py"
            )

            _log(f"Exception: {error_message}")

            traceback.print_exc()

    _log(
        f"Initialization complete: "
        f"{len(_GROUPS)} node group(s) available, "
        f"{len(_DISCOVERY_ERRORS)} failure(s)."
    )

    return None


def register_node_group_library():
    """Schedule node-group initialization after add-on registration."""
    if not bpy.app.timers.is_registered(_initialize_node_groups):
        bpy.app.timers.register(
            _initialize_node_groups,
            first_interval=0.1,
        )


def unregister_node_group_library():
    """Cancel initialization and clear runtime references."""
    if bpy.app.timers.is_registered(_initialize_node_groups):
        bpy.app.timers.unregister(_initialize_node_groups)

    _GROUPS.clear()
    _DISCOVERY_ERRORS.clear()


class NODE_MT_sequenced_bake_group_library(Menu):
    """Menu containing all successfully initialized node groups."""

    bl_label = "Node Group Library"
    bl_idname = "NODE_MT_sequenced_bake_group_library"

    def draw(self, context):
        layout = self.layout

        if not _GROUPS:
            layout.label(
                text="No node groups available",
                icon="INFO",
            )

            if _DISCOVERY_ERRORS:
                layout.label(
                    text=f"{len(_DISCOVERY_ERRORS)} loading error(s)",
                    icon="ERROR",
                )

            return

        for group_name in sorted(_GROUPS):
            operator = layout.operator(
                SequencedBakeNodeGroupOperator.bl_idname,
                text=group_name,
                icon="NODETREE",
            )

            operator.group_name = group_name


class SequencedBakeNodeGroupOperator(Operator):
    """Insert a library node group into the active shader tree."""

    bl_idname = "node.sequenced_bake_add_library_group"
    bl_label = "Add Sequenced Bake Node Group"
    bl_options = {"REGISTER", "UNDO"}

    group_name: StringProperty(
        name="Node Group Name",
    )

    @classmethod
    def poll(cls, context):
        space = getattr(context, "space_data", None)

        return bool(
            space
            and space.type == "NODE_EDITOR"
            and getattr(space, "tree_type", "") == "ShaderNodeTree"
            and getattr(space, "edit_tree", None) is not None
        )

    def execute(self, context):
        group = bpy.data.node_groups.get(self.group_name)

        if group is None:
            self.report(
                {"ERROR"},
                f"Node group '{self.group_name}' was not found.",
            )
            return {"CANCELLED"}

        try:
            tree = context.space_data.edit_tree

            node = tree.nodes.new("ShaderNodeGroup")
            node.node_tree = group
            node.location = context.space_data.cursor_location

            for existing_node in tree.nodes:
                existing_node.select = False

            node.select = True
            tree.nodes.active = node

            return {"FINISHED"}

        except Exception as exc:
            self.report(
                {"ERROR"},
                f"Could not insert '{self.group_name}': {exc}",
            )
            return {"CANCELLED"}


__all__ = (
    "SequencedBakeNodeGroupOperator",
    "NODE_MT_sequenced_bake_group_library",
    "register_node_group_library",
    "unregister_node_group_library",
)
