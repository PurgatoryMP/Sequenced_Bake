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

import numpy as np
import bpy
import mathutils

_LOG_PREFIX = "[Sequenced Bake][Sculpt]"
_EPSILON = 1.0e-8


def _evaluated_mesh(obj: bpy.types.Object) -> tuple[bpy.types.Depsgraph, bpy.types.Object]:
    """Return the dependency graph and evaluated object for the given object.

    Args:
        obj (bpy.types.Object): The Blender object to evaluate.

    Returns:
        tuple[bpy.types.Depsgraph, bpy.types.Object]: The evaluation dependency
            graph and the evaluated mesh object.

    Raises:
        TypeError: If the object is None or not of type 'MESH'.
    """
    if obj is None or obj.type != "MESH":
        name = getattr(obj, "name", "<None>")
        kind = getattr(obj, "type", "<None>")
        raise TypeError(f"Sculpt maps require a mesh object; got '{name}' ({kind}).")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    return depsgraph, obj.evaluated_get(depsgraph)


def _read_vertex_coordinates(mesh: bpy.types.Mesh) -> np.ndarray:
    """Return evaluated vertex coordinates as an N x 3 float32 array.

    Args:
        mesh (bpy.types.Mesh): The evaluated mesh datablock.

    Returns:
        numpy.ndarray: An array of vertex coordinates of shape (N, 3).

    Raises:
        RuntimeError: If the mesh has no vertices or contains non-finite values.
    """
    if not mesh.vertices:
        raise RuntimeError("The evaluated mesh contains no vertices.")

    coords = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get("co", coords.ravel())
    if not np.isfinite(coords).all():
        raise RuntimeError("The evaluated mesh contains non-finite vertex coordinates.")
    return coords


def calculate_sculpt_bounds(obj: bpy.types.Object, bounds_obj: bpy.types.Object | None = None) -> np.ndarray:
    """Calculate stable, non-zero per-axis normalization extents.

    If bounds_obj is provided, extents are calculated from that reference
    object instead of the target mesh, locking the bounding box across
    animation frames to prevent wobbling or deformation artifacts. If no
    object is defined, normal mesh bounds are used.

    Args:
        obj (bpy.types.Object): Mesh object to evaluate.
        bounds_obj (bpy.types.Object | None): Optional reference object.

    Returns:
        numpy.ndarray: Three positive normalization extents (X, Y, Z).
    """
    target_obj = bounds_obj if bounds_obj is not None else obj
    depsgraph, obj_eval = _evaluated_mesh(target_obj)
    mesh = None
    try:
        mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if mesh is None:
            raise RuntimeError(f"Could not evaluate mesh '{target_obj.name}'.")
        coords = _read_vertex_coordinates(mesh)
        center = coords.mean(axis=0)
        extents = np.max(np.abs(coords - center), axis=0)
        extents = np.maximum(extents, _EPSILON).astype(np.float32)
        return extents
    finally:
        if mesh is not None:
            obj_eval.to_mesh_clear()


def get_sculpt_mesh_dimensions(obj: bpy.types.Object) -> tuple[int, int]:
    """Return a UV-derived grid estimate for diagnostics only.

    This value is deliberately not used to determine the output image size or
    to reshape mesh vertices. Non-grid meshes are valid input to the rasterizer.

    Args:
        obj (bpy.types.Object): Mesh object to evaluate.

    Returns:
        tuple[int, int]: Unique U and V coordinate counts.
    """
    depsgraph, obj_eval = _evaluated_mesh(obj)
    mesh = None
    try:
        mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if mesh is None or not mesh.uv_layers.active:
            return 0, 0
        uv_data = mesh.uv_layers.active.data
        u_values = np.asarray([round(float(item.uv.x), 6) for item in uv_data])
        v_values = np.asarray([round(float(item.uv.y), 6) for item in uv_data])
        return len(np.unique(u_values)), len(np.unique(v_values))
    finally:
        if mesh is not None:
            obj_eval.to_mesh_clear()


