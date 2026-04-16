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

import bpy
import os
import time

from .processing import (
    clear_generated_textures,
    connect_metallic_node,
    connect_occlusion_node,
    reconnect_node,
    create_image_texture,
    bake_frame,
)


class SequencedBakeOperator(bpy.types.Operator):
    """
    Modal operator that performs sequenced texture baking across frames,
    materials, and bake types.

    This operator constructs a task queue of (material, bake_type, frame)
    tuples and processes them incrementally using Blender's modal timer
    system. It ensures non-blocking execution while maintaining UI
    responsiveness.

    The operator handles:
    - Task queue generation across materials, bake types, and frame range
    - Frame-by-frame baking execution
    - Temporary node graph modification (e.g., Metallic baking)
    - Progress tracking, FPS calculation, and ETA estimation
    - Resource cleanup on completion or cancellation

    Instance Attributes:
        _timer (bpy.types.Timer):
            Timer instance used to drive modal updates.

        _materials (list[bpy.types.Material]):
            List of materials included in the bake operation.

        _bake_map (dict[str, bool]):
            Mapping of bake types to their enabled/disabled state.

        _frames (list[int]):
            List of frame numbers to process.

        _start_time (float):
            Timestamp marking when the bake operation started.

        _last_frame_time (float):
            Timestamp of the last processed frame.

        _frame_durations (list[float]):
            Collection of per-task execution durations used for
            performance metrics.

        _tasks (list[tuple[bpy.types.Material, str, int]]):
            Ordered queue of bake tasks.

        _task_index (int):
            Current index within the task queue.

        _obj (bpy.types.Object):
            Target object whose materials are being baked.

        _props (SequencedBakeProperties):
            Reference to the add-on property group containing user settings.

        _scene (bpy.types.Scene):
            Active scene used during baking.
    """

    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _materials = None
    _bake_map = None
    _frames = None
    _start_time = None
    _last_frame_time = None
    _frame_durations = []
    _tasks = []
    _task_index = 0
    _obj = None
    _props = None
    _scene = None

    def invoke(self, context, event):
        """
                Initializes the bake operation and starts the modal execution loop.

                Performs validation checks, prepares materials and bake configuration,
                constructs the task queue, and registers a timer for incremental
                processing.

                Validation includes:
                - Ensuring Cycles render engine is active
                - Verifying output path is set
                - Confirming an active object and material exist

                Also initializes progress tracking and timing metrics.

                Args:
                    context (bpy.types.Context): Current Blender context.
                    event (bpy.types.Event): Event that triggered the operator.

                Returns:
                    set[str]: {'RUNNING_MODAL'} if initialization succeeds,
                              {'CANCELLED'} if validation fails.
                """

        self._scene = context.scene
        self._props = self._scene.sequenced_bake_props
        self._obj = context.active_object
        self._props.bake_progress = 0.0
        self._props.bake_status = "Starting bake..."
        self._start_time = time.time()

        # validation (moved from execute)
        scene = self._scene
        props = self._props

        if scene.render.engine != 'CYCLES':
            self.report({'WARNING'}, "Sequenced Bake requires Cycles render engine")
            return {'CANCELLED'}

        if not props.sequenced_bake_output_path:
            self.report({'ERROR'}, "No output path specified")
            return {'CANCELLED'}

        if not self._obj or not self._obj.active_material:
            self.report({'ERROR'}, "Active object with material required")
            return {'CANCELLED'}

        # materials
        if props.bake_mode == 'ALL':
            self._materials = [
                slot.material for slot in self._obj.material_slots if slot.material
            ]
        else:
            self._materials = [self._obj.active_material]

        if not self._materials:
            self.report({'ERROR'}, "No materials found")
            return {'CANCELLED'}

        # bake map (same as before)
        self._bake_map = {
            "NORMAL": props.sequenced_bake_normal,
            "ROUGHNESS": props.sequenced_bake_roughness,
            "GLOSSY": props.sequenced_bake_glossy,
            "EMIT": props.sequenced_bake_emission,
            "AO": props.sequenced_bake_ambient_occlusion,
            "SHADOW": props.sequenced_bake_shadow,
            "POSITION": props.sequenced_bake_position,
            "UV": props.sequenced_bake_uv,
            "ENVIRONMENT": props.sequenced_bake_environment,
            "DIFFUSE": props.sequenced_bake_diffuse,
            "TRANSMISSION": props.sequenced_bake_transmission,
            "COMBINED": props.sequenced_bake_combined,
            "METALLIC": props.sequenced_bake_metallic,
            "OCCLUSION": props.sequenced_bake_occlusion,
        }

        self._frames = list(range(scene.frame_start, scene.frame_end + 1))

        # build task queue
        self._build_tasks()

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def _build_tasks(self):
        """
        Constructs the internal bake task queue.

        Iterates over all selected materials, enabled bake types, and
        frame range to generate a flattened list of tasks. Each task is
        represented as a tuple:

            (material, bake_type, frame)

        This queue is processed sequentially during modal execution.

        Side Effects:
            - Populates self._tasks with ordered bake operations.
        """

        self._tasks = []

        for mat in self._materials:
            for bake_type, enabled in self._bake_map.items():
                if not enabled:
                    continue

                for frame in self._frames:
                    self._tasks.append((mat, bake_type, frame))

    def modal(self, context, event):
        """
        Handles modal event processing for the bake operation.

        This method is repeatedly called by Blender's event system.
        It processes bake tasks incrementally using a timer event,
        allowing the UI to remain responsive.

        Behavior:
        - ESC key cancels the operation
        - TIMER events trigger processing of the next task
        - Completes when all tasks are processed

        Args:
            context (bpy.types.Context): Current Blender context.
            event (bpy.types.Event): Incoming event.

        Returns:
            set[str]: Operator state:
                - {'RUNNING_MODAL'} while processing
                - {'FINISHED'} when complete
                - {'CANCELLED'} if interrupted
                - {'PASS_THROUGH'} for unrelated events
        """

        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        if self._task_index >= len(self._tasks):
            self.finish(context)
            return {'FINISHED'}

        self.process_next_task(context)

        if context.area:
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def process_next_task(self, context):
        """
        Executes the next bake task in the queue.

        This method performs a full bake cycle for a single task:
        - Updates UI state (material, type, frame)
        - Sets the scene frame
        - Prepares material nodes (if required)
        - Creates an image texture target
        - Executes the bake operation
        - Restores node state (if modified)
        - Records timing and updates performance metrics

        Also updates:
        - Progress percentage
        - Estimated time remaining (ETA)
        - Effective FPS

        Args:
            context (bpy.types.Context): Current Blender context.

        Side Effects:
            - Advances task index
            - Modifies scene state
            - Writes baked image to disk
            - Updates UI-bound properties
        """

        props = self._props

        frame_start_time = time.time()

        mat, bake_type, frame = self._tasks[self._task_index]
        self._task_index += 1

        # UI STATE UPDATE
        self._props.bake_current_material = mat.name
        self._props.bake_current_type = bake_type
        self._props.bake_frame_info = f"{frame} / {len(self._frames)}"
        self._props.bake_status = "Baking"

        # FRAME SETUP
        scene = self._scene
        scene.frame_set(frame)
        bpy.context.view_layer.update()

        # METALLIC NODE PREP
        if bake_type == "METALLIC":
            connect_metallic_node(mat)

        # Occlusion  NODE PREP
        if bake_type == "OCCLUSION":
            connect_occlusion_node(mat)

        bake_dir = os.path.join(
            bpy.path.abspath(props.sequenced_bake_output_path),
            f"{self._obj.name}_{mat.name}_{bake_type}"
        )
        os.makedirs(bake_dir, exist_ok=True)

        image_node, image = create_image_texture(
            material=mat,
            name=f"{self._obj.name}_{mat.name}_{bake_type}_{frame}",
            width=props.sequenced_bake_width,
            height=props.sequenced_bake_height,
            alpha=props.sequence_is_alpha,
            float_buffer=props.sequence_use_float,
            interpolation=props.interpolation,
            projection=props.projection,
            extension=props.extension,
            colorspace=props.colorspace,
        )

        # BAKING
        bake_frame(
            bake_type=bake_type,
            props=props,
            frame=frame,
            obj=self._obj,
            mat=mat,
            image_node=image_node,
            image=image,
            output_dir=bake_dir,
        )

        if bake_type == "METALLIC":
            reconnect_node(mat)

        if bake_type == "OCCLUSION":
            reconnect_node(mat)

        # FRAME TIMING 
        frame_end_time = time.time()
        frame_duration = frame_end_time - frame_start_time

        self._frame_durations.append(frame_duration)

        # FPS
        if self._frame_durations:
            avg_frame_time = sum(self._frame_durations) / len(self._frame_durations)
            if avg_frame_time > 0:
                self._props.bake_fps = round(1.0 / avg_frame_time, 3)
            else:
                self._props.bake_fps = 0.0

        # PROGRESS
        self._props.bake_progress = self.get_progress()

        # ETA (frame-based)
        progress = self._task_index / len(self._tasks)

        if self._frame_durations and progress > 0:
            avg_frame = sum(self._frame_durations) / len(self._frame_durations)
            remaining_tasks = len(self._tasks) - self._task_index

            eta_seconds = avg_frame * remaining_tasks

            # formatted HH:MM:SS.mmm
            self._props.bake_estimated_time = self.format_time(eta_seconds)
        else:
            self._props.bake_estimated_time = "00:00:00.000"

        # STATUS (clean lifecycle only)
        self._props.bake_status = self.get_status_text()

    def get_effective_fps(self):
        """
        Calculates the effective frames-per-second of the bake process.

        Uses the average duration of processed frames to estimate
        throughput.

        Returns:
            float: Calculated FPS value. Returns 0.0 if insufficient data
            or invalid timing values are present.
        """

        if not self._frame_durations:
            return 0.0

        avg = sum(self._frame_durations) / len(self._frame_durations)

        if avg <= 0:
            return 0.0

        return 1.0 / avg

    def format_time(self, seconds: float) -> str:
        """
        Formats a time duration into a human-readable string.

        Converts seconds into either:
        - HH:MM:SS.mmm format (if duration >= 1 hour)
        - MM:SS.mmm format (otherwise)

        Args:
            seconds (float): Time duration in seconds.

        Returns:
            str: Formatted time string. Returns "00:00:00" for invalid input.
        """

        if seconds is None or seconds < 0:
            return "00:00:00"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        else:
            return f"{minutes:02d}:{secs:06.3f}"

    def get_progress(self):
        """
        Computes overall progress of the bake operation.

        Progress is calculated as the ratio of completed tasks
        to total tasks.

        Returns:
            float: Progress value in range [0.0, 1.0].
                   Returns 0.0 if no tasks exist.
        """

        if not self._tasks:
            return 0.0
        return self._task_index / len(self._tasks)

    def get_status_text(self):
        """
        Determines the current status label for the bake process.

        Returns:
            str: Status string:
                - "Idle" if no tasks exist
                - "Baking" while tasks are being processed
        """

        if not self._tasks:
            return "Idle"

        return "Baking"

    def finish(self, context):
        """
        Finalizes the bake operation after all tasks are completed.

        Responsibilities:
        - Stops the modal timer
        - Cleans up generated textures (if enabled)
        - Updates UI state to completed
        - Reports completion to the user

        Args:
            context (bpy.types.Context): Current Blender context.

        Side Effects:
            - Removes timer from window manager
            - Updates bake progress and status
        """

        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        clear_generated_textures(self._props)

        self._props.bake_progress = 1.0
        self._props.bake_status = "Completed"
        self.report({'INFO'}, "Sequenced Bake completed")

    def cancel(self, context):
        """
        Cancels the bake operation prematurely.

        Performs cleanup similar to finish(), but sets the status
        to indicate cancellation instead of completion.

        Args:
            context (bpy.types.Context): Current Blender context.

        Side Effects:
            - Stops modal timer
            - Cleans up generated textures
            - Updates UI status to "Cancelled"
        """

        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        clear_generated_textures(self._props)
        self._props.bake_status = "Cancelled"
        self.report({'WARNING'}, "Sequenced Bake cancelled")
