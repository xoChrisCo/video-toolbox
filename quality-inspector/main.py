#!/usr/bin/env python3

"""
Video Quality Inspection Tool

This script generates screenshot and video samples from video files in a given folder.
It can operate in two modes:
1. Single folder mode: Generate samples from a single input folder
2. Comparison mode: Compare transcoded video files with their originals

Usage:
  python3 main.py [-h] [-s SCREENSHOT_PATH] [-ns SCREENSHOT_SAMPLES]
                                   [-nv VIDEO_SAMPLES] [-l VIDEO_LENGTH] [-v] [-f]
                                   [-e EXTENSIONS [EXTENSIONS ...]] [-c COMPARE_PATH]
                                   [-lt LOWER_THRESHOLD] [-ut UPPER_THRESHOLD]
                                   [--ignore-thresholds] [--force-video-samples]
                                   [--force-all] [-d]
                                   input_path

Arguments:
  input_path            Path to the video files (or transcoded files in comparison mode)

Options:
  -h, --help            Show this help message and exit
  -s, --screenshot_path SCREENSHOT_PATH
                        Path to save screenshots and video samples (default: ./screenshots)
  -ns, --screenshot_samples SCREENSHOT_SAMPLES
                        Number of screenshot samples to take (default: 5)
  -nv, --video_samples VIDEO_SAMPLES
                        Number of video samples to take (default: 3)
  -l, --video_length VIDEO_LENGTH
                        Length of video samples in seconds (default: 7)
  -v, --verbose         Enable verbose output
  -f, --force           Force regeneration of samples, even if they already exist
  -e, --extensions EXTENSIONS [EXTENSIONS ...]
                        List of video file extensions to process (default: .mkv .mp4 .avi .mov .wmv .flv .webm .m4v .mpeg .mpg .m2ts .ts)
  -c, --compare_path COMPARE_PATH
                        Path to the original video files for comparison mode
  -lt, --lower_threshold LOWER_THRESHOLD
                        Lower bitrate threshold in percent for video generation (default: 60)
  -ut, --upper_threshold UPPER_THRESHOLD
                        Upper bitrate threshold in percent for video generation (default: 105)
  --ignore-thresholds   Ignore bitrate thresholds and create video samples for all files
  --force-video-samples Force creation of video samples even if bitrates are within thresholds
  --force-all           Force processing of all videos, even if bitrates are identical
  -d, --debug           Enable debug mode with additional output

Examples:
  1. Process all video files in a directory:
     python3 main.py /path/to/videos

  2. Process only MKV and AVI files, save screenshots in a custom directory:
     python3 main.py /path/to/videos -e mkv avi -s /path/to/custom/screenshots

  3. Compare transcoded videos with originals:
     python3 main.py /path/to/transcoded -c /path/to/original

  4. Generate more samples with longer video clips:
     python3 main.py /path/to/videos -ns 5 -nv 5 -l 10

  5. Use custom bitrate thresholds and force video sample creation:
     python3 main.py /path/to/videos -lt 80 -ut 120 --force-video-samples

  6. Process all videos, ignoring thresholds and existing samples:
     python3 main.py /path/to/videos --ignore-thresholds --force-all

  7. Debug mode with verbose output:
     python3 main.py /path/to/videos -v -d

Output:
- Screenshot samples and video samples saved in the specified screenshot_path
- Output folder structure: screenshot_path/input_folder/video_name
- Filename pattern: scr-52-00_02_40_331-original
    - scr: screenshot or vid for video sample
    - 52: bitrate ratio (transcoded/original)
    - 00_02_40_331: timestamp (hours_minutes_seconds_milliseconds)
    - original: for comparison mode, otherwise screen for single folder mode
- Summary of processed, skipped, and failed files
- Detailed logs if verbose or debug mode is enabled

Notes:
- Use the -f flag to force regeneration of all samples, deleting existing ones.
- In comparison mode, ensure that the directory structure in both input and compare paths match.
- Bitrate thresholds determine when video samples are generated in comparison mode.
- The --force-all flag processes all videos, even if their bitrates are identical.
"""

import argparse
import os
import sys
from colorama import Fore, Style # type: ignore
import colorama # type: ignore
import time
import textwrap
from video_processor import VideoProcessor
from utils import generate_summary, setup_logging
from datetime import timedelta
from constants import (
    DEFAULT_VIDEO_EXTENSIONS,
    DEFAULT_SCREENSHOT_SAMPLES,
    DEFAULT_VIDEO_SAMPLES,
    DEFAULT_VIDEO_LENGTH,
    DEFAULT_LOWER_THRESHOLD,
    DEFAULT_UPPER_THRESHOLD,
    DEFAULT_SAMPLE_PATH,
    DEFAULT_SAMPLE_CSV_PATH,
    ERROR_MESSAGES,
    Colors,
    Styles
)

