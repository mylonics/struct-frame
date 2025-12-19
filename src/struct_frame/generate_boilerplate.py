#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

"""
Boilerplate Code Generator for struct-frame

This script generates boilerplate code (frame parsers) from a frame_formats.proto file.
It uses the new header + payload architecture for composable frame formats.

Usage:
  # Update the boilerplate code in the src folder (for developers)
  python generate_boilerplate.py --update-src

  # Generate boilerplate for Python to a custom path
  python generate_boilerplate.py --frame_formats custom_formats.proto --py_path output/py
"""

import argparse
import os
import sys

# Add parent directory to path for imports when running as script
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from struct_frame.frame_format import parse_frame_formats
from struct_frame.polyglot_parser_py_gen import generate_py_polyglot_parser


def get_default_frame_formats_path():
    """Get the path to the default frame_formats.proto file included with the package"""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'frame_formats.proto')


def get_boilerplate_dir():
    """Get the path to the boilerplate directory in the package"""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'boilerplate')


def write_file(path, content):
    """Write content to a file, creating directories if needed"""
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Generated: {path}")


def generate_boilerplate_to_paths(frame_formats_file, py_path=None):
    """
    Generate frame parser boilerplate code from a frame_formats.proto file.
    
    Args:
        frame_formats_file: Path to the frame_formats.proto file
        py_path: Output directory for Python code (if None, skip Python generation)
    
    Returns:
        dict: Dictionary mapping output paths to generated content
    """
    collection = parse_frame_formats(frame_formats_file)
    files = {}
    
    if py_path:
        # Generate the polyglot parser
        name = os.path.join(py_path, "polyglot_parser.py")
        files[name] = generate_py_polyglot_parser(collection)
    
    return files


def update_src_boilerplate():
    """
    Update the boilerplate code in the src/struct_frame/boilerplate folder.
    
    This function generates frame parser code from the default frame_formats.proto
    file and writes it to the boilerplate directories. This is intended for developers
    who need to regenerate the boilerplate code after modifying the frame format
    definitions.
    """
    frame_formats_file = get_default_frame_formats_path()
    boilerplate_dir = get_boilerplate_dir()
    
    if not os.path.exists(frame_formats_file):
        print(f"Error: frame_formats.proto not found at {frame_formats_file}")
        return False
    
    print(f"Generating boilerplate from: {frame_formats_file}")
    print(f"Output directory: {boilerplate_dir}")
    
    files = generate_boilerplate_to_paths(
        frame_formats_file,
        py_path=os.path.join(boilerplate_dir, 'py'),
    )
    
    for path, content in files.items():
        write_file(path, content)
    
    print(f"\nSuccessfully generated {len(files)} boilerplate files")
    return True


def generate_to_custom_paths(args):
    """
    Generate frame parser code to custom output paths.
    
    This function generates frame parser code from a user-specified frame_formats.proto
    file and writes it to user-specified output directories.
    """
    frame_formats_file = args.frame_formats[0]
    
    if not os.path.exists(frame_formats_file):
        print(f"Error: frame_formats.proto not found at {frame_formats_file}")
        return False
    
    # Check that at least one output path is specified
    if not args.py_path:
        print("Error: --py_path must be specified")
        return False
    
    print(f"Generating boilerplate from: {frame_formats_file}")
    
    files = generate_boilerplate_to_paths(
        frame_formats_file,
        py_path=args.py_path[0] if args.py_path else None,
    )
    
    for path, content in files.items():
        write_file(path, content)
    
    print(f"\nSuccessfully generated {len(files)} files")
    return True


def main():
    parser = argparse.ArgumentParser(
        prog='generate_boilerplate',
        description='Generate frame parser boilerplate code from frame_formats.proto',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update the boilerplate code in the src folder (for developers)
  python generate_boilerplate.py --update-src
  
  # Generate boilerplate for Python to custom path
  python generate_boilerplate.py --frame_formats my_formats.proto --py_path output/py
"""
    )
    
    parser.add_argument('--update-src', action='store_true',
                        help='Update the boilerplate code in the src/struct_frame/boilerplate folder '
                             'using the default frame_formats.proto file')
    
    parser.add_argument('--frame_formats', nargs=1, type=str,
                        help='Path to a custom frame_formats.proto file')
    
    parser.add_argument('--py_path', nargs=1, type=str,
                        help='Output directory for Python frame parser code')
    
    args = parser.parse_args()
    
    # If --update-src is specified, update the boilerplate in the src folder
    if args.update_src:
        success = update_src_boilerplate()
        return 0 if success else 1
    
    # If --frame_formats is specified, generate to custom paths
    if args.frame_formats:
        success = generate_to_custom_paths(args)
        return 0 if success else 1
    
    # No valid arguments provided
    print("Error: Must specify either --update-src or --frame_formats")
    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
