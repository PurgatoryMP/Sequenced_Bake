# Sequenced Bake

## Overview

**Sequenced Bake** is a Blender add-on module designed for high-throughput, frame-by-frame material baking across animated sequences.

It provides a **non-blocking, task-driven baking pipeline** that processes materials, bake passes, and frame ranges in a structured queue—allowing complex baking operations to run while maintaining full UI responsiveness.

The system integrates directly with Blender’s material node workflows, supports advanced bake configurations, and includes real-time diagnostics such as progress tracking, FPS, and estimated completion time.

---

## Architecture

The Sequenced Bake module is structured into a modular pipeline:

- `operator.py` — Modal task scheduler and execution engine  
- `processing.py` — Core baking logic and node manipulation utilities  
- `properties.py` — Full configuration system and user-defined bake settings  
- `ui.py` — UI panels and node-based interface  

This separation allows for clean extensibility and isolates bake logic from UI and state management.

---

## Core Features

### Sequenced Bake Engine
- Modal, timer-driven execution (non-blocking)
- Task queue built from:
  - Materials (active or all)
  - Enabled bake types
  - Frame range
- Per-task execution model:  
  `(material, bake_type, frame)`
- **Total tasks = Materials × Bake Types × Frames**
- Maintains UI responsiveness during long bake operations

---

### Multi-Material & Batch Baking
- Bake:
  - Active material only  
  - **All materials on an object**
- Automatically iterates through material slots
- Organizes output per material and bake type

---

### Frame Sequencing
- Uses scene frame range (`frame_start → frame_end`)
- Automatically steps and evaluates scene per frame
- Supports animated shaders, drivers, and keyframed node values

---

### Supported Bake Types

Includes all major Cycles bake passes plus extended workflows:

- Normal (with full swizzle + space control)
- Roughness
- Glossy
- Diffuse (with lighting contribution control)
- Transmission
- Emission
- Ambient Occlusion
- Shadow
- Position
- UV
- Environment
- Combined (configurable contributions)
- Metallic *(custom node routing)*
- ORM (Occlusion / Roughness / Metallic packed output)
- Sculpt *(beta — UV -> Object-space position bake)*

---

### Advanced Node Injection (Non-Destructive)

Sequenced Bake dynamically modifies material node trees when required:

- **Metallic Bake**
  - Temporarily reroutes Metallic → Material Output

- **ORM Bake**
  - Constructs a temporary node graph:
    - AO → Red
    - Roughness → Green
    - Metallic → Blue
  - Injects a temporary Principled BSDF for emission-based baking
  - Preserves:
    - Alpha connections
    - Normal inputs

---

## Sculpt Maps in v1.1.8

The Sculpt Map system generates a **normalized object-space position map** by projecting evaluated mesh geometry into UV space and encoding the resulting 3D positions into an RGB image.

It is designed for **Second Life sculpt maps** and for stable sculpt-map generation across animated sequences.

## How It Works

### 1. Evaluated Mesh Sampling

- Uses Blender's evaluated mesh, including modifiers and animation.
- Extracts the evaluated mesh geometry and active UV data.
- Supports arbitrary mesh topology rather than requiring a specific subdivision layout.

### 2. UV-Space Rasterization

The mesh is converted into triangles in UV space.

For each sculpt-map pixel:

- The corresponding UV coordinate is calculated.
- UV triangles are tested for pixel coverage.
- Barycentric coordinates are calculated for covered pixels.
- The 3D vertex positions are interpolated across the triangle.

This produces a continuous object-space position map across the UV surface.

### 3. Position Encoding

Interpolated object-space positions are normalized into the `0–1` range and encoded into the RGB channels:

- **R = X**
- **G = Y**
- **B = Z**

The resulting image contains the object-space position of the mesh surface at each UV location.

### 4. Stable Sculpt Bounds

Sculpt-map normalization can use a dedicated **Bounding Object**.

When a bounding object is specified:

- The bounding object's bounds are used as the normalization reference.
- The same bounds are maintained across animation frames.
- Deforming geometry does not cause the sculpt-map coordinate range to change.

This helps prevent frame-to-frame scaling, shifting, or distortion in animated sculpt-map sequences.

If no bounding object is specified, the bounds are calculated from the evaluated mesh.

