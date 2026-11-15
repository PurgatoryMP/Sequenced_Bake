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


import os
import bpy
from bpy.types import Operator
from . import processing


class OBJECT_OT_CreateSpriteSheet(Operator):
    """Generate a sprite sheet from a directory, VSE, or compositor."""

    bl_idname = "object.create_sprite_sheet"
    bl_label = "Generate Sprite Sheet"
    bl_description = "Generate a sprite sheet from the selected source"

    def execute(self, context):
        """Validate the source and begin sprite-sheet generation."""
        self._timer = None
        self._subdirs = []
        self._current_index = 0
        self._props = context.scene.sprite_sheet_props

        if self._props.source_type == "DIRECTORY":
            return self._execute_directory(context)
        if self._props.source_type == "VSE":
            return self._execute_vse(context)
        if self._props.source_type == "COMPOSITOR":
            return self._execute_compositor(context)

        self.report({"ERROR"}, "Unsupported source type")
        return {"CANCELLED"}

    def _execute_directory(self, context):
        """Process one source directory per modal timer event."""
        directory = bpy.path.abspath(self._props.directory)
        if not directory or not os.path.isdir(directory):
            self.report({"ERROR"}, f"Invalid or missing directory: {directory}")
            return {"CANCELLED"}

        try:
            subdirs = [
                os.path.join(directory, name)
                for name in sorted(os.listdir(directory))
                if os.path.isdir(os.path.join(directory, name))
            ]
        except OSError as exc:
            self.report({"ERROR"}, f"Failed to enumerate directory: {exc}")
            return {"CANCELLED"}

        self._subdirs = subdirs or [directory]
        self._current_index = 0

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        self.report(
            {"INFO"},
            f"Starting sprite sheet generation for {len(self._subdirs)} subdirectory(ies)",
        )
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        """Process the next directory when the modal timer fires."""
        if event.type == "ESC":
            self._cancel(context)
            self.report({"INFO"}, "Sprite sheet generation cancelled")
            return {"CANCELLED"}

        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        if self._current_index >= len(self._subdirs):
            self._finish(context)
            self.report({"INFO"}, "Sprite sheets created successfully")
            return {"FINISHED"}

        directory = self._subdirs[self._current_index]
        self._current_index += 1
        self._process_directory(directory)

        if context.area:
            context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _process_directory(self, directory):
        """Load and process one directory (including per-UDIM sprite sheets)."""
        try:
            udim_groups = processing.load_directory_udim_groups(
                directory,
                start_frame=self._props.start_frame,
                end_frame=self._props.end_frame,
                report_fn=self.report,
            )
        except Exception as exc:
            print(f"[Sprite Sheet Creator] Failed to load '{directory}': {exc}")
            self.report({"ERROR"}, f"Failed to load images from {directory}: {exc}")
            return

        if not udim_groups:
            self.report({"WARNING"}, f"No images found in directory: {directory}")
            return

        base_output_name = os.path.basename(os.path.normpath(directory)) or "SpriteSheet"

        for udim_tile, images in udim_groups.items():
            if not images:
                continue

            sheet_label = (
                f"{base_output_name} (UDIM {udim_tile})"
                if udim_tile is not None
                else base_output_name
            )
            try:
                processing.process_images(
                    images,
                    self._props,
                    base_output_name,
                    report_fn=self.report,
                    udim_tile=udim_tile,
                )
            except Exception as exc:
                print(f"[Sprite Sheet Creator] Failed to process '{sheet_label}': {exc}")
                self.report(
                    {"ERROR"},
                    f"Failed to process sprite sheet for {sheet_label}: {exc}",
                )

    def _execute_vse(self, context):
        """Generate a sprite sheet from rendered VSE frames."""
        if not self._props.vse_output_path:
            self.report({"ERROR"}, "VSE output path is required")
            return {"CANCELLED"}

        try:
            images = processing.load_vse_frames(
                context,
                self._props,
                report_fn=self.report,
            )
            if not images:
                return {"CANCELLED"}
            processing.process_images(
                images,
                self._props,
                output_name="VSE",
                report_fn=self.report,
            )
        except Exception as exc:
            print(f"[Sprite Sheet Creator] VSE generation failed: {exc}")
            self.report({"ERROR"}, f"Failed to process VSE sprite sheet: {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def _execute_compositor(self, context):
        """Generate a sprite sheet from compositor-rendered frames."""
        if not self._props.compositor_output_path:
            self.report({"ERROR"}, "Compositor output path is required")
            return {"CANCELLED"}

        try:
            images = processing.load_compositor_frames(
                context,
                self._props,
                report_fn=self.report,
            )
            if not images:
                return {"CANCELLED"}
            processing.process_images(
                images,
                self._props,
                output_name="Compositor",
                report_fn=self.report,
            )
        except Exception as exc:
            print(f"[Sprite Sheet Creator] Compositor generation failed: {exc}")
            self.report(
                {"ERROR"},
                f"Failed to process compositor sprite sheet: {exc}",
            )
            return {"CANCELLED"}

        return {"FINISHED"}

    def _finish(self, context):
        """Stop the modal timer."""
        if self._timer is not None:
            try:
                context.window_manager.event_timer_remove(self._timer)
            except RuntimeError as exc:
                print(f"[Sprite Sheet Creator] Failed to remove timer: {exc}")
            self._timer = None
        self._subdirs = []
        self._current_index = 0

    def _cancel(self, context):
        """Stop modal processing after cancellation."""
        self._finish(context)


class SPRITESHEET_OT_AddImages(Operator):
    """Open a file browser to select and append images to the list."""

    bl_idname = "spritesheet.add_images"
    bl_label = "Append Images"
    bl_description = "Open a directory and append selected images to the list"
    bl_options = {"REGISTER", "UNDO"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
    filter_image: bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    filter_folder: bpy.props.BoolProperty(default=True, options={"HIDDEN"})

    def invoke(self, context, event):
        props = context.scene.sprite_sheet_props
        if props.directory:
            self.directory = bpy.path.abspath(props.directory)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        from .properties import IMAGE_EXTENSIONS, _get_udim_tile

        props = context.scene.sprite_sheet_props
        has_udims = bool(props.detected_udim_tiles)
        active_udim = (
            int(props.selected_udim_tile)
            if has_udims and props.selected_udim_tile.isdigit()
            else 0
        )

        added_count = 0
        for file_elem in self.files:
            if not file_elem.name:
                continue
            ext = os.path.splitext(file_elem.name)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue

            full_path = os.path.join(self.directory, file_elem.name)
            if not os.path.isfile(full_path):
                continue

            detected_udim = _get_udim_tile(file_elem.name)
            item = props.directory_images.add()
            item.name = file_elem.name
            item.filepath = full_path
            item.udim = detected_udim if detected_udim is not None else active_udim
            added_count += 1

        if added_count == 0:
            self.report({"WARNING"}, "No valid image files were selected")
            return {"CANCELLED"}

        # Sync UDIM tracking if new UDIM tiles were introduced
        all_udims = sorted({item.udim for item in props.directory_images if item.udim != 0})
        if all_udims:
            props.detected_udim_tiles = ",".join(str(u) for u in all_udims)
            if props.selected_udim_tile not in [str(u) for u in all_udims]:
                props.selected_udim_tile = str(all_udims[0])
            active_udim = int(props.selected_udim_tile)
            visible_count = sum(1 for item in props.directory_images if item.udim == active_udim)
        else:
            visible_count = len(props.directory_images)

        props.directory_images_index = len(props.directory_images) - 1
        props.end_frame = max(1, visible_count)
        if props.start_frame > props.end_frame:
            props.start_frame = 1

        self.report({"INFO"}, f"Appended {added_count} image(s)")
        return {"FINISHED"}


class SPRITESHEET_OT_ListAction(Operator):
    """Reorder, reverse, remove, or refresh the directory image item list."""

    bl_idname = "spritesheet.list_action"
    bl_label = "Image List Action"
    bl_description = "Reorder, reverse, remove, or refresh the directory image list"
    bl_options = {"REGISTER", "UNDO"}

    action: bpy.props.EnumProperty(
        items=[
            ("TOP", "Move to Top", "Move selected image to the top of the list"),
            ("UP", "Move Up", "Move selected image up in the list"),
            ("DOWN", "Move Down", "Move selected image down in the list"),
            ("BOTTOM", "Move to Bottom", "Move selected image to the bottom of the list"),
            ("REVERSE", "Reverse Order", "Reverse the order of all images in the list"),
            ("REMOVE", "Remove Image", "Remove the selected image from the list"),
            ("REFRESH", "Refresh", "Reload images from the selected directory"),
        ]
    )

    def execute(self, context):
        from .properties import populate_directory_image_list

        props = context.scene.sprite_sheet_props
        items = props.directory_images
        idx = props.directory_images_index

        if self.action == "REFRESH":
            populate_directory_image_list(props, context, preserve_order=True)
            return {"FINISHED"}

        has_udims = bool(props.detected_udim_tiles)
        selected_udim = (
            int(props.selected_udim_tile)
            if has_udims and props.selected_udim_tile.isdigit()
            else 0
        )

        # Indices in directory_images belonging to the active UDIM (or all items if non-UDIM)
        visible_indices = [
            i for i, item in enumerate(items)
            if not has_udims or item.udim == selected_udim
        ]

        if idx not in visible_indices:
            return {"CANCELLED"}

        pos = visible_indices.index(idx)

        if self.action == "REMOVE":
            items.remove(idx)

            # Recompute visible items for the active UDIM after deletion
            remaining_visible = [
                i for i, item in enumerate(items)
                if not has_udims or item.udim == selected_udim
            ]

            if remaining_visible:
                next_pos = min(pos, len(remaining_visible) - 1)
                props.directory_images_index = remaining_visible[next_pos]
            else:
                props.directory_images_index = max(0, min(idx, len(items) - 1))

            # Clean up UDIM dropdown if no items remain for that tile
            if has_udims:
                remaining_udims = sorted({item.udim for item in items if item.udim != 0})
                if remaining_udims:
                    props.detected_udim_tiles = ",".join(str(u) for u in remaining_udims)
                    if props.selected_udim_tile not in [str(u) for u in remaining_udims]:
                        props.selected_udim_tile = str(remaining_udims[0])
                else:
                    props.detected_udim_tiles = ""

            new_count = (
                sum(1 for item in items if item.udim == int(props.selected_udim_tile))
                if props.detected_udim_tiles and props.selected_udim_tile.isdigit()
                else len(items)
            )
            props.end_frame = max(1, new_count)
            if props.start_frame > props.end_frame:
                props.start_frame = 1

            return {"FINISHED"}

        if len(visible_indices) < 2:
            return {"CANCELLED"}

        if self.action == "TOP" and pos > 0:
            target_idx = visible_indices[0]
            items.move(idx, target_idx)
            props.directory_images_index = target_idx

        elif self.action == "UP" and pos > 0:
            target_idx = visible_indices[pos - 1]
            items.move(idx, target_idx)
            props.directory_images_index = target_idx

        elif self.action == "DOWN" and pos < len(visible_indices) - 1:
            target_idx = visible_indices[pos + 1]
            items.move(idx, target_idx)
            props.directory_images_index = target_idx

        elif self.action == "BOTTOM" and pos < len(visible_indices) - 1:
            target_idx = visible_indices[-1]
            items.move(idx, target_idx)
            props.directory_images_index = target_idx

        elif self.action == "REVERSE":
            desired_names = [items[i].name for i in reversed(visible_indices)]

            for slot_pos, target_idx in enumerate(visible_indices):
                desired_name = desired_names[slot_pos]
                current_idx = next(
                    i for i in visible_indices[slot_pos:]
                    if items[i].name == desired_name
                )
                if current_idx != target_idx:
                    items.move(current_idx, target_idx)

            props.directory_images_index = visible_indices[len(visible_indices) - 1 - pos]

        return {"FINISHED"}