def _rasterize_triangle(output: np.ndarray, coverage: np.ndarray, uv: np.ndarray, colors: np.ndarray) -> int:
    """Rasterize one UV-space triangle using barycentric interpolation.

    Args:
        output (numpy.ndarray): Target RGB image buffer of shape (H, W, 3).
        coverage (numpy.ndarray): Boolean coverage mask of shape (H, W).
        uv (numpy.ndarray): Triangle UV coordinates of shape (3, 2).
        colors (numpy.ndarray): Vertex RGB color values of shape (3, 3).

    Returns:
        int: Number of newly covered pixels.
    """
    height, width, _ = output.shape
    uv_pixels = np.empty((3, 2), dtype=np.float64)
    # Map 0..1 UV coordinates across full image dimensions to prevent edge offset/clipping
    uv_pixels[:, 0] = np.clip(uv[:, 0], 0.0, 1.0) * width
    uv_pixels[:, 1] = np.clip(uv[:, 1], 0.0, 1.0) * height

    # Reject UV triangles entirely outside the unit square.
    if (np.max(uv[:, 0]) < 0.0 or np.min(uv[:, 0]) > 1.0 or
            np.max(uv[:, 1]) < 0.0 or np.min(uv[:, 1]) > 1.0):
        return 0

    x0 = max(0, int(np.floor(uv_pixels[:, 0].min())))
    x1 = min(width - 1, int(np.ceil(uv_pixels[:, 0].max())))
    y0 = max(0, int(np.floor(uv_pixels[:, 1].min())))
    y1 = min(height - 1, int(np.ceil(uv_pixels[:, 1].max())))
    if x0 > x1 or y0 > y1:
        return 0

    p0, p1, p2 = uv_pixels
    denominator = ((p1[1] - p2[1]) * (p0[0] - p2[0]) +
                   (p2[0] - p1[0]) * (p0[1] - p2[1]))
    if abs(denominator) <= _EPSILON:
        return 0

    xs = np.arange(x0, x1 + 1, dtype=np.float64)
    ys = np.arange(y0, y1 + 1, dtype=np.float64)
    xx, yy = np.meshgrid(xs, ys)
    w0 = ((p1[1] - p2[1]) * (xx - p2[0]) +
          (p2[0] - p1[0]) * (yy - p2[1])) / denominator
    w1 = ((p2[1] - p0[1]) * (xx - p2[0]) +
          (p0[0] - p2[0]) * (yy - p2[1])) / denominator
    w2 = 1.0 - w0 - w1
    inside = (w0 >= -1.0e-6) & (w1 >= -1.0e-6) & (w2 >= -1.0e-6)
    if not inside.any():
        return 0

    interpolated = (
        w0[..., None] * colors[0] +
        w1[..., None] * colors[1] +
        w2[..., None] * colors[2]
    )
    region = output[y0:y1 + 1, x0:x1 + 1]
    mask = coverage[y0:y1 + 1, x0:x1 + 1]
    
    # At shared edges either adjacent triangle is a valid interpolation. Do not
    # overwrite pixels already assigned, avoiding order-dependent seam colors.
    write_mask = inside & ~mask
    region[write_mask] = interpolated[write_mask]
    mask[write_mask] = True
    return int(write_mask.sum())


