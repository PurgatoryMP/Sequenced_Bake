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
    uv_pixels[:, 0] = np.clip(uv[:, 0], 0.0, 1.0) * width
    uv_pixels[:, 1] = np.clip(uv[:, 1], 0.0, 1.0) * height

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
    write_mask = inside & ~mask
    region[write_mask] = interpolated[write_mask]
    mask[write_mask] = True
    return int(write_mask.sum())


def bake_sculpt_direct_to_buffer(
    obj: bpy.types.Object,
    image: bpy.types.Image,
    normalization_bounds: np.ndarray | list | None = None,
    bounds_obj: bpy.types.Object | None = None ) -> None:
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
        encoded = np.clip(((coords - center) / bounds) * 0.5 + 0.5, 0.0, 1.0)        
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

        if not coverage.all():
            try:
                from scipy.ndimage import distance_transform_edt
                nearest = distance_transform_edt(
                    ~coverage, return_distances=False, return_indices=True
                )
                output[~coverage] = output[tuple(axis[~coverage] for axis in nearest)]
            except ImportError:
                output[~coverage] = 0.5

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
    cylinder_segments: bpy.props.IntProperty(
        name="Segments",
        description="Number of height segments for cylinder",
        default=16,
        min=2,
        max=256
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
    
    sculpt_type: bpy.props.EnumProperty(
        name="Sculpt Type",
        description="Topological mesh type for the sculpt map",
        items=[
            ('GRID', "Plane / Grid", "Flat grid topology (standard plane sculptie)"),
            ('SPHERE', "Sphere", "Spherical topology with unmerged pole rows"),
            ('CYLINDER', "Cylinder", "Cylindrical topology"),
            ('TORUS', "Torus", "Torus / ring topology"),
            ('CAPSULE', "Capsule", "Generate a capsule sculpt map"),
            ('CUBE', "Cube", "Generate a spherical-grid cube"),
            ('ROUND_CUBE', "Round Cube", "Generate a smoothly blended cube"),
            ('HELIX', "Helix", "Generate a helical spring sculpt map"),
            ('STAIRS', "Stairs", "Generate a folded staircase sculpt map"),
            ('BOLT', "Bolt", "Generate a cylinder-mapped bolt"),
            ('NUT', "Nut", "Generate a torus-mapped nut")
        ],
        default='GRID'
    )
    
    torus_ring_shape: bpy.props.EnumProperty(
        name="Ring Shape",
        description="Cross-sectional shape of the torus ring",
        items=[
            ('STANDARD', "Standard", "Standard circular torus"),
            ('D_RING', "D-Ring Loop", "D-shaped ring loop"),
            ('SQUARE', "Square Loop", "Square shaped loop"),
            ('ROUNDED', "Rounded loop", "Rounded rectangular loop"),
        ],
        default='STANDARD'
    )
    
    # torus Properties
    torus_major_radius: bpy.props.FloatProperty(name="Major Radius", default=1.0, min=0.1)
    torus_minor_radius: bpy.props.FloatProperty(name="Minor Radius", default=0.25, min=0.01)
    torus_shape_power: bpy.props.FloatProperty(
        name="Shape Power", 
        description="Controls the sharpness of corners for Square/Rounded, and the flatness of the D-Ring",
        default=2.0, 
        min=0.1, 
        max=10.0
    )
    
    # Generic Grid Resolution (Use for Cube/Round Cube/Capsule)
    grid_vertices: bpy.props.IntProperty(name="Vertices", default=32, min=4, max=256)
    grid_segments: bpy.props.IntProperty(name="Segments", default=32, min=4, max=256)
    
    # Capsule Properties
    capsule_radius: bpy.props.FloatProperty(name="Radius", default=1.0, min=0.1)
    capsule_height: bpy.props.FloatProperty(name="Total Height", default=3.0, min=0.1)
    
    # Cube Properties
    cube_size: bpy.props.FloatProperty(name="Size", default=2.0, min=0.1)
    
    # Round Cube Properties
    rcube_sharpness: bpy.props.FloatProperty(name="Sharpness", default=0.8, min=0.0, max=1.0)   
    
    # Helix Properties
    helix_major_radius: bpy.props.FloatProperty(name="Major Radius", default=1.0, min=0.1)
    helix_minor_radius: bpy.props.FloatProperty(name="Minor Radius", default=0.2, min=0.01)
    helix_height: bpy.props.FloatProperty(name="Height", default=4.0, min=0.1)
    helix_turns: bpy.props.FloatProperty(name="Turns", default=3.0, min=0.5)
    
    # Bolt Properties
    bolt_head_radius: bpy.props.FloatProperty(name="Head Radius", default=1.5, min=0.1)
    bolt_head_height: bpy.props.FloatProperty(name="Head Height", default=1.0, min=0.1)
    bolt_shaft_radius: bpy.props.FloatProperty(name="Shaft Radius", default=0.75, min=0.1)
    bolt_shaft_height: bpy.props.FloatProperty(name="Shaft Height", default=3.0, min=0.1)
    bolt_sides: bpy.props.IntProperty(name="Head Sides", default=6, min=3, max=32)

    # Nut Properties
    nut_inner_radius: bpy.props.FloatProperty(name="Inner Radius", default=0.75, min=0.1)
    nut_outer_radius: bpy.props.FloatProperty(name="Outer Radius", default=1.5, min=0.2)
    nut_height: bpy.props.FloatProperty(name="Height", default=1.0, min=0.1)
    nut_sides: bpy.props.IntProperty(name="Sides", default=6, min=3, max=32)
    
    # Additional Bolt Properties
    bolt_collapse_ends: bpy.props.BoolProperty(name="Collapse Ends", default=True)
    bolt_bevel_weight: bpy.props.FloatProperty(name="Bevel Weight", default=1.0, min=0.0, max=1.0)
    bolt_bevel_radius: bpy.props.FloatProperty(name="Bevel Radius", default=0.05, min=0.0)

    # Additional Nut Properties
    nut_bevel_weight: bpy.props.FloatProperty(name="Bevel Weight", default=1.0, min=0.0, max=1.0)
    nut_bevel_radius: bpy.props.FloatProperty(name="Bevel Radius", default=0.05, min=0.0)
    
    # Stairs Properties
    stairs_steps: bpy.props.IntProperty(name="Steps", default=10, min=1, max=128)
    stairs_step_height: bpy.props.FloatProperty(name="Step Height", default=0.2, min=0.01)
    stairs_step_depth: bpy.props.FloatProperty(name="Step Depth", default=0.3, min=0.01)
    stairs_width: bpy.props.FloatProperty(name="Width", default=2.0, min=0.1)
    stairs_inner_radius: bpy.props.FloatProperty(name="Inner Radius", default=1.0, min=0.0)
    stairs_curve: bpy.props.FloatProperty(
        name="Curve (Degrees)", 
        default=0.0, 
        description="Total rotation angle for spiral staircases. Positive curves right, negative left"
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
            box.prop(self, "cylinder_segments")
            box.prop(self, "cylinder_depth")
            
        elif self.sculpt_type == 'TORUS':
            box.label(text="Torus Settings:")
            box.prop(self, "torus_ring_shape")
            box.prop(self, "torus_major_segments")
            box.prop(self, "torus_minor_segments")
            box.prop(self, "torus_major_radius")
            box.prop(self, "torus_minor_radius")
            if self.torus_ring_shape in {'SQUARE', 'ROUNDED', 'D_RING'}:
                box.prop(self, "torus_shape_power")
        
        elif self.sculpt_type == 'CAPSULE':
            box.label(text="Capsule Settings:")
            box.prop(self, "grid_vertices")
            box.prop(self, "grid_segments")
            box.prop(self, "capsule_radius")
            box.prop(self, "capsule_height")
            
        elif self.sculpt_type == 'CUBE':
            box.label(text="Cube Settings:")
            box.prop(self, "grid_vertices")
            box.prop(self, "grid_segments")
            box.prop(self, "cube_size")
            
        elif self.sculpt_type == 'ROUND_CUBE':
            box.label(text="Round Cube Settings:")
            box.prop(self, "grid_vertices")
            box.prop(self, "grid_segments")
            box.prop(self, "cube_size", text="Base Size")
            box.prop(self, "rcube_sharpness")
        
        elif self.sculpt_type == 'STAIRS':
            box.label(text="Stairs Settings:")
            box.prop(self, "grid_vertices", text="Width Resolution")
            box.prop(self, "grid_segments", text="Profile Resolution")
            box.prop(self, "stairs_steps")
            box.prop(self, "stairs_step_height")
            box.prop(self, "stairs_step_depth")
            box.prop(self, "stairs_width")
            box.prop(self, "stairs_inner_radius")
            box.prop(self, "stairs_curve")
        
        elif self.sculpt_type == 'HELIX':
            box.label(text="Helix Settings:")
            box.prop(self, "grid_vertices", text="Wire Vertices")
            box.prop(self, "grid_segments", text="Length Segments")
            box.prop(self, "helix_major_radius")
            box.prop(self, "helix_minor_radius")
            box.prop(self, "helix_height")
            box.prop(self, "helix_turns")
        
        elif self.sculpt_type == 'BOLT':
            box.label(text="Bolt Settings:")
            box.prop(self, "grid_vertices", text="Perimeter Vertices")
            box.prop(self, "grid_segments", text="Profile Segments")
            box.prop(self, "bolt_sides")
            box.prop(self, "bolt_head_radius")
            box.prop(self, "bolt_head_height")
            box.prop(self, "bolt_shaft_radius")
            box.prop(self, "bolt_shaft_height")
            box.prop(self, "bolt_collapse_ends")
            if self.bolt_collapse_ends:
                box.prop(self, "bolt_bevel_weight")
                box.prop(self, "bolt_bevel_radius")

        elif self.sculpt_type == 'NUT':
            box.label(text="Nut Settings:")
            box.prop(self, "grid_vertices", text="Cross-Section Vertices")
            box.prop(self, "grid_segments", text="Perimeter Segments")
            box.prop(self, "nut_sides")
            box.prop(self, "nut_inner_radius")
            box.prop(self, "nut_outer_radius")
            box.prop(self, "nut_height")
            box.prop(self, "nut_bevel_weight")
            box.prop(self, "nut_bevel_radius")

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
            bm = bmesh.new()
            cols = self.cylinder_vertices
            rows = self.cylinder_segments
            half_depth = self.cylinder_depth / 2.0
            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            for j in range(rows + 1):
                v_frac = j / float(rows)
                z = -half_depth + (v_frac * self.cylinder_depth)
                row = []
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    lon = u_frac * 2.0 * np.pi
                    x = np.cos(lon)
                    y = np.sin(lon)
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

            mesh_data = bpy.data.meshes.new("SculptCylinderMesh")
            bm.to_mesh(mesh_data)
            bm.free()
            obj = bpy.data.objects.new("SculptCylinder", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
        elif self.sculpt_type == 'TORUS':
            import math
            bm = bmesh.new()
            cols = self.torus_major_segments
            rows = self.torus_minor_segments
            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            major_r = getattr(self, "torus_major_radius", 1.0)
            minor_r = getattr(self, "torus_minor_radius", 0.25)
            power = getattr(self, "torus_shape_power", 3.0)

            def eval_major_pos(a):
                mx, my = math.cos(a), math.sin(a)
                if self.torus_ring_shape == 'SQUARE':
                    # Superellipse with a high power for sharp square corners
                    p = 10.0
                    n = (abs(mx)**p + abs(my)**p)**(1.0 / p)
                    return mx / n, my / n
                elif self.torus_ring_shape == 'ROUNDED':
                    # Superellipse tied to the user's Shape Power control
                    p = max(1.5, power)
                    n = (abs(mx)**p + abs(my)**p)**(1.0 / p)
                    return mx / n, my / n
                elif self.torus_ring_shape == 'D_RING':
                    # Half circle, half flat bar, shifted left to center the origin
                    return max(0.0, mx) - 0.5, my
                # 'STANDARD'
                return mx, my

            for j in range(rows + 1):
                v_frac = j / float(rows)
                minor_angle = v_frac * 2.0 * math.pi
                
                # The cross-section pipe remains circular
                cx = math.cos(minor_angle) * minor_r
                cz = math.sin(minor_angle) * minor_r

                row = []
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    major_angle = u_frac * 2.0 * math.pi
                    
                    # Get base coordinate on the macro ring path
                    px, py = eval_major_pos(major_angle)
                    
                    # Calculate outward normal using numeric derivative
                    delta = 0.001
                    px1, py1 = eval_major_pos(major_angle + delta)
                    px2, py2 = eval_major_pos(major_angle - delta)
                    
                    tx, ty = (px1 - px2), (py1 - py2)
                    length = math.hypot(tx, ty)
                    if length > 0.00001:
                        tx, ty = tx / length, ty / length
                    else:
                        tx, ty = 0.0, 1.0
                        
                    # Rotate the path tangent 90 degrees outward to get the XY normal
                    nx, ny = ty, -tx
                    
                    # Apply major radius and displace the cross section along the normal
                    x = (px * major_r) + (nx * cx)
                    y = (py * major_r) + (ny * cx)
                    z = cz
                    
                    co = mathutils.Vector((x, y, z))
                    row.append(bm.verts.new(co))
                verts_grid.append(row)

            bm.verts.ensure_lookup_table()

            for j in range(rows):
                for i in range(cols):
                    v0, v1 = verts_grid[j][i], verts_grid[j][i+1]
                    v2, v3 = verts_grid[j+1][i+1], verts_grid[j+1][i]
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

            mesh_data = bpy.data.meshes.new("SculptTorus")
            bm.to_mesh(mesh_data)
            bm.free()

            obj = bpy.data.objects.new("SculptTorus", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
        elif self.sculpt_type == 'STAIRS':
            import math
            bm = bmesh.new()
            cols = self.grid_vertices
            rows = self.grid_segments
            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            step_h = self.stairs_step_height
            step_d = self.stairs_step_depth
            steps = self.stairs_steps
            profile_length = steps * (step_h + step_d)
            total_depth = steps * step_d
            total_height = steps * step_h
            curve_rads = math.radians(self.stairs_curve)

            for j in range(rows + 1):
                v_frac = j / float(rows)
                
                # Trace distance along the folded stair profile
                d = v_frac * profile_length
                step_idx = int(d / (step_h + step_d))
                if step_idx >= steps: 
                    step_idx = steps - 1
                
                local_d = d - (step_idx * (step_h + step_d))
                
                if local_d <= step_d:
                    # Tread (Horizontal)
                    pz = step_idx * step_h
                    py = (step_idx * step_d) + local_d
                else:
                    # Riser (Vertical)
                    pz = (step_idx * step_h) + (local_d - step_d)
                    py = (step_idx + 1) * step_d
                
                # Center the staircase height and depth for baseline
                pz -= total_height / 2.0
                centered_py = py - (total_depth / 2.0)
                
                row = []
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    
                    # Apply inner radius correctly to both modes
                    radius = self.stairs_inner_radius + (u_frac * self.stairs_width)
                    
                    if abs(curve_rads) > 0.001:
                        # Spiral staircase wrapping around the Z axis
                        t = py / total_depth
                        angle = t * curve_rads
                        x = radius * math.cos(angle)
                        y = radius * math.sin(angle)
                        z = pz
                    else:
                        # Straight staircase
                        x = (u_frac - 0.5) * self.stairs_width
                        y = centered_py
                        z = pz
                    
                    co = mathutils.Vector((x, y, z))
                    vert = bm.verts.new(co)
                    row.append(vert)
                verts_grid.append(row)

            bm.verts.ensure_lookup_table()

            for j in range(rows):
                for i in range(cols):
                    v0, v1 = verts_grid[j][i], verts_grid[j][i+1]
                    v2, v3 = verts_grid[j+1][i+1], verts_grid[j+1][i]
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
                        
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bw_layer = bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")
            
            for edge in bm.edges:
                if not edge.is_boundary:
                    try:
                        if edge.calc_face_angle() > 0.5:
                            edge[bw_layer] = 1.0
                    except ValueError:
                        # BMesh cannot calculate angles for highly twisted quads bridging a 90-degree fold
                        pass

            mesh_data = bpy.data.meshes.new("SculptStairs")
            bm.to_mesh(mesh_data)
            bm.free()

            obj = bpy.data.objects.new("SculptStairs", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
                
        elif self.sculpt_type == 'HELIX':
            import math
            bm = bmesh.new()
            cols = self.grid_vertices
            rows = self.grid_segments
            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            for j in range(rows + 1):
                v_frac = j / float(rows)
                t = v_frac * self.helix_turns * 2.0 * math.pi
                
                # Calculate the vertical climb
                base_z = -self.helix_height / 2.0 + (v_frac * self.helix_height)
                
                row = []
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    lon = u_frac * 2.0 * math.pi
                    
                    # Calculate local wire cross-section offsets
                    offset_n = self.helix_minor_radius * math.cos(lon)
                    offset_z = self.helix_minor_radius * math.sin(lon)
                    
                    # Apply cross-section to the global spiral path
                    x = (self.helix_major_radius + offset_n) * math.cos(t)
                    y = (self.helix_major_radius + offset_n) * math.sin(t)
                    z = base_z + offset_z
                    
                    co = mathutils.Vector((x, y, z))
                    vert = bm.verts.new(co)
                    row.append(vert)
                verts_grid.append(row)

            bm.verts.ensure_lookup_table()

            # Generate grid faces and map UV coordinates
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

            mesh_data = bpy.data.meshes.new("SculptHelix")
            bm.to_mesh(mesh_data)
            bm.free()

            obj = bpy.data.objects.new("SculptHelix", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
        
        elif self.sculpt_type in {'BOLT', 'NUT'}:
            import math
            bm = bmesh.new()
            cols = self.grid_vertices
            rows = self.grid_segments
            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            for j in range(rows + 1):
                v_frac = j / float(rows)
                row = []
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    
                    if self.sculpt_type == 'BOLT':
                        z_total = self.bolt_shaft_height + self.bolt_head_height
                        z_start = -z_total / 2.0
                        
                        # Apply pole collapsing for closed topology
                        if self.bolt_collapse_ends and j == 0:
                            z, r, sides = z_start, 0.0, 32
                        elif self.bolt_collapse_ends and j == rows:
                            z, r, sides = z_start + z_total, 0.0, self.bolt_sides
                        elif v_frac < (self.bolt_shaft_height / z_total):
                            z = z_start + (v_frac / (self.bolt_shaft_height / z_total)) * self.bolt_shaft_height
                            r, sides = self.bolt_shaft_radius, 32
                        else:
                            head_v = (v_frac - (self.bolt_shaft_height / z_total)) / (self.bolt_head_height / z_total)
                            z = z_start + self.bolt_shaft_height + (head_v * self.bolt_head_height)
                            r, sides = self.bolt_head_radius, self.bolt_sides
                        
                        angle = u_frac * 2.0 * math.pi
                        segment_angle = (2.0 * math.pi) / sides
                        local_angle = angle % segment_angle
                        r_poly = r * math.cos(segment_angle / 2.0) / math.cos(local_angle - segment_angle / 2.0)
                        
                        x = r_poly * math.cos(angle)
                        y = r_poly * math.sin(angle)
                        
                    elif self.sculpt_type == 'NUT':
                        u_wrap = (u_frac % 1.0) * 4.0
                        if u_wrap <= 1.0: 
                            r_minor, z_offset = self.nut_inner_radius, (self.nut_height / 2.0) - (u_wrap * self.nut_height)
                        elif u_wrap <= 2.0: 
                            r_minor = self.nut_inner_radius + ((u_wrap - 1.0) * (self.nut_outer_radius - self.nut_inner_radius))
                            z_offset = -self.nut_height / 2.0
                        elif u_wrap <= 3.0: 
                            r_minor, z_offset = self.nut_outer_radius, -self.nut_height / 2.0 + ((u_wrap - 2.0) * self.nut_height)
                        else: 
                            r_minor = self.nut_outer_radius - ((u_wrap - 3.0) * (self.nut_outer_radius - self.nut_inner_radius))
                            z_offset = self.nut_height / 2.0
                            
                        angle = v_frac * 2.0 * math.pi
                        segment_angle = (2.0 * math.pi) / self.nut_sides
                        local_angle = angle % segment_angle
                        
                        r_poly = r_minor * math.cos(segment_angle / 2.0) / math.cos(local_angle - segment_angle / 2.0)
                        x = r_poly * math.cos(angle)
                        y = r_poly * math.sin(angle)
                        z = z_offset

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

            # Automatically assign Bevel Weights to sharp corners
            if self.sculpt_type == 'NUT' or (self.sculpt_type == 'BOLT' and self.bolt_collapse_ends):
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                
                # Use generic float layer for Blender 4.0+ compatibility
                bw_layer = bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")
                weight = self.bolt_bevel_weight if self.sculpt_type == 'BOLT' else self.nut_bevel_weight
                
                for edge in bm.edges:
                    # Target hard 90-degree transitions
                    if not edge.is_boundary and edge.calc_face_angle() > 0.5:
                        edge[bw_layer] = weight

            mesh_data = bpy.data.meshes.new(f"Sculpt{self.sculpt_type.title()}")
            bm.to_mesh(mesh_data)
            bm.free()

            obj = bpy.data.objects.new(f"Sculpt{self.sculpt_type.title()}", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            # Apply Bevel Modifier dynamically
            radius = self.bolt_bevel_radius if self.sculpt_type == 'BOLT' else self.nut_bevel_radius
            if radius > 0 and (self.sculpt_type == 'NUT' or self.bolt_collapse_ends):
                mod = obj.modifiers.new(name="Bevel", type='BEVEL')
                mod.limit_method = 'WEIGHT'
                mod.width = radius
                mod.segments = 3
                mod.profile = 0.5
        
        elif self.sculpt_type in {'CAPSULE', 'CUBE', 'ROUND_CUBE'}:
            import math
            bm = bmesh.new()
            cols = self.grid_vertices
            rows = self.grid_segments
            uv_layer = bm.loops.layers.uv.verify()
            verts_grid = []

            # Pre-calculate capsule profile length to map UV 'V' coordinates accurately
            if self.sculpt_type == 'CAPSULE':
                L = max(0.0, self.capsule_height - (2.0 * self.capsule_radius))
                R = self.capsule_radius
                profile_len = (math.pi * R) + L

            for j in range(rows + 1):
                v_frac = j / float(rows)
                row = []
                
                for i in range(cols + 1):
                    u_frac = i / float(cols)
                    lon = u_frac * 2.0 * math.pi
                    
                    if self.sculpt_type == 'CAPSULE':
                        d = v_frac * profile_len
                        if d <= (math.pi * R / 2.0): # Bottom cap
                            lat = -math.pi/2.0 + (d / R)
                            z = -L/2.0 + (R * math.sin(lat))
                            r = R * math.cos(lat)
                        elif d <= (math.pi * R / 2.0 + L): # Straight cylinder body
                            z = -L/2.0 + (d - (math.pi * R / 2.0))
                            r = R
                        else: # Top cap
                            lat = (d - (math.pi * R / 2.0) - L) / R
                            z = L/2.0 + (R * math.sin(lat))
                            r = R * math.cos(lat)
                        
                        x = r * math.cos(lon)
                        y = r * math.sin(lon)
                        co = mathutils.Vector((x, y, z))
                        
                    elif self.sculpt_type in {'CUBE', 'ROUND_CUBE'}:
                        # 1. Map U linearly to a square perimeter [-1, 1]
                        u_wrap = (u_frac % 1.0) * 4.0
                        if u_wrap <= 1.0:
                            nx, ny = 1.0, -1.0 + (u_wrap * 2.0)
                        elif u_wrap <= 2.0:
                            nx, ny = 1.0 - ((u_wrap - 1.0) * 2.0), 1.0
                        elif u_wrap <= 3.0:
                            nx, ny = -1.0, 1.0 - ((u_wrap - 2.0) * 2.0)
                        else:
                            nx, ny = -1.0 + ((u_wrap - 3.0) * 2.0), -1.0
                            
                        # 2. Map V linearly to bottom cap, side walls, and top cap
                        if v_frac <= 0.25:
                            # Bottom face folds inward to the pole
                            r_cube = v_frac / 0.25
                            cx, cy, cz = nx * r_cube, ny * r_cube, -1.0
                        elif v_frac >= 0.75:
                            # Top face folds inward to the pole
                            r_cube = (1.0 - v_frac) / 0.25
                            cx, cy, cz = nx * r_cube, ny * r_cube, 1.0
                        else:
                            # Vertical side walls map directly
                            cx, cy = nx, ny
                            cz = -1.0 + ((v_frac - 0.25) / 0.5) * 2.0
                            
                        base_co = mathutils.Vector((cx, cy, cz))
                        
                        if self.sculpt_type == 'CUBE':
                            co = base_co * (self.cube_size / 2.0)
                            
                        elif self.sculpt_type == 'ROUND_CUBE':
                            # Map the sharpness property (0 to 1) to a corner radius (1 to 0)
                            radius = 1.0 - self.rcube_sharpness
                            inner_bound = 1.0 - radius
                            
                            # Clamp the base coordinates to the boundary of the internal sharp cube
                            ix = max(-inner_bound, min(inner_bound, base_co.x))
                            iy = max(-inner_bound, min(inner_bound, base_co.y))
                            iz = max(-inner_bound, min(inner_bound, base_co.z))
                            inner_co = mathutils.Vector((ix, iy, iz))
                            
                            # Push outward radially from the clamped internal box to create precise, uniform spherical corners
                            diff = base_co - inner_co
                            if diff.length > 0:
                                blended_co = inner_co + (diff.normalized() * radius)
                            else:
                                blended_co = base_co
                                
                            co = blended_co * (self.cube_size / 2.0)

                    vert = bm.verts.new(co)
                    row.append(vert)
                verts_grid.append(row)

            bm.verts.ensure_lookup_table()

            # Generate grid faces and map UV coordinates
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

            mesh_data = bpy.data.meshes.new(f"Sculpt{self.sculpt_type.title().replace('_', '')}")
            bm.to_mesh(mesh_data)
            bm.free()

            obj = bpy.data.objects.new(f"Sculpt{self.sculpt_type.title().replace('_', '')}", mesh_data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
        else:
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=32, y_subdivisions=32, size=2.0)
            obj = context.active_object
            if obj:
                obj.name = "SculptMesh"

        if obj:
            self.report({'INFO'}, f"Created sculpt mesh: {obj.name}")            
            context.view_layer.update()            
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            bbox = context.active_object
            bbox.name = f"{obj.name}_bbox"
            bbox.display_type = 'WIRE'            
            bbox.dimensions = obj.dimensions
            
            # Center the bounding box accurately on the mesh geometry
            local_bbox_center = sum((mathutils.Vector(b) for b in obj.bound_box), mathutils.Vector()) / 8.0
            bbox.location = obj.matrix_world @ local_bbox_center
            
            if hasattr(context.scene, "sequenced_bake_props"):
                context.scene.sequenced_bake_props.sequenced_bake_sculpt_bounds_object = bbox
                
            bbox.select_set(False)
            context.view_layer.objects.active = obj
            obj.select_set(True)

        return {'FINISHED'}


class VIEW3D_MT_mesh_sculpties_add(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_mesh_sculpties_add"
    bl_label = "Sculpts"

    def draw(self, context):
        layout = self.layout

        # Grid / Plane
        layout.operator("mesh.add_sculpt_mesh", text="Grid", icon='MESH_PLANE').sculpt_type = 'GRID'
        
        # Standard Primitives
        layout.operator("mesh.add_sculpt_mesh", text="Sphere", icon='MESH_UVSPHERE').sculpt_type = 'SPHERE'
        layout.operator("mesh.add_sculpt_mesh", text="Cylinder", icon='MESH_CYLINDER').sculpt_type = 'CYLINDER'
        layout.operator("mesh.add_sculpt_mesh", text="Torus", icon='MESH_TORUS').sculpt_type = 'TORUS'
        layout.operator("mesh.add_sculpt_mesh", text="Capsule", icon='MESH_CAPSULE').sculpt_type = 'CAPSULE'
        layout.operator("mesh.add_sculpt_mesh", text="Cube", icon='MESH_CUBE').sculpt_type = 'CUBE'
        
        # Modified Primitives
        layout.operator("mesh.add_sculpt_mesh", text="Round Cube", icon='MOD_BEVEL').sculpt_type = 'ROUND_CUBE'
        layout.operator("mesh.add_sculpt_mesh", text="Helix", icon='MOD_SCREW').sculpt_type = 'HELIX'
        layout.operator("mesh.add_sculpt_mesh", text="Stairs", icon='MOD_ARRAY').sculpt_type = 'STAIRS'
        
        # Hardware
        layout.operator("mesh.add_sculpt_mesh", text="Bolt", icon='MESH_CYLINDER').sculpt_type = 'BOLT'
        layout.operator("mesh.add_sculpt_mesh", text="Nut", icon='MESH_TORUS').sculpt_type = 'NUT'

def menu_func_add_sculpties(self, context):
    self.layout.menu(VIEW3D_MT_mesh_sculpties_add.bl_idname, icon='UV_DATA')
