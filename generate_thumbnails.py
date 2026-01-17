#!/usr/bin/env python3
"""
Generate thumbnails for all images in the full/ directory.

Usage:
    python generate_thumbnails.py --source ./full --dest ./thumbnails --size 600
"""

import argparse
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Installing Pillow...")
    import subprocess
    subprocess.run(['pip', 'install', 'Pillow'])
    from PIL import Image
    HAS_PIL = True


def generate_thumbnail(source_path, dest_path, size, quality):
    """Generate a thumbnail for an image."""
    try:
        with Image.open(source_path) as img:
            # Calculate new size maintaining aspect ratio
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # Convert RGBA to RGB for PNG with transparency
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as JPEG with quality
            img.save(dest_path, 'JPEG', quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"✗ Error: {source_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate thumbnails')
    parser.add_argument('--source', type=str, default='./', help='Source directory with full images')
    parser.add_argument('--dest', type=str, default='./.thumbnails', help='Destination directory for thumbnails')
    parser.add_argument('--size', type=int, default=600, help='Max thumbnail size (default: 600)')
    parser.add_argument('--quality', type=int, default=75, help='JPEG quality (default: 75)')
    args = parser.parse_args()

    source_dir = Path(args.source)
    dest_dir = Path(args.dest)

    if not source_dir.exists():
        print(f"✗ Source directory not found: {source_dir}")
        return

    supported_formats = ['.jpg', '.jpeg', '.png']

    # Find all images
    images = []
    for ext in supported_formats:
        images.extend(source_dir.rglob(f'*{ext}'))

    print(f"🔍 Found {len(images)} images in {source_dir}/")

    if len(images) == 0:
        print("No images found.")
        return

    # Generate thumbnails
    success = 0
    skipped = 0

    for i, source_path in enumerate(images):
        relative_path = source_path.relative_to(source_dir)
        dest_path = dest_dir / relative_path

        if "thumbnails" in str(source_path):
            continue

        # Check if thumbnail already exists and is newer
        if dest_path.exists():
            source_mtime = source_path.stat().st_mtime
            dest_mtime = dest_path.stat().st_mtime
            if dest_mtime > source_mtime:
                skipped += 1
                print(f"\r✓ Skipping existing [{int((i + 1) / len(images) * 100)}%]", end='', flush=True)
                continue

        # Generate thumbnail
        if generate_thumbnail(source_path, dest_path, args.size, args.quality):
            success += 1
            print(f"\r✓ Generating [{int((i + 1) / len(images) * 100)}%]", end='', flush=True)

    print(f"\r✓ Generated {success} thumbnails, {skipped} skipped     ")


if __name__ == '__main__':
    main()
