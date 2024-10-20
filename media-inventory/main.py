#!/usr/bin/env python3
"""
Media Inventory Script

This script analyzes video files in a specified directory and its subdirectories,
extracting detailed metadata and generating comprehensive statistics about the media collection.

Usage:
    python main.py <root_folder> [options]

Arguments:
    root_folder             Root folder to search for video files

Options:
    -h, --help              Show this help message and exit
    -v LEVEL, --verbosity LEVEL
                            Verbosity level: 0 (quiet), 1 (normal), 2 (verbose) [default: 1]
    -o FILENAME, --output FILENAME
                            Custom output file name for the CSV report
    -d DIR, --output-dir DIR
                            Custom output directory for generated files
    --delimiter CHAR        Custom delimiter for CSV output [default: tab]
    --full-ffprobe          Include full ffprobe output in the Raw ffprobe output column
    --pretty-json           Output raw JSON data in multi-line format (default is single line)

Output:
    The script generates two main output files:
    1. A CSV file containing detailed information about each video file.
    2. A text file with overall statistics about the media collection.

    These files are saved in the 'output' directory by default, or in the
    specified custom output directory.

Features:
    - Recursive scanning of directories for video files
    - Extraction of detailed metadata using FFprobe
    - Generation of statistics on various aspects of the media collection:
      * File formats and sizes
      * Video codecs, resolutions, and bitrates
      * Audio tracks, languages, and formats
      * Subtitle information
    - Progress reporting during the scanning and analysis process
    - Customizable output options

Requirements:
    - Python 3.6+
    - FFprobe (part of the FFmpeg package)
    - Required Python packages: colorama, tqdm

Note:
    Ensure that FFprobe is installed and accessible in your system PATH.

Examples:
    Basic usage:
        python main.py /path/to/your/media/folder

    Verbose output with custom CSV filename:
        python main.py /path/to/your/media/folder -v 2 -o my_media_inventory.csv

    Use comma as CSV delimiter and include full FFprobe output:
        python main.py /path/to/your/media/folder --delimiter ',' --full-ffprobe

    Specify custom output directory:
        python main.py /path/to/your/media/folder -d /path/to/output/directory

For more information and updates, visit: https://github.com/yourusername/media-inventory
"""

import argparse
from file_processing import process_videos
from script_statistics import generate_statistics, process_audio_streams
from output import print_and_write_statistics
from colorama import init, Fore, Style # type: ignore
import os
from datetime import datetime
import time

from config import (
    DEFAULT_OUTPUT_FOLDER,
    VERBOSITY_QUIET,
    VERBOSITY_NORMAL,
    VERBOSITY_VERBOSE,
    CSV_DELIMITER
)

def main():
    parser = argparse.ArgumentParser(
        description="Media Inventory Script: Analyze video files and generate detailed metadata and statistics.",
        epilog="For more information and updates, visit: https://github.com/yourusername/media-inventory",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("root_folder", help="Root folder to search for video files")
    parser.add_argument("-v", "--verbosity", type=int, choices=[VERBOSITY_QUIET, VERBOSITY_NORMAL, VERBOSITY_VERBOSE], 
                        default=VERBOSITY_NORMAL,
                        help=f"Verbosity level: {VERBOSITY_QUIET} (quiet), {VERBOSITY_NORMAL} (normal), {VERBOSITY_VERBOSE} (verbose)")
    parser.add_argument("-o", "--output", help="Custom output file name for the CSV report")
    parser.add_argument("-d", "--output-dir", help="Custom output directory for generated files")
    parser.add_argument("--delimiter", default=CSV_DELIMITER, 
                        help=f"Custom delimiter for CSV output (default: {CSV_DELIMITER})")
    parser.add_argument("--full-ffprobe", action="store_true", 
                        help="Include full ffprobe output in the Raw ffprobe output column")
    parser.add_argument("--pretty-json", action="store_true", 
                        help="Output raw JSON data in multi-line format (default is single line)")
    
    args = parser.parse_args()

    init(autoreset=True)  # Initialize colorama

    if not os.path.isdir(args.root_folder):
        print(f"{Fore.RED}Error: The specified root folder does not exist.{Style.RESET_ALL}")
        return
    
    # Extract the folder name from the input path
    folder_name = os.path.basename(os.path.normpath(args.root_folder))

    # Sanitize the folder name for use in filenames
    sanitized_folder_name = ''.join(c for c in folder_name if c.isalnum() or c in (' ', '_', '-')).rstrip()

    output_folder = args.output_dir if args.output_dir else os.path.join(os.getcwd(), DEFAULT_OUTPUT_FOLDER)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    if args.output:
        base_name, ext = os.path.splitext(args.output)
        output_file = f"{timestamp} - {sanitized_folder_name}{ext}"
    else:
        output_file = f"{timestamp} - {sanitized_folder_name}.csv"
    
    stats_file = f"{timestamp} - {sanitized_folder_name} - statistics.txt"

    print(f"{Fore.CYAN}Starting Media Inventory process...{Style.RESET_ALL}")
    
    start_time = time.time()
    processed_files, failed_files, metadata_list = process_videos(args.root_folder, output_folder, output_file, args.verbosity, args.delimiter, args.full_ffprobe, args.pretty_json)
    
    stats = generate_statistics(args.root_folder, start_time, processed_files, failed_files, metadata_list)
    process_audio_streams(stats, metadata_list)
    print_and_write_statistics(stats, os.path.join(output_folder, stats_file))

    print(f"{Fore.CYAN}Media Inventory process completed.")
    print(f"CSV file saved as: {os.path.join(output_folder, output_file)} (Delimiter used: {'TAB' if args.delimiter == chr(9) else repr(args.delimiter)})")
    print(f"Statistics file saved as: {os.path.join(output_folder, stats_file)}{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Process interrupted by user. Exiting...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"{Fore.CYAN}Media Inventory script finished.{Style.RESET_ALL}")