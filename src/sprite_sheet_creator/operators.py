"""Operators for Sprite Sheet Creator."""

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
        """Load and process one directory, reporting errors to the console/UI."""
        try:
            images = processing.load_directory_images(
                directory,
                start_frame=self._props.start_frame,
                end_frame=self._props.end_frame,
                reversed_order=self._props.is_reversed,
                report_fn=self.report,
            )
        except Exception as exc:
            print(f"[Sprite Sheet Creator] Failed to load '{directory}': {exc}")
            self.report({"ERROR"}, f"Failed to load images from {directory}: {exc}")
            return

        if not images:
            self.report({"WARNING"}, f"No images found in directory: {directory}")
            return

        output_name = os.path.basename(os.path.normpath(directory)) or "SpriteSheet"
        try:
            processing.process_images(
                images,
                self._props,
                output_name,
                report_fn=self.report,
            )
        except Exception as exc:
            print(f"[Sprite Sheet Creator] Failed to process '{directory}': {exc}")
            self.report(
                {"ERROR"},
                f"Failed to process sprite sheet for {directory}: {exc}",
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
