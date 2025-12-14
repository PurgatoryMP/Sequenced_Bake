# Sequenced Bake

## Table of Contents
1. [About](#about)  
2. [Features](#features)  
   1. [Animated Texture Baking](#animated-texture-baking)  
   2. [Sprite Sheet Creation](#sprite-sheet-creation)  
3. [Installation](#installation)  
4. [Usage](#usage)  
   1. [Sequenced Bake Tool](#sequenced-bake-tool)  
   2. [Sprite Sheet Creator](#sprite-sheet-creator)  
5. [Configuration](#configuration)  
6. [Examples](#examples)  
7. [Contributing](#contributing)  
8. [License](#license)  
9. [Acknowledgements](#acknowledgements)

---

## About

**Sequenced Bake** is a Blender add-on designed to streamline the process of baking animated material sequences and generating sprite sheet assets. With intuitive UI panels and automated workflows, this tool provides efficient material sequence baking and sprite sheet compilation for use in game engines, 2D/3D tools, and other production pipelines.

This project includes two main modules:
- `sequenced_bake.py` — automated bake sequencing for textures across frame ranges  
- `sprite_sheet_creator.py` — generates optimized sprite sheets from baked sequences

---

## Features

### Animated Texture Baking
- Bake textures across a user-specified frame range  
- Supports Cycles bake types  
- Handles automatic file naming and sequential output  
- Optionally override image node file paths on the fly  
- Designed to integrate with Blender’s node editor workflows

### Sprite Sheet Creation
- Compile a sequence of images into a single sprite sheet  
- Customizable grid size, padding, and layout options  
- Output common sprite sheet formats suitable for game engines  
- Automatically orders frames based on naming or frame index

---

## Installation

1. Download the latest release of **Sequenced Bake**.
2. Open Blender and navigate to:
   `Edit → Preferences… → Add-ons`
3. Click **Install…** and select the downloaded ZIP file.
4. Enable the add-on by checking the box next to `Sequenced Bake`.
5. Save preferences to retain activation.

---

## Usage

### Sequenced Bake Tool

1. In the **Shader Editor**, select the material you want to bake.
2. Ensure your material contains an image texture node to bake into.
3. In the **Sequenced Bake** panel:
   - Set the **Image Folder** where source images are located (if overriding).
   - Toggle **Override Image Path** to automatically walk through a sequence.
   - Set start and end frames for the bake sequence.
4. Click **Animated Bake** to execute the bake over the specified frames.
5. Output images are automatically saved to your configured directory.

---

### Sprite Sheet Creator

1. After baking your texture sequence, open the **Sprite Sheet Creator** panel.
2. Select the folder containing your sequence of images.
3. Configure sheet settings:
   - Columns and rows  
   - Padding between frames  
   - Output resolution
4. Click **Generate Sprite Sheet**.
5. The sprite sheet will be saved to the selected output location.

---

## Configuration

Both tools expose user-configurable settings such as:

- Frame range (start/end)
- Output directories
- Image format (e.g., PNG, EXR)
- Naming conventions
- Sprite sheet grid layout settings

These settings can be accessed in the respective panel UI within Blender.

---

## Examples

**Animated Bake Example**