## Sculpt Map Resolution

The sculpt-map resolution should generally match the density and proportions of the mesh.

| Mesh Density | Recommended Resolution |
|---|---|
| Very Low (≤10 tris) | 16×16 |
| Low (10–100 tris) | 16×16 – 32×32 |
| Medium (100–2k tris) | 32×32 – 64×64 |
| High (2k–10k tris) | 64×64 – 128×128 |
| Very High (10k+ tris) | 128×128 |

Non-square resolutions can also be useful when the UV layout has significantly different density along each axis.

For example:

- `32×128`
- `64×128`
- `128×64`

This can be useful for long or highly directional meshes such as railings, strips, and other elongated assets.

## Key Features

- Evaluated mesh support
- Modifier and animation support
- UV-based triangle rasterization
- Barycentric position interpolation
- Object-space position encoding
- Stable animation-frame normalization
- Optional Bounding Object for consistent bounds
- Support for arbitrary mesh topology
- Improved handling of uncovered UV pixels
- Designed for Second Life sculpt-map workflows

## Output

The Sculpt Map produces an RGB position map where:

- **Red** represents normalized X position.
- **Green** represents normalized Y position.
- **Blue** represents normalized Z position.

The resulting image can be used for:

- Second Life sculpt maps
- Displacement reconstruction
- Procedural mesh workflows
- Animated mesh baking
- Position-map based reconstruction pipelines

## Limitations

- Requires a suitable UV layout for accurate results.
- Overlapping UVs can produce conflicting pixel data.
- UV seams and gaps may result in uncovered pixels.
- Sculpt-map resolution should be appropriate for the mesh's topology and UV density.
- For animated meshes, a **Bounding Object** is recommended when consistent frame-to-frame normalization is required.

---

### Image Generation Pipeline
- Generates a new image per task (material × bake type × frame)
- Creates image textures dynamically during execution
- Configurable:
  - Resolution (1–8192)
  - Bit depth (8-bit / 32-bit float)
  - Alpha support
  - Color space
- Automatically assigns and activates bake targets
- Cleans up unused image datablocks after completion (optional)

---

### Selected-to-Active Baking
- Full support for projection baking workflows:
  - Cage object support
  - Ray distance control
  - Extrusion settings

---

### Color Management Control
Per-bake override of Blender color pipeline:

- Display Device
- View Transform
- Look
- Exposure / Gamma
- Sequencer color space

Ensures consistent output for pipelines requiring strict color fidelity.

---

### Real-Time Diagnostics

Live bake feedback includes:

- Progress (0.0 → 1.0)
- Current material
- Current bake type
- Frame index tracking
- Effective FPS (throughput)
- Estimated time remaining (ETA)

---

### Performance Model

- Incremental processing via Blender modal timer
- Avoids UI freezing during large batch jobs
- Tracks per-task execution time for accurate ETA prediction

---

## User Interface

### 3D View Panel (N-Panel)

Located under:  
**`View3D → Sidebar → Sequenced Bake`**

Includes:

- Material Manager (slot-based workflow)
- Frame range controls
- Image settings
- Bake type selection
- Color management
- Bake controls
- Real-time diagnostics panel (progress, FPS, ETA, current task)

---

### Shader Editor Node

A fully functional **Sequenced Bake Node** is available:

- Mirrors panel functionality
- Allows node-based workflow integration
- Useful for material-centric pipelines

---

## Usage

### Basic Workflow

1. Select an object with a material  
2. Ensure **Cycles** is the active render engine  
3. Open the **Sequenced Bake panel** or node  
4. Configure:
   - Output directory
   - Frame range
   - Image settings
   - Bake types  
5. Click **“Bake Material Sequence”**

The system will:

- Build a task queue  
- Process each bake incrementally  
- Save outputs per material / type / frame  

---

## Output Structure

Baked images are organized as:

<output_path>/
<Object><Material><BakeType>/
1.png
2.png
3.png


---

## Configuration Highlights

- Resolution up to 8K  
- Multiple image formats (PNG, EXR, TIFF, etc.)  
- Normal map presets:
  - OpenGL
  - DirectX
  - Unity / Unreal / Substance  
- Texture sampling:
  - Interpolation
  - Projection
  - Extension modes  