def bake_sculpt_direct_to_buffer(
    obj: bpy.types.Object,
    image: bpy.types.Image,
    normalization_bounds: np.ndarray | list | None = None,
    bounds_obj: bpy.types.Object | None = None
) -> None:
    """Write a sculpt map to a Blender image using evaluated mesh triangles.

    Each output pixel is located in UV space and receives a barycentrically
    interpolated object-space position, encoded into RGB in the 0..1 range
    and quantized to 8-bit per channel precision (256 discrete levels).
    If bounds_obj is specified, normalization bounds and center are locked
    to the reference object to ensure stable animation baking without wobble.

    Args:
        obj (bpy.types.Object): Mesh object to encode.
        image (bpy.types.Image): Target Blender image datablock.
        normalization_bounds (numpy.ndarray | list | None): Optional extents from
            calculate_sculpt_bounds. If omitted, extents are calculated
            from the current evaluated mesh or bounds_obj.
        bounds_obj (bpy.types.Object | None): Optional reference object.

    Raises:
        TypeError: If the image or object is invalid.
        ValueError: If image dimensions or normalization bounds are invalid.
        RuntimeError: If the evaluated mesh or UV map is invalid.
    """
    if image is None or len(image.size) < 2:
        raise TypeError("A valid Blender image is required for sculpt-map output.")
    width, height = int(image.size[0]), int(image.size[1])
    if width < 2 or height < 2:
        raise ValueError(f"Sculpt map must be at least 2x2 pixels; got {width}x{height}.")

    depsgraph, obj_eval = _evaluated_mesh(obj)
    mesh = None
    try:
        mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if mesh is None:
            raise RuntimeError(f"Could not evaluate mesh '{obj.name}'.")
        uv_layer = mesh.uv_layers.active
        if uv_layer is None:
            raise RuntimeError(f"Mesh '{obj.name}' has no active UV map.")
        if not mesh.polygons:
            raise RuntimeError(f"Mesh '{obj.name}' contains no polygons to rasterize.")

        coords = _read_vertex_coordinates(mesh)

        # Lock center and bounds to reference bounding object if provided
        if bounds_obj is not None:
            _, ref_obj_eval = _evaluated_mesh(bounds_obj)
            ref_mesh = ref_obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            try:
                if ref_mesh is None:
                    raise RuntimeError(f"Could not evaluate bounds object '{bounds_obj.name}'.")
                ref_coords = _read_vertex_coordinates(ref_mesh)
                center = ref_coords.mean(axis=0)
                bounds = np.max(np.abs(ref_coords - center), axis=0)
            finally:
                if ref_mesh is not None:
                    ref_obj_eval.to_mesh_clear()
        else:
            center = coords.mean(axis=0)
            if normalization_bounds is None:
                bounds = np.max(np.abs(coords - center), axis=0)
            else:
                bounds = np.asarray(normalization_bounds, dtype=np.float32).reshape(-1)
                if bounds.size != 3 or not np.isfinite(bounds).all():
                    raise ValueError("normalization_bounds must contain three finite values.")

        bounds = np.maximum(bounds, _EPSILON)
        
        # Encode coordinates to 0..1 range
        encoded = np.clip(((coords - center) / bounds) * 0.5 + 0.5, 0.0, 1.0)
        
        # Quantize vertex colors to strict 8-bit per channel precision (0 to 255 steps)[cite: 3]
        encoded = np.round(encoded * 255.0) / 255.0

        mesh.calc_loop_triangles()
        uv_values = np.empty((len(mesh.loops), 2), dtype=np.float64)
        uv_layer.data.foreach_get("uv", uv_values.ravel())
        output = np.zeros((height, width, 3), dtype=np.float32)
        coverage = np.zeros((height, width), dtype=bool)
        triangle_count = 0
        covered_count = 0

        for triangle in mesh.loop_triangles:
            loop_indices = tuple(triangle.loops)
            vertex_indices = tuple(triangle.vertices)
            tri_uv = uv_values[list(loop_indices)]
            tri_colors = encoded[list(vertex_indices)]
            covered = _rasterize_triangle(output, coverage, tri_uv, tri_colors)
            if covered:
                triangle_count += 1
                covered_count += covered

        if not coverage.any():
            raise RuntimeError(
                f"No pixels were covered by UV triangles for '{obj.name}'. "
                "Check that the active UV map overlaps the 0-1 UV tile."
            )

        # Sculpt maps are opaque RGB position maps. Uncovered pixels are filled
        # from the nearest covered texel to avoid black borders during filtering.
        if not coverage.all():
            try:
                from scipy.ndimage import distance_transform_edt
                nearest = distance_transform_edt(
                    ~coverage, return_distances=False, return_indices=True
                )
                output[~coverage] = output[tuple(axis[~coverage] for axis in nearest)]
            except ImportError:
                # SciPy is not guaranteed to ship with Blender. Keep unpainted
                # texels at the neutral position rather than fail the bake.
                output[~coverage] = 0.5

        # Quantize final raster output buffer to strict 8-bit per channel precision[cite: 3]
        output = np.round(output * 255.0) / 255.0

        rgba = np.ones((height, width, 4), dtype=np.float32)
        rgba[..., :3] = output
        image.pixels.foreach_set(rgba.ravel())
        image.update()

        print(
            f"{_LOG_PREFIX} Baked '{obj.name}' using {len(coords)} evaluated vertices, "
            f"{len(mesh.loop_triangles)} triangles, {triangle_count} rasterized triangles, "
            f"image={width}x{height}, covered_pixels={int(coverage.sum())}/{width * height}."
        )
    except Exception as exc:
        print(f"{_LOG_PREFIX} Failed for '{getattr(obj, 'name', '<unknown>')}': {exc}")
        raise RuntimeError(f"Sculpt map bake failed for object '{obj.name}': {exc}") from exc
    finally:
        if mesh is not None:
            obj_eval.to_mesh_clear()


