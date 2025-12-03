#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

"""
Boilerplate Code Generator for struct-frame

This script generates boilerplate code (frame parsers) from a frame_formats.proto file.
It can be used in two modes:

1. Developer mode: Regenerate the boilerplate code in the src/struct_frame/boilerplate folder.
   This is useful for developers who want to update the boilerplate code after modifying
   the frame_formats.proto file.
   
   Usage: python generate_boilerplate.py --update-src

2. User mode: Generate boilerplate code to a custom output folder using a custom
   frame_formats.proto file. This allows users to define their own frame formats
   and generate the corresponding parser code.
   
   Usage: python generate_boilerplate.py --frame_formats custom_formats.proto \\
          --c_path output/c --ts_path output/ts --py_path output/py
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
from struct_frame.frame_parser_c_gen import generate_c_frame_parsers, generate_c_frame_parsers_multi
from struct_frame.frame_parser_py_gen import generate_py_frame_parsers, generate_py_frame_parsers_multi
from struct_frame.frame_parser_ts_gen import (generate_ts_frame_parsers, generate_js_frame_parsers,
                                               generate_ts_frame_parsers_multi, generate_js_frame_parsers_multi)
from struct_frame.frame_parser_cpp_gen import generate_cpp_frame_parsers, generate_cpp_frame_parsers_multi


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


def generate_boilerplate_to_paths(frame_formats_file, c_path=None, ts_path=None, 
                                   js_path=None, py_path=None, cpp_path=None,
                                   multi_file=True):
    """
    Generate frame parser boilerplate code from a frame_formats.proto file.
    
    Args:
        frame_formats_file: Path to the frame_formats.proto file
        c_path: Output directory for C code (if None, skip C generation)
        ts_path: Output directory for TypeScript code (if None, skip TS generation)
        js_path: Output directory for JavaScript code (if None, skip JS generation)
        py_path: Output directory for Python code (if None, skip Python generation)
        cpp_path: Output directory for C++ code (if None, skip C++ generation)
        multi_file: If True, generate multiple files per language (default: True)
    
    Returns:
        dict: Dictionary mapping output paths to generated content
    """
    formats = parse_frame_formats(frame_formats_file)
    files = {}
    
    if c_path:
        if multi_file:
            c_files = generate_c_frame_parsers_multi(formats)
            for filename, content in c_files.items():
                files[os.path.join(c_path, filename)] = content
        else:
            name = os.path.join(c_path, "frame_parsers_gen.h")
            files[name] = generate_c_frame_parsers(formats)
    
    if ts_path:
        if multi_file:
            ts_files = generate_ts_frame_parsers_multi(formats)
            for filename, content in ts_files.items():
                files[os.path.join(ts_path, filename)] = content
        else:
            name = os.path.join(ts_path, "frame_parsers_gen.ts")
            files[name] = generate_ts_frame_parsers(formats)
    
    if js_path:
        if multi_file:
            js_files = generate_js_frame_parsers_multi(formats)
            for filename, content in js_files.items():
                files[os.path.join(js_path, filename)] = content
        else:
            name = os.path.join(js_path, "frame_parsers_gen.js")
            files[name] = generate_js_frame_parsers(formats)
    
    if py_path:
        if multi_file:
            py_files = generate_py_frame_parsers_multi(formats)
            for filename, content in py_files.items():
                files[os.path.join(py_path, filename)] = content
        else:
            name = os.path.join(py_path, "frame_parsers_gen.py")
            files[name] = generate_py_frame_parsers(formats)
    
    if cpp_path:
        if multi_file:
            cpp_files = generate_cpp_frame_parsers_multi(formats)
            for filename, content in cpp_files.items():
                files[os.path.join(cpp_path, filename)] = content
        else:
            name = os.path.join(cpp_path, "frame_parsers_gen.hpp")
            files[name] = generate_cpp_frame_parsers(formats)
    
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
        c_path=os.path.join(boilerplate_dir, 'c'),
        ts_path=os.path.join(boilerplate_dir, 'ts'),
        js_path=os.path.join(boilerplate_dir, 'js'),
        py_path=os.path.join(boilerplate_dir, 'py'),
        cpp_path=os.path.join(boilerplate_dir, 'cpp')
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
    if not any([args.c_path, args.ts_path, args.js_path, args.py_path, args.cpp_path]):
        print("Error: At least one output path must be specified")
        print("Use --c_path, --ts_path, --js_path, --py_path, or --cpp_path")
        return False
    
    print(f"Generating boilerplate from: {frame_formats_file}")
    
    files = generate_boilerplate_to_paths(
        frame_formats_file,
        c_path=args.c_path[0] if args.c_path else None,
        ts_path=args.ts_path[0] if args.ts_path else None,
        js_path=args.js_path[0] if args.js_path else None,
        py_path=args.py_path[0] if args.py_path else None,
        cpp_path=args.cpp_path[0] if args.cpp_path else None
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
  
  # Generate boilerplate for specific languages to custom paths
  python generate_boilerplate.py --frame_formats my_formats.proto --py_path output/py
  
  # Generate boilerplate for all languages
  python generate_boilerplate.py --frame_formats my_formats.proto \\
      --c_path output/c --ts_path output/ts --js_path output/js \\
      --py_path output/py --cpp_path output/cpp
"""
    )
    
    parser.add_argument('--update-src', action='store_true',
                        help='Update the boilerplate code in the src/struct_frame/boilerplate folder '
                             'using the default frame_formats.proto file')
    
    parser.add_argument('--frame_formats', nargs=1, type=str,
                        help='Path to a custom frame_formats.proto file')
    
    parser.add_argument('--c_path', nargs=1, type=str,
                        help='Output directory for C frame parser code')
    
    parser.add_argument('--ts_path', nargs=1, type=str,
                        help='Output directory for TypeScript frame parser code')
    
    parser.add_argument('--js_path', nargs=1, type=str,
                        help='Output directory for JavaScript frame parser code')
    
    parser.add_argument('--py_path', nargs=1, type=str,
                        help='Output directory for Python frame parser code')
    
    parser.add_argument('--cpp_path', nargs=1, type=str,
                        help='Output directory for C++ frame parser code')
    
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
