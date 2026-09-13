"""Processing helpers for Sprite Sheet Creator."""

import os
import platform
import subprocess

import bpy
import numpy as np


IMAGE_FORMAT_MAP = {
    "png": "PNG",
    "jpeg": "JPEG",
    "bmp": "BMP",
    "tiff": "TIFF",
    "tga": "TGA",
    "openexr": "OPEN_EXR",
    "hdr": "HDR",
    "cineon": "CINEON",
    "dpx": "DPX",
}


def _report(report_fn, level, message):
    """Send a message through a Blender report callback when available."""
    if report_fn:
        report_fn(level, message)
    else:
        print(f"[Sprite Sheet Creator] {message}")


def _read_image_pixels(image):
    """Read an image's RGBA pixels into a NumPy array efficiently."""
    width, height = image.size
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    return buffer.reshape((height, width, 4))


def _resize_nearest(src, width, height):
    """Resize an RGBA array with nearest-neighbor sampling using NumPy."""
    source_height, source_width = src.shape[:2]
    x_indices = np.minimum(
        (np.arange(width, dtype=np.float32) * source_width / width).astype(np.int32),
        source_width - 1,
    )
    y_indices = np.minimum(
        (np.arange(height, dtype=np.float32) * source_height / height).astype(np.int32),
        source_height - 1,
    )
    return src[y_indices[:, None], x_indices[None, :]]


