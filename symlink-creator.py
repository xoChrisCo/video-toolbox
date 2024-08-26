#!/usr/bin/env python3

"""
Symlink Creator for Tdarr

This script creates a folder of symlinks based on a list of file paths.
It's designed to help prepare a set of files for processing with Tdarr,
allowing you to create a temporary library from a specific list of files
rather than an entire folder.

Usage:
  python create_symlinks.py -f <input_file> [-o <output_folder>] [-q]
  python create_symlinks.py -h

Options:
  -h, --help            Show this help message and exit
  -f FILE, --file FILE  Input file containing list of file paths (one per line)
  -o DIR, --output DIR  Output directory for symlinks (default: ./symlinks)
  -q, --quiet           Quiet mode (suppress informational output)
"""

import argparse
import os
import sys

def create_symlinks(input_file, output_dir, quiet=False):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        if not quiet:
            print(f"Created output directory: {output_dir}")

    with open(input_file, 'r') as f:
        file_paths = f.read().splitlines()

    total_files = len(file_paths)
    successful_links = 0

    if not quiet:
        print(f"Found {total_files} file paths in the input file.")

    for file_path in file_paths:
        if not os.path.exists(file_path):
            if not quiet:
                print(f"Warning: File does not exist: {file_path}")
            continue

        filename = os.path.basename(file_path)
        link_path = os.path.join(output_dir, filename)

        try:
            os.symlink(file_path, link_path)
            successful_links += 1
        except FileExistsError:
            if not quiet:
                print(f"Warning: Symlink already exists: {link_path}")
        except Exception as e:
            if not quiet:
                print(f"Error creating symlink for {file_path}: {str(e)}")

    if not quiet:
        print(f"\nProcessing complete.")
        print(f"Total files processed: {total_files}")
        print(f"Successful symlinks created: {successful_links}")

def main():
    parser = argparse.ArgumentParser(description="Create symlinks for Tdarr processing")
    parser.add_argument('-f', '--file', required=True, help="Input file containing list of file paths")
    parser.add_argument('-o', '--output', default='./symlinks', help="Output directory for symlinks")
    parser.add_argument('-q', '--quiet', action='store_true', help="Quiet mode")

    args = parser.parse_args()

    create_symlinks(args.file, args.output, args.quiet)

if __name__ == "__main__":
    main()