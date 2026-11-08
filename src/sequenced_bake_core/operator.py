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
import time

import bpy
import bmesh
import numpy as np

from .processing import (
    bake_frame,
    clear_generated_textures,
    connect_metallic_node,
    connect_occlusion_node,
    create_image_texture,
    restore_material_state,
)



class SEQUENCED_BAKE_OT_udim_add(bpy.types.Operator):
    """Add the next available UDIM tile immediately."""

    bl_idname = "sequenced_bake.udim_add"
    bl_label = "Add UDIM Tile"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.sequenced_bake_props

        existing_tiles = {
            tile.tile_index
            for tile in props.udim_tiles
        }

        # Find the first available valid UDIM index.
        tile_number = 1001

        while tile_number in existing_tiles and tile_number <= 2000:
            tile_number += 1

        if tile_number > 2000:
            self.report(
                {'ERROR'},
                "No available UDIM indexes remain."
            )
            return {'CANCELLED'}

        new_tile = props.udim_tiles.add()
        new_tile.name = str(tile_number)
        new_tile.tile_index = tile_number

        props.udim_active_index = len(props.udim_tiles) - 1

        print(
            f"[Sequenced Bake] Added UDIM tile {tile_number}"
        )

        return {'FINISHED'}


class SEQUENCED_BAKE_OT_udim_remove(bpy.types.Operator):
    """Remove the currently selected UDIM tile."""

    bl_idname = "sequenced_bake.udim_remove"
    bl_label = "Remove UDIM Tile"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.sequenced_bake_props

        if not props.udim_tiles:
            props.udim_active_index = 0
            return {'CANCELLED'}

        index = props.udim_active_index

        if not 0 <= index < len(props.udim_tiles):
            return {'CANCELLED'}

        removed_number = props.udim_tiles[index].tile_index

        props.udim_tiles.remove(index)

        if props.udim_tiles:
            props.udim_active_index = min(
                index,
                len(props.udim_tiles) - 1
            )
        else:
            props.udim_active_index = 0

        print(
            f"[Sequenced Bake] Removed UDIM tile {removed_number}"
        )

        return {'FINISHED'}
        


