#!/usr/bin/env python3
"""
Photo Gallery Build Script

Scans local images and generates gallery data with GitHub URLs.

Usage:
    python build_gallery.py --local ./photos --github 66RING/66RING --meta /tmp
"""

import os
import json
import re
import argparse
from pathlib import Path

_skip_dir = [".thumbnails"]
base_url = "https://raw.githubusercontent.com"

def parse_markdown(md_path):
    """Parse markdown file with optional YAML frontmatter."""
    content = md_path.read_text(encoding='utf-8')
    frontmatter = {}
    markdown_content = content.strip()

    # Check for YAML frontmatter
    frontmatter_pattern = r'^---\n(.*?)\n---\n(.*)$'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        # Parse YAML frontmatter
        yaml_text = match.group(1)
        for line in yaml_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip().lower()] = value.strip()
        markdown_content = match.group(2).strip()

    return frontmatter, markdown_content


def get_common_prefix(paths):
    """Find the common prefix of all paths."""
    if not paths:
        return ''

    # Split paths into parts
    split_paths = [p.split('/') for p in paths]

    # Find common prefix
    common = []
    for parts in zip(*split_paths):
        if len(set(parts)) == 1:
            common.append(parts[0])
        else:
            break

    return '/'.join(common)


def scan_directory(local_path):
    """Scan directory for images and corresponding markdown files, grouped by directory."""
    # Dictionary to group images by directory
    dir_groups = {}
    supported_formats = ['.jpg', '.jpeg', '.png']

    for entry in Path(local_path).rglob('*'):
        # Skip thumbnails directory
        if bool(set(_skip_dir) & set(entry.parts)):
            continue

        if entry.is_file():
            ext = entry.suffix.lower()
            if ext in supported_formats:
                relative_path = entry.relative_to(local_path)
                path_str = str(relative_path).replace('\\', '/')
                basename = entry.stem

                # Get directory name (parent folder)
                full_dir = str(relative_path.parent).replace('\\', '/') if relative_path.parent != Path('.') else ''

                # Look for matching .md file
                md_path = entry.parent / f"{basename}.md"
                metadata = {}
                description = None

                if md_path.exists():
                    metadata, description = parse_markdown(md_path)

                if full_dir not in dir_groups:
                    dir_groups[full_dir] = []

                dir_groups[full_dir].append({
                    'path': path_str,
                    'directory': full_dir,  # Will be updated later after finding common prefix
                    'title': metadata.get('title'),
                    'date': metadata.get('date'),
                    'location': metadata.get('location'),
                    'camera': metadata.get('camera'),
                    'lens': metadata.get('lens'),
                    'settings': metadata.get('settings'),
                    'description': description,
                })

    # Find and remove common prefix from directory names
    all_dirs = list(dir_groups.keys())
    common_prefix = get_common_prefix([d for d in all_dirs if d])

    if common_prefix:
        # Remove common prefix and leading slash
        for dir_name in dir_groups:
            if dir_name.startswith(common_prefix):
                new_dir = dir_name[len(common_prefix):].lstrip('/')
                # Update directory field for all images in this group
                for img in dir_groups[dir_name]:
                    img['directory'] = new_dir
            else:
                for img in dir_groups[dir_name]:
                    img['directory'] = dir_name
    else:
        # No common prefix, keep as is
        for dir_name in dir_groups:
            for img in dir_groups[dir_name]:
                img['directory'] = dir_name

    # Sort directories and flatten into list
    # Empty directory (root level) comes first
    start_idx = len(get_common_prefix(dir_groups.keys())) + 1
    sorted_dirs = sorted(
        [d for d in dir_groups.keys() if d],
        key=lambda d: (d[start_idx].isdigit(), d),
        reverse=True
    )
    if '' in dir_groups:
        sorted_dirs = [''] + sorted_dirs

    images = []
    for dir_name in sorted_dirs:
        images.extend(dir_groups[dir_name])

    return images


def generate_gallery_data(images, github_repo, branch, local_dir_name):
    """Generate gallery data with GitHub URLs."""
    username, repo = github_repo.split('/', 1) if '/' in github_repo else (github_repo, '')

    gallery_data = []
    for img in images:
        # Use GitHub raw content URL (more reliable)
        url = f"{base_url}/{username}/{repo}/{branch}"

        gallery_data.append({
            'thumbnail': f"{url}/.thumbnails/{img['path']}",
            'full': f"{url}/{img['path']}",
            **img
        })

    return gallery_data