- Optional automatic cleanup of generated textures  

---

## Requirements

- Blender (Cycles render engine required)

---

## Notes

- Designed for **animation baking pipelines**, not single-frame baking  
- Optimized for:
  - Game asset workflows  
  - Shader-driven animation  
  - Procedural material baking  
- Node graph modifications are **fully reversible and non-destructive**

---

## Pipeline / Use Cases

### Game Development (Real-Time Engines)

Sequenced Bake supports asset pipelines targeting Unity, Unreal Engine, and custom runtimes.

- Bake shader-driven animation into **image sequences**
- Generate full PBR map sets across frames
- Replace runtime shader cost with pre-baked textures

---

### Shader-to-Texture Conversion

- Convert procedural materials into static or animated textures  
- Preserve lighting contributions and emission data  
- Useful for asset export and lookdev finalization  

---

### VFX and Motion Graphics

- Bake animated effects (dissolves, energy flows, scans)  
- Generate frame-accurate image sequences for compositing and sprites  

---

### Procedural Material Caching

- Cache time-dependent shaders into textures  
- Eliminate runtime evaluation cost  
- Enable deterministic playback  

---

### High-Volume Batch Processing

Designed to handle:

- Hundreds of frames  
- Multiple materials  
- Multiple bake passes per material  

---

### Pipeline Integration

- Deterministic output structure  
- Consistent naming conventions  
- Color management control for pipeline compliance  

---

# Sprite Sheet Creator

## Overview

**Sprite Sheet Creator** is a Blender add-on module designed to convert frame-based image data into structured, production-ready sprite sheets.

This module is designed as the second stage of the pipeline:

**Bake → Image Sequence → Sprite Sheet**

It supports multiple input sources—including image directories, the Video Sequence Editor (VSE), and Compositor outputs—and assembles them into optimized sprite sheets.

Supports both **immediate and modal (non-blocking) execution**, depending on the source type.

---

## Architecture

- `operators.py` — Execution logic and batch processing  
- `processing.py` — Image loading and sprite assembly  
- `properties.py` — Configuration system  
- `ui.py` — Unified interface  

---

## Core Features

### Multi-Source Frame Input

#### Image Sequence (Directory)
- Load frames from a folder  
- Detect subdirectories for batch processing  
- Sorting and frame range control  

#### Video Sequence Editor (VSE)
- Renders frames from the VSE timeline  
- Supports single or multiple channels  

#### Compositor Output
- Renders frames through compositor nodes  
- Uses defined resolution per sprite cell  

---

### Batch Processing Engine (Directory Mode)

- Modal, timer-driven execution  
- Processes subdirectories automatically  
- One sprite sheet per directory  

---

### Sprite Sheet Assembly

- Grid layout (Columns × Rows)  
- Frame placement:
  - Left-to-right  
  - Top-to-bottom  
- Source frames are **resampled to match cell size**  
- Stops when grid capacity is reached  

---

### Image Processing Pipeline

- NumPy-backed pixel processing for efficient bulk image manipulation  
- Per-frame:
  - Load  
  - Rescale  
  - Write to atlas  

---

### Output System

- Multiple formats (PNG, EXR, etc.)  
- Auto naming and overwrite control  
- Flexible output paths  

---

## Output Structure

### Single Output

- <output_path>/<SpriteSheetName>.png

### Batch Directory Output

<root_directory>/
Sequence_A/
    Sequence_A.png

Sequence_B/
    Sequence_B.png


---

## Usage

1. Select source (Directory / VSE / Compositor)  
2. Set frame range  
3. Configure grid layout  
4. Define output settings  
5. Generate sprite sheet  

---

## Notes

- Designed to pair directly with **Sequenced Bake**  
- Optimized for:
  - Flipbook textures  
  - Sprite animation  
  - Real-time pipelines  

---

## Pipeline / Use Cases

### Game Development

- Flipbook textures  
- Particle atlases  
- Engine-ready sprite sheets  

---

### Sequenced Bake Integration

- Direct pipeline:
  - Bake → Image Sequence → Sprite Sheet  

---

### Batch Processing

- Process entire animation libraries  
- One folder = one sprite sheet  

---

## Community / Support

- **Discord**: https://discord.gg/uZw54mGKZH