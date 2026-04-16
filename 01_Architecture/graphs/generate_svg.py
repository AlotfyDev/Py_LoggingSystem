#!/usr/bin/env python3
"""
Graph Asset Generator

This script generates SVG files from Graphviz DOT files for the Logging System architecture.

Usage:
    python generate_svg.py              # Generate all SVGs
    python generate_svg.py --dot glob   # Generate specific pattern
    python generate_svg.py --all       # Also generate PNG
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Configuration
SCRIPT_DIR = Path(__file__).parent
GRAPHS_DIR = SCRIPT_DIR
OUTPUT_DIR = GRAPHS_DIR


def find_dot_files(pattern: str = "*.dot") -> list[Path]:
    """Find all DOT files in the graphs directory."""
    return list(GRAPHS_DIR.glob(pattern))


def render_dot_to_svg(dot_file: Path, output_dir: Optional[Path] = None) -> bool:
    """Render a DOT file to SVG using Graphviz dot command."""
    if output_dir is None:
        output_dir = dot_file.parent
    
    svg_file = output_dir / f"{dot_file.stem}.svg"
    
    try:
        result = subprocess.run(
            ["dot", "-Tsvg", str(dot_file), "-o", str(svg_file)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Generated: {svg_file.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error rendering {dot_file.name}: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ Error: Graphviz 'dot' command not found.")
        print("  Please install Graphviz: https://graphviz.org/download/")
        return False


def render_dot_to_png(dot_file: Path, output_dir: Optional[Path] = None) -> bool:
    """Render a DOT file to PNG using Graphviz dot command."""
    if output_dir is None:
        output_dir = dot_file.parent
    
    png_file = output_dir / f"{dot_file.stem}.png"
    
    try:
        result = subprocess.run(
            ["dot", "-Tpng", str(dot_file), "-o", str(png_file)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Generated: {png_file.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error rendering {dot_file.name}: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ Error: Graphviz 'dot' command not found.")
        return False


def render_dot_to_pdf(dot_file: Path, output_dir: Optional[Path] = None) -> bool:
    """Render a DOT file to PDF using Graphviz dot command."""
    if output_dir is None:
        output_dir = dot_file.parent
    
    pdf_file = output_dir / f"{dot_file.stem}.pdf"
    
    try:
        result = subprocess.run(
            ["dot", "-Tpdf", str(dot_file), "-o", str(pdf_file)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Generated: {pdf_file.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error rendering {dot_file.name}: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ Error: Graphviz 'dot' command not found.")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate SVG/PNG/PDF from Graphviz DOT files"
    )
    parser.add_argument(
        "--pattern",
        "-p",
        default="*.dot",
        help="Glob pattern for DOT files (default: *.dot)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output directory (default: same as DOT files)"
    )
    parser.add_argument(
        "--svg", "-s",
        action="store_true",
        default=True,
        help="Generate SVG files (default: True)"
    )
    parser.add_argument(
        "--png", 
        action="store_true",
        default=False,
        help="Generate PNG files"
    )
    parser.add_argument(
        "--pdf", 
        action="store_true",
        default=False,
        help="Generate PDF files"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generate all formats (SVG, PNG, PDF)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if Graphviz is installed"
    )
    
    args = parser.parse_args()
    
    # Check if Graphviz is installed
    try:
        subprocess.run(
            ["dot", "-V"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Error: Graphviz 'dot' command not found.")
        print()
        print("Please install Graphviz:")
        print("  macOS:    brew install graphviz")
        print("  Linux:    sudo apt-get install graphviz")
        print("  Windows:  https://graphviz.org/download/")
        print()
        sys.exit(1)
    
    if args.check:
        result = subprocess.run(["dot", "-V"], capture_output=True, text=True)
        print(f"✓ Graphviz installed: {result.stdout.strip()}")
        return
    
    # Generate all formats if --all is specified
    generate_svg = args.svg and not args.png and not args.pdf
    generate_png = args.png or args.all
    generate_pdf = args.pdf or args.all
    
    # Find DOT files
    dot_files = find_dot_files(args.pattern)
    
    if not dot_files:
        print(f"No DOT files found matching pattern: {args.pattern}")
        sys.exit(1)
    
    print(f"Found {len(dot_files)} DOT file(s)")
    print()
    
    success_count = 0
    fail_count = 0
    
    for dot_file in sorted(dot_files):
        if generate_svg:
            if render_dot_to_svg(dot_file, args.output):
                success_count += 1
            else:
                fail_count += 1
        
        if generate_png:
            if render_dot_to_png(dot_file, args.output):
                success_count += 1
            else:
                fail_count += 1
        
        if generate_pdf:
            if render_dot_to_pdf(dot_file, args.output):
                success_count += 1
            else:
                fail_count += 1
    
    print()
    print(f"Summary: {success_count} succeeded, {fail_count} failed")


if __name__ == "__main__":
    main()
