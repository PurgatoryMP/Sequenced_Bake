# This file is part of Sequence Bake.
#
# Sequence Bake is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or any later version.
#
# Sequence Bake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sequence Bake. If not, see <http://www.gnu.org/licenses/>.

import bpy
import os
import re
import numpy as np
import subprocess
import platform


# ------------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------------

def _report(report_fn, level, message):
    if report_fn:
        report_fn(level, message)


# ------------------------------------------------------------------------
# DIRECTORY
# ------------------------------------------------------------------------

def load_directory_images(directory, start_frame=None, end_frame=None, reversed_order=False, report_fn=None):
    """
    Load images from a directory and sort them according to selected sorting mode.
    optionally slicing according to start_frame and end_frame.

    Args:
        directory (str): Path to the folder containing numeric image files.
        start_frame (int, optional): 1-based starting frame to load.
        end_frame (int, optional): 1-based ending frame to load.
        reversed_order (bool, optional): Reverse the frame order.
        report_fn (callable, optional): Blender report function to call with messages.

    Returns:
        list[bpy.types.Image]: Loaded Blender image objects.
    """
    images = []

    try:
        if not os.path.isdir(directory):
            _report(report_fn, {'ERROR'}, f"Directory not found: {directory}")
            return images

        try:
            files = os.listdir(directory)
        except Exception as e:
            _report(report_fn, {'ERROR'}, f"Failed to list directory contents: {directory}\nError: {e}")
            return images

        # Filter valid image files (any filename with extension)
        image_files = [
            f for f in files
            if os.path.splitext(f)[1]
        ]

        if not image_files:
            _report(report_fn, {'WARNING'}, f"No image files found in directory: {directory}")
            return images

        # Alphabetical sorting.
        try:
            if hasattr(bpy.context.scene, "sprite_sheet_props"):
                props = bpy.context.scene.sprite_sheet_props

                if props.use_alphabetical_sort:
                    if props.alphabetical_case_sensitive:
                        image_files.sort(reverse=props.alphabetical_reverse)
                    else:
                        image_files.sort(
                            key=lambda f: f.lower(),
                            reverse=props.alphabetical_reverse
                        )
                else:
                    image_files.sort(reverse=reversed_order)
            else:
                image_files.sort(reverse=reversed_order)

        except Exception as e:
            _report(report_fn, {'ERROR'}, f"Failed to sort image files in {directory}\nError: {e}")
            return images

        # Apply start/end frame slicing
        total_images = len(image_files)
        start_index = max(0, (start_frame - 1) if start_frame else 0)
        end_index = min(total_images, end_frame if end_frame else total_images)

        if start_index >= total_images:
            _report(report_fn, {'WARNING'}, f"start_frame {start_frame} exceeds number of images ({total_images}) in {directory}")
            return images

        if end_index <= 0:
            _report(report_fn, {'WARNING'}, f"end_frame {end_frame} is before the first image in {directory}")
            return images

        image_files = image_files[start_index:end_index]

        if not image_files:
            _report(report_fn, {'WARNING'}, f"No images to load after applying start/end frame slice: {start_frame}-{end_frame}")
            return images

        # Load images into Blender
        for filename in image_files:
            path = os.path.join(directory, filename)
            try:
                img = bpy.data.images.load(path)
                images.append(img)
            except RuntimeError as e:
                _report(report_fn, {'WARNING'}, f"Failed to load image: {filename}\nBlender Error: {e}")
            except Exception as e:
                _report(report_fn, {'ERROR'}, f"Unexpected error loading image: {filename}\nError: {e}")

    except Exception as e:
        _report(report_fn, {'ERROR'}, f"Unexpected failure in load_directory_images for {directory}\nError: {e}")

    return images



# ------------------------------------------------------------------------
# VSE
# ------------------------------------------------------------------------

def load_vse_frames(context, props, report_fn=None):
    scene = context.scene
    start = props.start_frame
    end = props.end_frame

    images = []

    seq = scene.sequence_editor
    if seq is None:
        seq = scene.sequence_editor_create()

    strips = seq.strips_all
    if not strips:
        _report(report_fn, {'ERROR'}, "No VSE strips found")
        return images

    if props.use_all_vse_channels:
        strips_to_render = [s for s in strips if not s.mute]
    else:
        strips_to_render = [s for s in strips if s.channel == props.vse_channel]

    if not strips_to_render:
        _report(report_fn, {'ERROR'}, "No VSE strips match the selected criteria")
        return images

    original_mute = {}
    if not props.use_all_vse_channels:
        for strip in strips:
            original_mute[strip] = strip.mute
            strip.mute = (strip.channel != props.vse_channel)

    temp_dir = bpy.app.tempdir
    os.makedirs(temp_dir, exist_ok=True)

    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format

    scene.render.image_settings.file_format = 'PNG'

    try:
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            temp_path = os.path.join(temp_dir, f"vse_frame_{frame:05d}.png")
            scene.render.filepath = temp_path

            bpy.ops.render.render(write_still=True)

            if os.path.exists(temp_path):
                img = bpy.data.images.load(temp_path)
                img.name = f"VSE_Frame_{frame}"
                images.append(img)
            else:
                _report(report_fn, {'WARNING'}, f"Failed to render VSE frame {frame}")

    finally:
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format

        if not props.use_all_vse_channels:
            for strip, mute in original_mute.items():
                strip.mute = mute

    return images


# ------------------------------------------------------------------------
# COMPOSITOR
# ------------------------------------------------------------------------