def generate_stagger_css(offset_2col=24, offset_3col=48):
    """Generate CSS for horizontal staggered layout."""
    return f'''        /* Staggered effect - horizontal offset for columns */
        .gallery-item:nth-child(3n+2) {{
            margin-left: {offset_2col}px;
            margin-right: -{offset_2col}px;
        }}
        .gallery-item:nth-child(3n+3) {{
            margin-left: {offset_3col}px;
            margin-right: -{offset_3col}px;
        }}

        @media (max-width: 1200px) {{
            /* For 2 columns */
            .gallery-item:nth-child(3n+2) {{
                margin-left: 0;
                margin-right: 0;
            }}
            .gallery-item:nth-child(3n+3) {{
                margin-left: 0;
                margin-right: 0;
            }}
            .gallery-item:nth-child(even) {{
                margin-left: {offset_2col + 8}px;
                margin-right: -{offset_2col + 8}px;
            }}
        }}

        @media (max-width: 768px) {{
            /* For 1 column - no offset */
            .gallery-item:nth-child(3n+2),
            .gallery-item:nth-child(3n+3),
            .gallery-item:nth-child(even) {{
                margin-left: 0;
                margin-right: 0;
            }}
        }}'''


def generate_html(gallery_data, local_path, template_path=None, stagger_2col=24, stagger_3col=48, border_radius=6):
    """Generate HTML file from template with embedded gallery data."""

    # Default template path
    if template_path is None:
        script_dir = Path(__file__).parent
        template_path = script_dir / 'gallery_template.html'

    # Read template
    template = Path(template_path).read_text(encoding='utf-8')

    # Convert to JavaScript
    js_data = json.dumps(gallery_data, ensure_ascii=False)

    # Generate stagger CSS
    stagger_css = generate_stagger_css(stagger_2col, stagger_3col)

    # Replace placeholders
    html_content = template.replace('{{GALLERY_DATA}}', js_data)
    html_content = html_content.replace('{{STAGGER_CSS}}', stagger_css)
    html_content = html_content.replace('{{BORDER_RADIUS}}', str(border_radius))

    return html_content


def main():
    parser = argparse.ArgumentParser(description='Build photo gallery')
    parser.add_argument('--local', type=str, default="./", help='Local photos directory path')
    parser.add_argument('--github', type=str, default="66RING/66RING", help='GitHub repo (user/repo)')
    parser.add_argument('--meta', type=str, default='.', help='Metadata output directory (default: current dir)')
    parser.add_argument('--branch', type=str, default='gh-pages', help='GitHub branch (default: gh-pages)')
    parser.add_argument('--output', type=str, default='gallery.html', help='Output HTML file')
    parser.add_argument('--stagger-2col', type=int, default=24, help='Horizontal offset for 2nd column in px (default: 24)')
    parser.add_argument('--stagger-3col', type=int, default=48, help='Horizontal offset for 3rd column in px (default: 48)')
    parser.add_argument('--no-stagger', default=True, action='store_true', help='Disable staggered layout')
    parser.add_argument('--border-radius', type=int, default=2, help='Border radius for gallery items in px (default: 6)')
    args = parser.parse_args()

    local_path = Path(args.local).resolve()

    # Scan images
    print(f"🔍 Scanning: {local_path}")
    images = scan_directory(local_path)
    print(f"✓ Found {len(images)} images")

    # Generate gallery data
    gallery_data = generate_gallery_data(images, args.github, args.branch, local_path.name)

    # Save metadata
    meta_dir = Path(args.meta)
    meta_dir.mkdir(parents=True, exist_ok=True)

    meta_file = meta_dir / 'gallery-data.json'
    meta_file.write_text(json.dumps(gallery_data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"✓ Metadata saved to: {meta_file}")

    # Generate HTML
    stagger_2col = 0 if args.no_stagger else args.stagger_2col
    stagger_3col = 0 if args.no_stagger else args.stagger_3col
    html_content = generate_html(gallery_data, local_path.name,
                                  stagger_2col=stagger_2col,
                                  stagger_3col=stagger_3col,
                                  border_radius=args.border_radius)

    output_file = meta_dir / args.output
    output_file.write_text(html_content, encoding='utf-8')
    print(f"✓ Gallery saved to: {output_file}")

    # Show GitHub info
    username, repo = args.github.split('/', 1) if '/' in args.github else (args.github, '')
    print(f"\n📦 GitHub URLs:")
    print(f"   Thumbnail: https://raw.githubusercontent.com/{username}/{repo}/{args.branch}/.thumbnails/")
    print(f"   Full: https://raw.githubusercontent.com/{username}/{repo}/{args.branch}/")
    print(f"\n🌐 GitHub Pages URL:")
    print(f"   https://{username}.github.io/{repo}/")
    import generate_thumbnails
    generate_thumbnails.main()


if __name__ == '__main__':
    main()