def diagnose_udim_uv_layout(obj, udim_tiles):
    """
    Inspect the active and render UV maps using Blender 5.2's
    current UV attribute API.

    Reports the UV tile occupied by each polygon and checks
    whether the requested image contains those tiles.
    """

    import math

    if not obj or obj.type != 'MESH':
        raise RuntimeError(
            "UDIM diagnostics require an active mesh object."
        )

    mesh = obj.data

    active_uv = mesh.uv_layers.active
    render_uv = mesh.uv_layers.active_render

    print("\n========== SEQUENCED BAKE UDIM DIAGNOSTICS ==========")
    print(f"Object: {obj.name}")
    print(f"Mesh: {mesh.name}")
    print(f"Mesh Vertices: {len(mesh.vertices)}")
    print(f"Mesh Loops: {len(mesh.loops)}")
    print(f"Mesh Polygons: {len(mesh.polygons)}")
    print(f"UV Maps: {len(mesh.uv_layers)}")

    if not active_uv:
        print("[ERROR] No active UV map.")
        print("=====================================================\n")
        return

    print(f"Active UV Map: {active_uv.name}")
    print(f"Active UV Coordinates: {len(active_uv.uv)}")
    print(
        "Render UV Map: "
        f"{render_uv.name if render_uv else 'None'}"
    )

    uv_layer = render_uv if render_uv else active_uv

    if len(uv_layer.uv) != len(mesh.loops):
        print(
            "[ERROR] UV coordinate count does not match "
            "the mesh loop count."
        )
        print("=====================================================\n")
        return

    requested_tiles = {
        int(tile.tile_index)
        for tile in udim_tiles
    }

    print(f"Requested UDIM Tiles: {sorted(requested_tiles)}")

    def get_udim_number(u, v):
        tile_u = math.floor(u)
        tile_v = math.floor(v)

        if not (0 <= tile_u <= 9 and 0 <= tile_v <= 99):
            return None

        return 1001 + tile_u + (tile_v * 10)

    tile_face_counts = {}
    invalid_faces = []
    crossing_faces = []

    for polygon in mesh.polygons:

        coords = [
            uv_layer.uv[index].vector.copy()
            for index in polygon.loop_indices
        ]

        if not coords:
            continue

        # Determine the polygon's UV center.
        center_u = sum(uv.x for uv in coords) / len(coords)
        center_v = sum(uv.y for uv in coords) / len(coords)

        tile_number = get_udim_number(center_u, center_v)

        if tile_number is None:
            invalid_faces.append(polygon.index)
            continue

        tile_face_counts[tile_number] = (
            tile_face_counts.get(tile_number, 0) + 1
        )

        # Detect polygons whose UV corners occupy
        # more than one UDIM tile.
        corner_tiles = {
            get_udim_number(uv.x, uv.y)
            for uv in coords
        }

        corner_tiles.discard(None)

        if len(corner_tiles) > 1:
            crossing_faces.append(
                (polygon.index, sorted(corner_tiles))
            )

    print("\nUV Face Distribution:")

    for tile_number, count in sorted(tile_face_counts.items()):

        status = (
            "OK"
            if tile_number in requested_tiles
            else "MISSING FROM IMAGE"
        )

        print(
            f"  UDIM {tile_number}: "
            f"{count} faces [{status}]"
        )

    missing_tiles = (
        set(tile_face_counts.keys()) - requested_tiles
    )

    unused_tiles = (
        requested_tiles - set(tile_face_counts.keys())
    )

    if missing_tiles:
        print("\n[ERROR] UVs occupy tiles missing from the image:")

        for tile_number in sorted(missing_tiles):
            print(f"  Missing UDIM: {tile_number}")

    if unused_tiles:
        print("\n[INFO] Requested tiles without UV faces:")

        for tile_number in sorted(unused_tiles):
            print(f"  Unused UDIM: {tile_number}")

    if crossing_faces:
        print("\n[WARNING] Faces crossing UDIM boundaries:")

        for face_index, tiles in crossing_faces[:30]:
            print(f"  Face {face_index}: {tiles}")

    if invalid_faces:
        print("\n[ERROR] Faces outside supported UDIM coordinates:")

        for face_index in invalid_faces[:30]:
            print(f"  Face {face_index}")

    if not tile_face_counts:
        print("\n[ERROR] No UV faces could be classified.")

    if not missing_tiles and tile_face_counts:
        print("\n[OK] All UV-occupied tiles exist in the image.")

    print("=====================================================\n")



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

            if self.node_tree_name:
                material = bpy.data.materials.get(self.node_tree_name)
                if material and material.use_nodes and material.node_tree:
                    node_tree = material.node_tree
                else:
                    node_tree = bpy.data.node_groups.get(self.node_tree_name)

            if node_tree:
                node = node_tree.nodes.get(self.node_name)

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
        
        if props.image_source == 'TILED':
            diagnose_udim_uv_layout(
                self._obj,
                props.udim_tiles
            )

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

        if scene.render.engine != "CYCLES":
            self.report({"WARNING"}, "Sequenced Bake requires Cycles render engine for material passes")
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
            self._materials = [self._obj.active_material] if self._obj.active_material else []

        if not self._materials:
            self.report({"ERROR"}, "No materials found")
            return {"CANCELLED"}

        if not any(self._bake_map.values()):
            self.report({"WARNING"}, "No bake types are enabled")
            return {"CANCELLED"}

        if props.frame_mode == "CURRENT":
            self._frames = [scene.frame_current]
        else:
            step = max(1, props.frame_step)
            self._frames = list(range(scene.frame_start, scene.frame_end + 1, step))

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
                mat_name = material.name if material else "NoMaterial"
                output_dir = os.path.join(
                    root,
                    f"{self._obj.name}_{mat_name}_{bake_type}",
                )
                self._output_dirs[(mat_name, bake_type)] = output_dir
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

        self._props.bake_current_material = material.name if material else "None"
        self._props.bake_current_type = bake_type
        self._props.bake_frame_info = f"{frame} / {len(self._frames)}"
        self._props.bake_status = "Baking"

        self._scene.frame_set(frame)

        image_node = None
        image = None
        material_state = None

        try:
            if material:
                if bake_type == "METALLIC":
                    material_state = connect_metallic_node(material)
                elif bake_type == "OCCLUSION":
                    material_state = connect_occlusion_node(material)

            colorspace = self._props.colorspace
            if bake_type in {"NORMAL", "ROUGHNESS", "METALLIC", "OCCLUSION"}:
                colorspace = "Non-Color"

            width = self._props.sequenced_bake_width
            height = self._props.sequenced_bake_height

            image_node, image = create_image_texture(
                material=material,
                name=f"{self._obj.name}_{material.name if material else 'NoMat'}_{bake_type}_{frame}",
                width=width,
                height=height,
                alpha=self._props.sequence_is_alpha,
                float_buffer=self._props.sequence_use_float,
                interpolation=self._props.interpolation,
                projection=self._props.projection,
                extension=self._props.extension,
                colorspace=colorspace,
                file_format=self._props.sequenced_bake_image_format,
                projection_blend=self._props.projection_blend,
                image_source=self._props.image_source,
                image_alpha_mode=self._props.image_alpha_mode,
                udim_tiles=self._props.udim_tiles,
            )
            self._generated_images.append(image)
            self._active_material = material
            self._active_material_state = material_state
            self._active_image_node = image_node
            self._active_image = image

            mat_name = material.name if material else "NoMaterial"
            output_dir = self._output_dirs[(mat_name, bake_type)]
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
            )
        finally:
            if image_node is not None and material and material.node_tree:
                try:
                    if image_node.name in material.node_tree.nodes:
                        material.node_tree.nodes.remove(image_node)
                except (ReferenceError, RuntimeError) as exc:
                    print(f"[Sequenced Bake] Failed to remove temporary image node: {exc}")

            if material_state is not None and material:
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