def load_compositor_frames(context, props):
    scene = context.scene
    start = props.start_frame
    end = props.end_frame

    images = []
    output_dir = bpy.path.abspath(props.compositor_output_path)
    os.makedirs(output_dir, exist_ok=True)

    original = {
        "filepath": scene.render.filepath,
        "format": scene.render.image_settings.file_format,
        "res_x": scene.render.resolution_x,
        "res_y": scene.render.resolution_y,
        "percent": scene.render.resolution_percentage,
    }

    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = props.image_width
    scene.render.resolution_y = props.image_height
    scene.render.resolution_percentage = 100

    try:
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            path = os.path.join(output_dir, f"compositor_frame_{frame:05d}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)

            if os.path.exists(path):
                img = bpy.data.images.load(path)
                img.name = f"Compositor_Frame_{frame}"
                images.append(img)
    finally:
        scene.render.filepath = original["filepath"]
        scene.render.image_settings.file_format = original["format"]
        scene.render.resolution_x = original["res_x"]
        scene.render.resolution_y = original["res_y"]
        scene.render.resolution_percentage = original["percent"]

    return images


# ------------------------------------------------------------------------
# IMAGE PROCESSING
# ------------------------------------------------------------------------

def process_images(images, props, output_name, report_fn=None):
    """
    Assemble a sprite sheet from a list of images, respecting start/end frames.
    Prints out current settings before processing.

    Args:
        images (list[bpy.types.Image]): Images to process
        props: Sprite sheet properties
        output_name (str): Base name for the sprite sheet
        report_fn (callable, optional): Blender report function
    """
    if not images:
        _report(report_fn, {'WARNING'}, "No images to process")
        return None

    # -----------------------------
    # Print current settings
    # -----------------------------
    settings_summary = (
        f"Sprite Sheet Settings:\n"
        f"  Source Type: {props.source_type}\n"
        f"  Start Frame: {props.start_frame}\n"
        f"  End Frame: {props.end_frame}\n"
        f"  Columns x Rows: {props.columns} x {props.rows}\n"
        f"  Cell Size: {props.image_width} x {props.image_height}\n"
        f"  File Name: {props.file_name or output_name}\n"
        f"  Image Format: {props.sprite_sheet_image_format}\n"
        f"  Use Alpha: {props.sprite_sheet_is_alpha}\n"
        f"  Overwrite Existing: {props.file_overwrite}\n"
        f"  Open Images After Save: {props.open_images}\n"
        f"  Open Output Directory: {props.open_output_directory}\n"
        f"  Reversed Order: {props.is_reversed}"
    )
    print(settings_summary)
    _report(report_fn, {'INFO'}, f"Starting sprite sheet generation: {output_name}")

    # -----------------------------
    # Clamp start/end frame
    # -----------------------------
    start_index = max(0, (props.start_frame - 1) if props.start_frame else 0)
    end_index = min(len(images), props.end_frame if props.end_frame else len(images))

    if start_index >= len(images):
        _report(report_fn, {'WARNING'}, f"start_frame ({props.start_frame}) exceeds number of images ({len(images)})")
        return None
    if end_index <= 0 or end_index <= start_index:
        _report(report_fn, {'WARNING'}, f"end_frame ({props.end_frame}) is invalid or before start_frame ({props.start_frame})")
        return None

    images = images[start_index:end_index]

    # -----------------------------
    # Prepare output directory
    # -----------------------------
    directory = bpy.path.abspath(
        props.directory if props.source_type == 'DIRECTORY'
        else props.vse_output_path if props.source_type == 'VSE'
        else props.compositor_output_path
    )

    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        _report(report_fn, {'ERROR'}, f"Failed to create output directory: {directory}\nError: {e}")
        return None

    # -----------------------------
    # Create sprite sheet
    # -----------------------------
    columns = props.columns
    rows = props.rows
    w = props.image_width
    h = props.image_height

    try:
        sprite = bpy.data.images.new(
            name=f"{output_name}_sprite_sheet",
            width=columns * w,
            height=rows * h,
            alpha=props.sprite_sheet_is_alpha
        )
    except Exception as e:
        _report(report_fn, {'ERROR'}, f"Failed to create new image for sprite sheet\nError: {e}")
        return None

    pixels = np.zeros((rows * h, columns * w, 4), dtype=np.float32)

    # -----------------------------
    # Populate sprite sheet
    # -----------------------------
    for idx, img in enumerate(images):
        if idx >= columns * rows:
            break

        try:
            x = (idx % columns) * w
            y = (idx // columns) * h

            ow, oh = img.size
            src = np.array(img.pixels[:], dtype=np.float32).reshape((oh, ow, 4))

            scaled = np.zeros((h, w, 4), dtype=np.float32)
            sx = w / ow
            sy = h / oh

            for j in range(h):
                for i in range(w):
                    scaled[j, i] = src[
                        min(int(j / sy), oh - 1),
                        min(int(i / sx), ow - 1)
                    ]

            pixels[
                pixels.shape[0] - y - h : pixels.shape[0] - y,
                x : x + w
            ] = scaled
        except Exception as e:
            _report(report_fn, {'WARNING'}, f"Failed to process image {img.name}\nError: {e}")

    sprite.pixels = pixels.flatten()

    # -----------------------------
    # Save sprite sheet
    # -----------------------------
    base_name = props.file_name.strip() or f"{output_name}_SpriteSheet"
    ext = f".{props.sprite_sheet_image_format}"
    path = os.path.join(directory, base_name + ext)

    if os.path.exists(path) and not props.file_overwrite:
        counter = 1
        while os.path.exists(path):
            path = os.path.join(directory, f"{base_name} ({counter}){ext}")
            counter += 1

    try:
        sprite.filepath_raw = path
        sprite.save()
        _report(report_fn, {'INFO'}, f"Sprite sheet saved: {path}")
    except Exception as e:
        _report(report_fn, {'ERROR'}, f"Failed to save sprite sheet: {path}\nError: {e}")
        return None

    return path
