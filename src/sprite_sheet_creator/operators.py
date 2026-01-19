import bpy
import os
from bpy.types import Operator
from . import processing


class OBJECT_OT_CreateSpriteSheet(Operator):
    bl_idname = "object.create_sprite_sheet"
    bl_label = "Generate Sprite Sheet"
    bl_description = "Generate a sprite sheet from the selected source"

    _timer = None
    _subdirs = None
    _current_index = 0
    _props = None

    # ------------------------------------------------------------------
    # Entry Point
    # ------------------------------------------------------------------

    def execute(self, context):
        self._props = context.scene.sprite_sheet_props

        if self._props.source_type == 'DIRECTORY':
            return self._execute_directory(context)

        if self._props.source_type == 'VSE':
            return self._execute_vse(context)

        if self._props.source_type == 'COMPOSITOR':
            return self._execute_compositor(context)

        self.report({'ERROR'}, "Unsupported source type")
        return {'CANCELLED'}

    # ------------------------------------------------------------------
    # DIRECTORY (Modal)
    # ------------------------------------------------------------------

    def _execute_directory(self, context):
        directory = bpy.path.abspath(self._props.directory)

        if not directory or not os.path.isdir(directory):
            self.report({'ERROR'}, f"Invalid or missing directory: {directory}")
            return {'CANCELLED'}

        # Detect subdirectories
        subdirs = [
            os.path.join(directory, d)
            for d in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, d))
        ]

        if not subdirs:
            subdirs = [directory]

        self._subdirs = subdirs
        self._current_index = 0

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        self.report({'INFO'}, f"Starting sprite sheet generation for {len(subdirs)} subdirectory(ies)")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'ESC':
            self._cancel(context)
            self.report({'INFO'}, "Sprite sheet generation cancelled")
            return {'CANCELLED'}

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        if self._current_index >= len(self._subdirs):
            self._finish(context)
            self.report({'INFO'}, "Sprite sheets created successfully")
            return {'FINISHED'}

        subdir = self._subdirs[self._current_index]
        self._process_directory(subdir)
        self._current_index += 1

        return {'PASS_THROUGH'}

    def _process_directory(self, directory):
        try:
            images = processing.load_directory_images(
                directory,
                start_frame=self._props.start_frame,
                end_frame=self._props.end_frame,
                reversed_order=self._props.is_reversed,
                report_fn=self.report,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load images from {directory}: {e}")
            return

        if not images:
            self.report({'WARNING'}, f"No images found in directory: {directory}")
            return

        output_name = os.path.basename(directory)
        try:
            processing.process_images(
                images,
                self._props,
                output_name,
                report_fn=self.report,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to process sprite sheet for {directory}: {e}")

    # ------------------------------------------------------------------
    # VSE
    # ------------------------------------------------------------------

    def _execute_vse(self, context):
        if not self._props.vse_output_path:
            self.report({'ERROR'}, "VSE output path is required")
            return {'CANCELLED'}

        try:
            images = processing.load_vse_frames(
                context,
                self._props,
                report_fn=self.report,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load VSE frames: {e}")
            return {'CANCELLED'}

        if self._props.is_reversed:
            images.reverse()

        try:
            processing.process_images(
                images,
                self._props,
                output_name="VSE",
                report_fn=self.report,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to process VSE sprite sheet: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    # ------------------------------------------------------------------
    # COMPOSITOR
    # ------------------------------------------------------------------

    def _execute_compositor(self, context):
        if not self._props.compositor_output_path:
            self.report({'ERROR'}, "Compositor output path is required")
            return {'CANCELLED'}

        try:
            images = processing.load_compositor_frames(
                context,
                self._props,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load compositor frames: {e}")
            return {'CANCELLED'}

        if self._props.is_reversed:
            images.reverse()

        try:
            processing.process_images(
                images,
                self._props,
                output_name="Compositor",
                report_fn=self.report,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to process compositor sprite sheet: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _finish(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def _cancel(self, context):
        self._finish(context)
        self._subdirs = None
        self._current_index = 0