class MESH_OT_add_sculpt_mesh(bpy.types.Operator):
    """Operator to add a sculpt mesh for Second Life / baking workflows with customizable topology and subdivisions."""
    bl_idname = "mesh.add_sculpt_mesh"
    bl_label = "Add Sculpt Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    sculpt_type: bpy.props.EnumProperty(
        name="Sculpt Type",
        description="Topological mesh type for the sculpt map",
        items=[
            ('GRID', "Plane / Grid", "Flat grid topology (standard plane sculptie)"),
            ('SPHERE', "Sphere", "Spherical topology with unmerged pole rows"),
            ('CYLINDER', "Cylinder", "Cylindrical topology"),
            ('TORUS', "Torus", "Torus / ring topology"),
        ],
        default='GRID'
    )

    # Grid / Plane subdivisions
    subdivisions_x: bpy.props.IntProperty(
        name="X Subdivisions",
        description="Number of subdivisions along X axis for grid",
        default=32,
        min=2,
        max=256
    )
    subdivisions_y: bpy.props.IntProperty(
        name="Y Subdivisions",
        description="Number of subdivisions along Y axis for grid",
        default=32,
        min=2,
        max=256
    )

    # Sphere segments/rings
    sphere_segments: bpy.props.IntProperty(
        name="Segments",
        description="Number of segments for sphere",
        default=32,
        min=3,
        max=256
    )
    sphere_rings: bpy.props.IntProperty(
        name="Rings",
        description="Number of rings for sphere",
        default=16,
        min=2,
        max=256
    )

    # Cylinder vertices/depth
    cylinder_vertices: bpy.props.IntProperty(
        name="Vertices",
        description="Number of vertices around cylinder",
        default=32,
        min=3,
        max=256
    )
    cylinder_depth: bpy.props.FloatProperty(
        name="Depth",
        description="Height of cylinder",
        default=2.0,
        min=0.01,
        max=100.0
    )

    # Torus segments
    torus_major_segments: bpy.props.IntProperty(
        name="Major Segments",
        description="Segments in the major ring of the torus",
        default=32,
        min=3,
        max=256
    )
    torus_minor_segments: bpy.props.IntProperty(
        name="Minor Segments",
        description="Segments in the cross-section of the torus",
        default=32,
        min=3,
        max=256
    )

    def draw(self, context: bpy.types.Context) -> None:
        """Draw operator properties in the F9 Adjust Last Operation panel."""
        layout = self.layout
        layout.prop(self, "sculpt_type")
        
        box = layout.box()
        if self.sculpt_type == 'GRID':
            box.label(text="Grid Settings:")
            box.prop(self, "subdivisions_x")
            box.prop(self, "subdivisions_y")
        elif self.sculpt_type == 'SPHERE':
            box.label(text="Sphere Settings:")
            box.prop(self, "sphere_segments")
            box.prop(self, "sphere_rings")
        elif self.sculpt_type == 'CYLINDER':
            box.label(text="Cylinder Settings:")
            box.prop(self, "cylinder_vertices")
            box.prop(self, "cylinder_depth")
        elif self.sculpt_type == 'TORUS':
            box.label(text="Torus Settings:")
            box.prop(self, "torus_major_segments")
            box.prop(self, "torus_minor_segments")

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Execute the operator to create the selected sculpt mesh primitive."""
        import bmesh

        if self.sculpt_type == 'GRID':
            bpy.ops.mesh.primitive_grid_add(
                x_subdivisions=self.subdivisions_x,
                y_subdivisions=self.subdivisions_y,
                size=2.0
            )
            obj = context.active_object
            if obj:
                obj.name = "SculptGrid"
        elif self.sculpt_type == 'SPHERE':
            # Create custom grid-based sphere where pole vertices are collapsed in 3D
            # but remain unmerged across a clean rectangular UV grid layout.
            bm = bmesh.new()
            cols = self.sphere_segments
            rows = self.sphere_rings

            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            for j in range(rows + 1):
                v_frac = j / float(rows)
                lat = (v_frac - 0.5) * np.pi
                row = []
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    lon = u_frac * 2.0 * np.pi

                    if j == 0:
                        co = mathutils.Vector((0.0, 0.0, -1.0))
                    elif j == rows:
                        co = mathutils.Vector((0.0, 0.0, 1.0))
                    else:
                        x = np.cos(lat) * np.cos(lon)
                        y = np.cos(lat) * np.sin(lon)
                        z = np.sin(lat)
                        co = mathutils.Vector((x, y, z))

                    vert = bm.verts.new(co)
                    row.append(vert)
                verts_grid.append(row)

            bm.verts.ensure_lookup_table()

            for j in range(rows):
                for i in range(cols):
                    v0 = verts_grid[j][i]
                    v1 = verts_grid[j][i+1]
                    v2 = verts_grid[j+1][i+1]
                    v3 = verts_grid[j+1][i]
                    try:
                        face = bm.faces.new((v0, v1, v2, v3))
                        face_uvs = {
                            v0: (i / cols, j / rows),
                            v1: ((i + 1) / cols, j / rows),
                            v2: ((i + 1) / cols, (j + 1) / rows),
                            v3: (i / cols, (j + 1) / rows),
                        }
                        for loop in face.loops:
                            uv_coords = face_uvs.get(loop.vert)
                            if uv_coords:
                                loop[uv_layer].uv = mathutils.Vector(uv_coords)
                    except ValueError:
                        continue

            mesh_data = bpy.data.meshes.new("SculptSphereMesh")
            bm.to_mesh(mesh_data)
            bm.free()

            obj = bpy.data.objects.new("SculptSphere", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
        elif self.sculpt_type == 'CYLINDER':
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=self.cylinder_vertices,
                depth=self.cylinder_depth,
                radius=1.0
            )
            obj = context.active_object
            if obj:
                obj.name = "SculptCylinder"
        elif self.sculpt_type == 'TORUS':
            bpy.ops.mesh.primitive_torus_add(
                major_segments=self.torus_major_segments,
                minor_segments=self.torus_minor_segments,
                major_radius=1.0,
                minor_radius=0.25
            )
            obj = context.active_object
            if obj:
                obj.name = "SculptTorus"
        else:
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=32, y_subdivisions=32, size=2.0)
            obj = context.active_object
            if obj:
                obj.name = "SculptMesh"

        if obj:
            self.report({'INFO'}, f"Created sculpt mesh: {obj.name}")
        return {'FINISHED'}


class VIEW3D_MT_mesh_sculpties_add(bpy.types.Menu):
    """Menu for adding sculpties/sculpt meshes in the 3D Viewport."""
    bl_idname = "VIEW3D_MT_mesh_sculpties_add"
    bl_label = "Sculpties"

    def draw(self, context: bpy.types.Context) -> None:
        """Draw menu items."""
        layout = self.layout
        layout.operator(MESH_OT_add_sculpt_mesh.bl_idname, text="Sculpt Mesh")


def menu_func_add_sculpties(self, context: bpy.types.Context) -> None:
    """Append the sculpties menu to the mesh add menu.

    Args:
        self: Operator or menu instance.
        context (bpy.types.Context): Blender context.
    """
    self.layout.menu(VIEW3D_MT_mesh_sculpties_add.bl_idname)