def _open_output_directory(path):
    """Open a directory using the host operating system."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        print(f"[Sprite Sheet Creator] Failed to open directory '{path}': {exc}")


def _show_image_in_editor(image):
    """Show an image in the first available Image Editor area."""
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.spaces.active.image = image
                area.tag_redraw()
                return True
    print("[Sprite Sheet Creator] No Image Editor area is currently open.")
    return False


def load_directory_images(
    directory,
    start_frame=None,
    end_frame=None,
    reversed_order=False,
    report_fn=None,
):
    """Load image files from a directory in the configured order."""
    images = []
    image_extensions = {
        ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".tga",
        ".exr", ".hdr", ".cin", ".dpx", ".webp",
    }

    try:
        if not os.path.isdir(directory):
            _report(report_fn, {"ERROR"}, f"Directory not found: {directory}")
            return images

        try:
            files = os.listdir(directory)
        except Exception as exc:
            _report(
                report_fn,
                {"ERROR"},
                f"Failed to list directory contents: {directory}\nError: {exc}",
            )
            return images

        image_files = [
            filename
            for filename in files
            if os.path.splitext(filename)[1].lower() in image_extensions
        ]

        if not image_files:
            _report(report_fn, {"WARNING"}, f"No image files found in directory: {directory}")
            return images

        props = getattr(bpy.context.scene, "sprite_sheet_props", None)
        if props and props.use_alphabetical_sort:
            key = None if props.alphabetical_case_sensitive else str.lower
            image_files.sort(
                key=key,
                reverse=props.alphabetical_reverse,
            )
        else:
            image_files.sort(reverse=reversed_order)

        total_images = len(image_files)
        start_index = max(0, (start_frame - 1) if start_frame else 0)
        end_index = min(total_images, end_frame if end_frame else total_images)

        if start_index >= total_images:
            _report(
                report_fn,
                {"WARNING"},
                f"start_frame {start_frame} exceeds number of images ({total_images}) in {directory}",
            )
            return images

        image_files = image_files[start_index:end_index]
        if reversed_order:
            image_files.reverse()

        for filename in image_files:
            path = os.path.join(directory, filename)
            try:
                images.append(bpy.data.images.load(path, check_existing=False))
            except RuntimeError as exc:
                _report(
                    report_fn,
                    {"WARNING"},
                    f"Failed to load image: {filename}\nBlender Error: {exc}",
                )
            except Exception as exc:
                _report(
                    report_fn,
                    {"ERROR"},
                    f"Unexpected error loading image: {filename}\nError: {exc}",
                )
    except Exception as exc:
        _report(
            report_fn,
            {"ERROR"},
            f"Unexpected failure in load_directory_images for {directory}\nError: {exc}",
        )

    return images


def load_vse_frames(context, props, report_fn=None):
    """Render the requested VSE frames into temporary Blender images."""
    scene = context.scene
    images = []
    seq = scene.sequence_editor_create()
    strips = seq.strips_all

    if not strips:
        _report(report_fn, {"ERROR"}, "No VSE strips found")
        return images

    if props.use_all_vse_channels:
        strips_to_render = [strip for strip in strips if not strip.mute]
    else:
        strips_to_render = [
            strip for strip in strips
            if strip.channel == props.vse_channel and not strip.mute
        ]

    if not strips_to_render:
        _report(report_fn, {"ERROR"}, "No VSE strips match the selected criteria")
        return images

    original_mute = {}
    if not props.use_all_vse_channels:
        for strip in strips:
            original_mute[strip] = strip.mute
            strip.mute = strip.channel != props.vse_channel

    temp_dir = bpy.app.tempdir
    os.makedirs(temp_dir, exist_ok=True)
    original_filepath = scene.render.filepath
    original_format = scene.render.image_settings.file_format

    scene.render.image_settings.file_format = "PNG"

    try:
        for frame in range(props.start_frame, props.end_frame + 1):
            scene.frame_set(frame)
            temp_path = os.path.join(temp_dir, f"vse_frame_{frame:05d}.png")
            scene.render.filepath = temp_path
            bpy.ops.render.render(write_still=True)

            if os.path.exists(temp_path):
                image = bpy.data.images.load(temp_path, check_existing=False)
                image.name = f"VSE_Frame_{frame}"
                images.append(image)
            else:
                _report(report_fn, {"WARNING"}, f"Failed to render VSE frame {frame}")
    finally:
        scene.render.filepath = original_filepath
        scene.render.image_settings.file_format = original_format
        for strip, mute in original_mute.items():
            strip.mute = mute

    if props.is_reversed:
        images.reverse()
    return images


def load_compositor_frames(context, props, report_fn=None):
    """Render compositor frames into temporary Blender images."""
    scene = context.scene
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

    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = props.image_width
    scene.render.resolution_y = props.image_height
    scene.render.resolution_percentage = 100

    try:
        for frame in range(props.start_frame, props.end_frame + 1):
            scene.frame_set(frame)
            path = os.path.join(output_dir, f"compositor_frame_{frame:05d}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)

            if os.path.exists(path):
                image = bpy.data.images.load(path, check_existing=False)
                image.name = f"Compositor_Frame_{frame}"
                images.append(image)
            else:
                _report(report_fn, {"WARNING"}, f"Failed to render compositor frame {frame}")
    finally:
        scene.render.filepath = original["filepath"]
        scene.render.image_settings.file_format = original["format"]
        scene.render.resolution_x = original["res_x"]
        scene.render.resolution_y = original["res_y"]
        scene.render.resolution_percentage = original["percent"]

    if props.is_reversed:
        images.reverse()
    return images


def _remove_temporary_images(images):
    """Remove specified image datablocks when they are no longer needed."""
    for image in list(images):
        try:
            if image and image.name in bpy.data.images and image.users == 0:
                bpy.data.images.remove(image)
        except (ReferenceError, RuntimeError) as exc:
            print(f"[Sprite Sheet Creator] Failed to remove temporary image: {exc}")


def process_images(images, props, output_name, report_fn=None):
    """Assemble, save, and optionally display a sprite sheet."""
    if not images:
        _report(report_fn, {"WARNING"}, "No images to process")
        return None

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
    _report(report_fn, {"INFO"}, f"Starting sprite sheet generation: {output_name}")

    selected_images = list(images)
    if not selected_images:
        _report(report_fn, {"WARNING"}, "No images remain after source frame selection")
        return None
    directory = bpy.path.abspath(
        props.directory
        if props.source_type == "DIRECTORY"
        else props.vse_output_path
        if props.source_type == "VSE"
        else props.compositor_output_path
    )

    if not directory:
        _report(report_fn, {"ERROR"}, "No sprite sheet output directory specified")
        return None

    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as exc:
        _report(
            report_fn,
            {"ERROR"},
            f"Failed to create output directory: {directory}\nError: {exc}",
        )
        return None

    columns = props.columns
    rows = props.rows
    width = props.image_width
    height = props.image_height
    sheet_width = columns * width
    sheet_height = rows * height

    try:
        sprite = bpy.data.images.new(
            name=f"{output_name}_sprite_sheet",
            width=sheet_width,
            height=sheet_height,
            alpha=props.sprite_sheet_is_alpha,
        )
        sprite.file_format = IMAGE_FORMAT_MAP[props.sprite_sheet_image_format]
    except Exception as exc:
        _report(report_fn, {"ERROR"}, f"Failed to create sprite sheet image\nError: {exc}")
        return None

    pixels = np.zeros((sheet_height, sheet_width, 4), dtype=np.float32)
    if not props.sprite_sheet_is_alpha:
        pixels[:, :, 3] = 1.0

    for index, image in enumerate(selected_images[: columns * rows]):
        try:
            x = (index % columns) * width
            y = (index // columns) * height
            source = _read_image_pixels(image)
            scaled = _resize_nearest(source, width, height)

            if not props.sprite_sheet_is_alpha:
                scaled = scaled.copy()
                scaled[:, :, 3] = 1.0

            target_y0 = sheet_height - y - height
            pixels[target_y0:target_y0 + height, x:x + width] = scaled
        except Exception as exc:
            _report(
                report_fn,
                {"WARNING"},
                f"Failed to process image {image.name}\nError: {exc}",
            )

    try:
        sprite.pixels.foreach_set(pixels.ravel())
        sprite.update()
    except Exception as exc:
        _report(report_fn, {"ERROR"}, f"Failed to write sprite sheet pixels\nError: {exc}")
        if sprite.name in bpy.data.images:
            bpy.data.images.remove(sprite)
        return None

    base_name = props.file_name.strip() or f"{output_name}_SpriteSheet"
    extension = props.sprite_sheet_image_format
    path = os.path.join(directory, f"{base_name}.{extension}")

    if os.path.exists(path) and not props.file_overwrite:
        counter = 1
        while os.path.exists(path):
            path = os.path.join(directory, f"{base_name} ({counter}).{extension}")
            counter += 1

    try:
        sprite.filepath_raw = path
        sprite.file_format = IMAGE_FORMAT_MAP[props.sprite_sheet_image_format]
        sprite.save()
        _report(report_fn, {"INFO"}, f"Sprite sheet saved: {path}")
    except Exception as exc:
        _report(report_fn, {"ERROR"}, f"Failed to save sprite sheet: {path}\nError: {exc}")
        return None

    if props.open_images:
        _show_image_in_editor(sprite)

    if props.open_output_directory:
        _open_output_directory(directory)

    if props.clear_generated_images and props.source_type in {"VSE", "COMPOSITOR"}:
        _remove_temporary_images(selected_images)

    return path
