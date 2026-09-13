"""Modal operator for Sequenced Bake."""

import os
import time

import bpy

from .processing import (
    bake_frame,
    calculate_sculpt_bounds,
    clear_generated_textures,
    connect_metallic_node,
    connect_occlusion_node,
    create_image_texture,
    restore_material_state,
)


class SequencedBakeOperator(bpy.types.Operator):
    """Bake selected material passes across a frame sequence."""

    bl_idname = "sequenced_bake.bake"
    bl_label = "Sequenced Bake"
    bl_options = {"REGISTER", "UNDO"}

    node_tree_name: bpy.props.StringProperty(
        name="Node Tree",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    node_name: bpy.props.StringProperty(
        name="Node",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def invoke(self, context, event):
        """Validate settings, build the task queue, and start baking."""
        self._timer = None
        self._materials = []
        self._bake_map = {}
        self._frames = []
        self._start_time = time.perf_counter()
        self._last_frame_time = self._start_time
        self._frame_durations = []
        self._total_duration = 0.0
        self._tasks = []
        self._task_index = 0
        self._obj = context.active_object
        self._props = context.scene.sequenced_bake_props
        if self.node_name:
            node = None
            node_tree = None

            # A Shader Node's ``id_data`` is the owning ID (normally the
            # Material), not necessarily the NodeTree itself.  The previous
            # implementation incorrectly assumed ``node_tree_name`` referred
            # to bpy.data.node_groups, which caused material shader nodes to
            # be reported as unresolved.
            if self.node_tree_name:
                material = bpy.data.materials.get(self.node_tree_name)
                if material and material.use_nodes and material.node_tree:
                    node_tree = material.node_tree
                else:
                    node_tree = bpy.data.node_groups.get(self.node_tree_name)

            if node_tree:
                node = node_tree.nodes.get(self.node_name)

            # Prefer the actual node-editor tree as a final fallback. This
            # also supports node trees whose owner is not a Material.
            if node is None:
                space = getattr(context, "space_data", None)
                context_tree = getattr(space, "edit_tree", None) if space else None
                if context_tree:
                    candidate = context_tree.nodes.get(self.node_name)
                    if candidate:
                        node = candidate
                        node_tree = context_tree

            if node and hasattr(node, "bake_props"):
                self._props = node.bake_props
                print(
                    f"Sequenced Bake: using settings from node '{node.name}' "
                    f"in '{node_tree.name if node_tree else 'node tree'}'"
                )
            else:
                self.report({"WARNING"}, "Sequenced Bake node could not be resolved; using scene bake settings")
        self._scene = context.scene
        self._generated_images = []
        self._output_dirs = {}
        self._sculpt_normalization_bounds = None
        self._active_material_state = None
        self._active_material = None
        self._active_image_node = None
        self._active_image = None

        self._props.bake_progress = 0.0
        self._props.bake_status = "Starting bake..."
        self._props.bake_current_material = ""
        self._props.bake_current_type = ""
        self._props.bake_frame_info = ""
        self._props.bake_fps = 0.0
        self._props.bake_estimated_time = "00:00:00.000"

        scene = self._scene
        props = self._props

        if scene.render.engine != "CYCLES":
            self.report({"WARNING"}, "Sequenced Bake requires Cycles render engine")
            return {"CANCELLED"}

        if not props.sequenced_bake_output_path:
            self.report({"ERROR"}, "No output path specified")
            return {"CANCELLED"}

        if not self._obj or self._obj.type != "MESH":
            self.report({"ERROR"}, "Active mesh object required")
            return {"CANCELLED"}

        if not self._obj.active_material:
            self.report({"ERROR"}, "Active object with material required")
            return {"CANCELLED"}

        if props.material_mode == "ALL":
            self._materials = [
                slot.material for slot in self._obj.material_slots if slot.material
            ]
        else:
            self._materials = [self._obj.active_material]

        if not self._materials:
            self.report({"ERROR"}, "No materials found")
            return {"CANCELLED"}

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
            "SCULPT": props.sequenced_bake_sculpt,
        }

        if not any(self._bake_map.values()):
            self.report({"WARNING"}, "No bake types are enabled")
            return {"CANCELLED"}

        if props.sequenced_bake_sculpt:
            if props.sequenced_bake_width > 128 or props.sequenced_bake_height > 128:
                self.report(
                    {"ERROR"},
                    "Second Life sculpt maps cannot exceed 128x128 pixels.",
                )
                return {"CANCELLED"}
            if props.sequenced_bake_width != props.sequenced_bake_height:
                self.report({"ERROR"}, "Second Life sculpt maps must be square.")
                return {"CANCELLED"}
            if props.sequenced_bake_image_format not in {"PNG", "TGA"}:
                self.report(
                    {"ERROR"},
                    "Second Life sculpt maps should be saved as lossless PNG or TGA images.",
                )
                return {"CANCELLED"}

        if props.frame_mode == "CURRENT":
            self._frames = [scene.frame_current]
        else:
            step = max(1, props.frame_step)
            self._frames = list(range(scene.frame_start, scene.frame_end + 1, step))

        if self._bake_map.get("SCULPT"):
            bounds_frame = scene.frame_start if props.frame_mode == "SEQUENCE" else scene.frame_current
            current_frame = scene.frame_current
            scene.frame_set(bounds_frame)
            self._sculpt_normalization_bounds = calculate_sculpt_bounds(self._obj)
            scene.frame_set(current_frame)

        self._build_tasks()
        if not self._tasks:
            self.report({"WARNING"}, "No bake tasks were generated")
            return {"CANCELLED"}

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _build_tasks(self):
        """Build the ordered material, pass, and frame task queue."""
        self._tasks.clear()
        self._output_dirs.clear()

        root = bpy.path.abspath(self._props.sequenced_bake_output_path)
        for material in self._materials:
            for bake_type, enabled in self._bake_map.items():
                if not enabled:
                    continue
                output_dir = os.path.join(
                    root,
                    f"{self._obj.name}_{material.name}_{bake_type}",
                )
                self._output_dirs[(material.name, bake_type)] = output_dir
                self._tasks.extend(
                    (material, bake_type, frame)
                    for frame in self._frames
                )

    def modal(self, context, event):
        """Process one bake task for each timer event."""
        if event.type == "ESC":
            self._cancel(context)
            return {"CANCELLED"}

        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        if self._task_index >= len(self._tasks):
            self.finish(context)
            return {"FINISHED"}

        try:
            self.process_next_task(context)
        except Exception as exc:
            print(f"[Sequenced Bake] Fatal task error: {exc}")
            self.report({"ERROR"}, f"Sequenced Bake failed: {exc}")
            self._cancel(context, failed=True)
            return {"CANCELLED"}

        if context.area:
            context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def process_next_task(self, context):
        """Execute the next bake task and update progress statistics."""
        material, bake_type, frame = self._tasks[self._task_index]
        self._task_index += 1
        task_start = time.perf_counter()

        self._props.bake_current_material = material.name
        self._props.bake_current_type = bake_type
        self._props.bake_frame_info = f"{frame} / {len(self._frames)}"
        self._props.bake_status = "Baking"

        self._scene.frame_set(frame)

        image_node = None
        image = None
        material_state = None

        try:
            if bake_type == "METALLIC":
                material_state = connect_metallic_node(material)
            elif bake_type == "OCCLUSION":
                material_state = connect_occlusion_node(material)

            colorspace = self._props.colorspace
            if bake_type in {"NORMAL", "ROUGHNESS", "METALLIC", "OCCLUSION"}:
                colorspace = "Non-Color"

            image_node, image = create_image_texture(
                material=material,
                name=f"{self._obj.name}_{material.name}_{bake_type}_{frame}",
                width=self._props.sequenced_bake_width,
                height=self._props.sequenced_bake_height,
                alpha=self._props.sequence_is_alpha,
                float_buffer=self._props.sequence_use_float,
                interpolation=self._props.interpolation,
                projection=self._props.projection,
                extension=self._props.extension,
                colorspace=colorspace,
                file_format=self._props.sequenced_bake_image_format,
            )
            self._generated_images.append(image)
            self._active_material = material
            self._active_material_state = material_state
            self._active_image_node = image_node
            self._active_image = image

            output_dir = self._output_dirs[(material.name, bake_type)]
            os.makedirs(output_dir, exist_ok=True)

            bake_frame(
                bake_type=bake_type,
                props=self._props,
                frame=frame,
                obj=self._obj,
                mat=material,
                image_node=image_node,
                image=image,
                output_dir=output_dir,
                sculpt_bounds=self._sculpt_normalization_bounds,
            )
        finally:
            if image_node is not None:
                try:
                    if image_node.name in material.node_tree.nodes:
                        material.node_tree.nodes.remove(image_node)
                except (ReferenceError, RuntimeError) as exc:
                    print(f"[Sequenced Bake] Failed to remove temporary image node: {exc}")

            if material_state is not None:
                try:
                    restore_material_state(material, material_state)
                except Exception as exc:
                    print(
                        f"[Sequenced Bake] Failed to restore material '{material.name}': {exc}"
                    )

            self._active_material = None
            self._active_material_state = None
            self._active_image_node = None
            self._active_image = None

        duration = time.perf_counter() - task_start
        self._frame_durations.append(duration)
        self._total_duration += duration

        self._props.bake_fps = self.get_effective_fps()
        self._props.bake_progress = self.get_progress()

        remaining_tasks = len(self._tasks) - self._task_index
        eta_seconds = self.get_effective_task_duration() * remaining_tasks
        self._props.bake_estimated_time = self.format_time(eta_seconds)
        self._props.bake_status = self.get_status_text()

    def get_effective_task_duration(self):
        """Return a stable average duration for completed tasks."""
        if not self._frame_durations:
            return 0.0
        return self._total_duration / len(self._frame_durations)

    def get_effective_fps(self):
        """Return completed bake tasks per second."""
        average = self.get_effective_task_duration()
        return 1.0 / average if average > 0.0 else 0.0

    @staticmethod
    def format_time(seconds):
        """Format seconds as HH:MM:SS.mmm or MM:SS.mmm."""
        if seconds is None or seconds < 0:
            return "00:00:00.000"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{remaining:06.3f}"
        return f"{minutes:02d}:{remaining:06.3f}"

    def get_progress(self):
        """Return completed-task progress in the range 0.0 to 1.0."""
        if not self._tasks:
            return 0.0
        return min(1.0, self._task_index / len(self._tasks))

    def get_status_text(self):
        """Return the current bake status."""
        return "Baking" if self._task_index < len(self._tasks) else "Finalizing"

    def _remove_timer(self, context):
        """Remove the modal timer if one is active."""
        if self._timer is not None:
            try:
                context.window_manager.event_timer_remove(self._timer)
            except RuntimeError as exc:
                print(f"[Sequenced Bake] Failed to remove modal timer: {exc}")
            self._timer = None

    def finish(self, context):
        """Finalize a successful bake operation."""
        self._remove_timer(context)
        clear_generated_textures(self._props, self._generated_images)
        self._props.bake_progress = 1.0
        self._props.bake_status = "Completed"
        self._props.bake_estimated_time = "00:00:00.000"
        self.report({"INFO"}, "Sequenced Bake completed")

    def _cancel(self, context, failed=False):
        """Cancel the bake operation and restore temporary state."""
        if self._active_material and self._active_material_state:
            try:
                restore_material_state(
                    self._active_material,
                    self._active_material_state,
                )
            except Exception as exc:
                print(f"[Sequenced Bake] Failed to restore active material: {exc}")

        self._remove_timer(context)
        clear_generated_textures(self._props, self._generated_images)
        self._props.bake_status = "Failed" if failed else "Cancelled"
        self.report(
            {"ERROR" if failed else "WARNING"},
            "Sequenced Bake failed" if failed else "Sequenced Bake cancelled",
        )