def format_time(seconds):
    return str(timedelta(seconds=int(seconds)))

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Output:
        - Screenshot samples and video samples saved in the specified screenshot_path
        - Summary of processed, skipped, and failed files
        - Detailed logs if verbose or debug mode is enabled

        Notes:
        - Use the -f flag to force regeneration of all samples, deleting existing ones.
        - In comparison mode, ensure that the directory structure in both input and compare paths match.
        - Bitrate thresholds determine when video samples are generated in comparison mode.
        - The --force-all flag processes all videos, even if their bitrates are identical.
        '''))
    
    parser.add_argument("input_path", help="Path to the video files (or transcoded files in comparison mode)")
    parser.add_argument("-c", "--compare_path", help="Path to the original video files for comparison mode")
    parser.add_argument("-s", "--screenshot_path", default=DEFAULT_SAMPLE_PATH, help=f"Path to save screenshots and video samples (default: {DEFAULT_SAMPLE_PATH})")
    parser.add_argument("--csv_path", default=DEFAULT_SAMPLE_CSV_PATH, help=f"Path to save the CSV file (default: {DEFAULT_SAMPLE_CSV_PATH})")
    parser.add_argument("-ns", "--screenshot_samples", type=int, default=DEFAULT_SCREENSHOT_SAMPLES, help=f"Number of screenshot samples to take (default: {DEFAULT_SCREENSHOT_SAMPLES})")
    parser.add_argument("-nv", "--video_samples", type=int, default=DEFAULT_VIDEO_SAMPLES, help=f"Number of video samples to take (default: {DEFAULT_VIDEO_SAMPLES})")
    parser.add_argument("-l", "--video_length", type=int, default=DEFAULT_VIDEO_LENGTH, help=f"Length of video samples in seconds (default: {DEFAULT_VIDEO_LENGTH})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-f", "--force", action="store_true", help="Force regeneration of samples, even if they already exist")
    parser.add_argument("--force-all", action="store_true", help="Force processing of all videos, even if bitrates are identical")
    parser.add_argument("-e", "--extensions", nargs='+', default=DEFAULT_VIDEO_EXTENSIONS,
                        help=f"List of video file extensions to process (default: {' '.join(DEFAULT_VIDEO_EXTENSIONS)})")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode with additional output")
    parser.add_argument("-lt", "--lower_threshold", type=float, default=DEFAULT_LOWER_THRESHOLD,
                        help=f"Lower bitrate threshold in percent (default: {DEFAULT_LOWER_THRESHOLD})")
    parser.add_argument("-ut", "--upper_threshold", type=float, default=DEFAULT_UPPER_THRESHOLD,
                        help=f"Upper bitrate threshold in percent (default: {DEFAULT_UPPER_THRESHOLD})")
    parser.add_argument("--ignore-thresholds", action="store_true",
                        help="Ignore bitrate thresholds and create video samples for all files")
    parser.add_argument("--force-video-samples", action="store_true",
                        help="Force creation of video samples even if bitrates are within thresholds")
    
    return parser.parse_args()

def validate_paths(input_path, compare_path=None):
    if not os.path.exists(input_path):
        print(f"{Colors.RED}{ERROR_MESSAGES['path_not_exist'].format(path=input_path)}{Colors.RESET}")
        sys.exit(1)

    if compare_path and not os.path.exists(compare_path):
        print(f"{Colors.RED}{ERROR_MESSAGES['path_not_exist'].format(path=compare_path)}{Colors.RESET}")
        sys.exit(1)

def main():
    colorama.init(autoreset=True)
    
    start_time = time.time()

    args = parse_arguments()
    
    # Ensure all extensions start with a dot
    args.extensions = tuple('.' + ext.lstrip('.').lower() for ext in args.extensions)

    validate_paths(args.input_path, args.compare_path)

    setup_logging(args.verbose, args.debug)

    # Adjust args for single folder mode
    if not args.compare_path:
        args.transcode_path = args.input_path
        args.original_path = None
    else:
        args.transcode_path = args.input_path
        args.original_path = args.compare_path

    # Print the execution summary
    print(generate_summary(args))
    print(f"\n{Colors.GREEN}{Styles.BOLD}Starting the video processing...{Colors.RESET}\n")

    # Initialize and run the VideoProcessor
    processor = VideoProcessor(args)
    processor.run()

    total_elapsed_time = time.time() - start_time
    formatted_time = format_time(total_elapsed_time)
    print(f"{Colors.CYAN}Total processing time: {formatted_time}{Colors.RESET}")

if __name__ == "__main__":
    main()