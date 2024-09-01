#!/usr/bin/env python3
"""
Media Inventory and Transcode Simulation Script
===============================================

This script analyzes video files, extracting metadata using ffprobe and simulating Plex transcoding
using FFmpeg with hardware acceleration (Intel QuickSync on Windows/Linux, VideoToolbox on Mac).
The results are saved in a CSV file.

Usage:
    python3 media-inventory.py (-i <input_folder> | -f <file_list>) [-e <extensions>] [-o <output>] [-q] 
                               [-t <duration>] [-s <samples>] [-c <concat>] [-D <delimiter>]
                               [--hwaccel <accelerator>] [-d <debug_level>] [-r <resume_file>]

Arguments:
    -i,  --input          : Path to the folder containing video files to analyze.
    -f,  --file-list      : Path to a text file containing a list of video files to analyze.
    -e,  --extensions     : Comma-separated list of video file extensions to analyze (default: mkv,mp4,avi).
    -o,  --output         : Base output folder for the results (default: output).
    -q,  --quiet          : Enable quiet mode (less verbose output).
    -t,  --duration       : Duration of each transcode simulation in seconds (default: full file duration).
    -s,  --samples        : Number of transcode samples to take (default: 1, 0 to skip transcoding).
    -c,  --concat         : Separator for concatenating text in issue descriptions (default: '; ').
    -D,  --delimiter      : Delimiter for the CSV file (default: tab).
    --hwaccel             : Specify hardware accelerator to use (choices: qsv, videotoolbox, none; default: none).
    -d,  --debug          : Debug level: 0 (Error, default), 1 (Warning), 2 (Debug).
    -r,  --resume         : Resume processing from a file list.
    -h,  --help           : Display this help message.

Features:
    - Analyzes video files from a specified folder or file list
    - Extracts detailed metadata for each video file using ffprobe
    - Simulates Plex transcoding using FFmpeg with hardware acceleration
      (Intel QuickSync, VideoToolbox, or no acceleration)
    - Allows multiple transcode samples at different positions in the file
    - Calculates transcode speed ratio (transcode speed / video frame rate)
    - Categorizes transcode performance (Error, Failed, Low, Medium, High)
    - Saves results in a CSV file with a timestamp in the filename
    - Displays detailed progress information by default (use -q for less verbose output)
    - Customizable CSV delimiter and text concatenation separator
    - Supports resuming interrupted processing

Output:
    - Creates a CSV file in the specified output folder with a timestamp in the filename.
    - The CSV includes columns for various video metadata, transcode simulation results,
      transcode speed ratios, and performance categories.
    - Creates a file list text file for resuming the process from the last cursor position.
    - Creates an end report after the process is complete with a summary of the results.

Requirements:
    - Python 3.6+
    - ffprobe and ffmpeg installed and accessible in the system PATH
    - For Intel QuickSync: Running on a system with Intel QuickSync support
    - For VideoToolbox: Running on a Mac with Apple Silicon or recent Intel processor
    - Run pip3 install -r requirements.txt

Note: Ensure you have the necessary permissions to read the video files and write to the output directory.

Examples:
    1. Basic usage (analyze all supported video files in a folder):
       python3 media-inventory.py -i /path/to/videos

    2. Analyze specific file types with 3 transcode samples:
       python3 media-inventory.py -i /path/to/videos -e mkv,mp4 -s 3

    3. Use custom output folder and CSV delimiter:
       python3 media-inventory.py -i /path/to/videos -o /path/to/output -D ","

    4. Analyze files without transcoding simulation:
       python3 media-inventory.py -i /path/to/videos -s 0

    5. Analyze files with custom transcode duration and quiet mode:
       python3 media-inventory.py -i /path/to/videos -t 30 -q

    6. Analyze files using VideoToolbox hardware acceleration:
       python3 media-inventory.py -i /path/to/videos --hwaccel videotoolbox

    7. Resume processing from a file list:
       python3 media-inventory.py -r /path/to/file_list.txt

    8. Analyze files from a custom file list:
       python3 media-inventory.py -f /path/to/custom_file_list.txt
"""

import argparse
import os
import time
import csv
import sys
import traceback
from colorama import init, Fore, Style # type: ignore

from file_processing import process_file
from utils import create_output_folder, read_file_list, update_cursor, generate_file_list
from reporting import generate_report
from custom_help_formatter import CustomHelpFormatter

init(autoreset=True)

def main(input_path, extensions, base_output_dir, quiet, csv_delimiter, concat_separator, duration, samples, hwaccel, debug_level, resume_file=None, is_file_list=False):
    start_time = time.time()

    print(f"{Fore.MAGENTA}\n\n###  MEDIA INVENTORY AND TRANSCODE SIMULATION  ###\n")

    if resume_file:
        output_dir = os.path.dirname(resume_file)
        file_list, cursor = read_file_list(resume_file)
        total_files = len(file_list)
        print(f"{Fore.YELLOW}Resuming process from file {cursor + 1}")
    else:
        output_dir = create_output_folder(base_output_dir)
        print(f"{Fore.CYAN}Indexing media files in {input_path}")
        print(f"{Fore.CYAN}Using arguments: {' '.join(sys.argv[1:])}")
        
        if is_file_list:
            file_list, total_files = read_file_list(input_path), 0
            for file in file_list:
                if os.path.isfile(file) and file.lower().endswith(extensions):
                    total_files += 1
        else:
            file_list_path, total_files = generate_file_list(input_path, extensions, output_dir, ' '.join(sys.argv))
            file_list, cursor = read_file_list(file_list_path)

    if total_files == 0:
        print(f"{Fore.YELLOW}Warning: No files found matching the specified criteria.")
        print(f"Please check if the path is correct and contains files with these extensions: {', '.join(extensions)}")
        print(f"Path searched: {input_path}{Style.RESET_ALL}")
        return  # Exit the function early
    
    if not resume_file:
        print(f"{Fore.GREEN}Found {total_files} files to process")
        if not is_file_list:
            print(f"{Fore.YELLOW}To resume this process, use: python3 {sys.argv[0]} -r {file_list_path}")

    output_file = os.path.join(output_dir, "video_files.csv")
    print(f"{Fore.CYAN}Starting processing. Output file: {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=csv_delimiter)
        # Write headers
        headers = [
            "File", "Extension", "Path", "Filename", "Filesize", "Container Format",
            "Video Codec", "Codec Long Name", "Profile", "Level", "Bitrate", "Width", "Height",
            "Color Space", "Color Primaries", "Color Transfer", "Color Range", "Chroma Location",
            "Field Order", "Refs", "Bits Per Raw Sample", "Pix Format", "HDR", "Bit Depth",
            "Duration", "Frame Rate", "Audio Codecs", "Audio Codec Long Names", "Audio Channels",
            "Audio Sample Rates", "Audio Bitrates", "Audio Bit Depth", "Audio Stream Count",
            "Subtitle Languages", "Subtitle Formats", "Subtitle Stream Count",
            "Creation Date", "Modification Date", "Issues Detected", "Issue Description",
            "Unknown metadata", "Non-standard video codec", "Non-standard audio codec",
            "Problematic subtitle format", "High bitrate", "Low bitrate",
            "Non-standard resolution", "Non-standard frame rate", "High bit depth",
            "HDR content", "4K content", "Complex video profile", "Variable frame rate",
            "Interlaced content", "High subtitle stream count", "Uncommon container format",
            "Very high bitrate", "Multiple audio streams", "Dolby Vision Profile 5"
        ]

        for i in range(samples):
            headers.extend([f"Transcode Speed {i+1}", f"Speed Ratio {i+1}", f"Performance {i+1}"])
        
        writer.writerow(headers)
        
        stats = {
            "total": len(file_list),
            "processed": 0,
            "error": 0,
            "failed": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "no_issues": 0,
            "with_issues": 0
        }

        for i, file_path in enumerate(file_list[cursor:], start=cursor):
            print(f"\nProcessing file {i+1}/{len(file_list)}: {file_path}")
            result = process_file(file_path, duration, samples, concat_separator, hwaccel, debug_level)
            stats["processed"] += 1

             # Write the result to CSV
            writer.writerow(result)
            csvfile.flush()  # Ensure data is written to file
            
            # Update stats based on result
            if result[-2] == "Error":  # Assuming the second-to-last item is the error status
                stats["error"] += 1
            elif result[-2] == "Failed":
                stats["failed"] += 1
            elif result[-2] == "Low":
                stats["low"] += 1
            elif result[-2] == "Medium":
                stats["medium"] += 1
            elif result[-2] == "High":
                stats["high"] += 1

            if result[36] == "0":  # Assuming "Issue Detected" is at index 36
                stats["no_issues"] += 1
            else:
                stats["with_issues"] += 1
            
            # Update cursor in file_list.txt
            if not is_file_list:
                update_cursor(file_list_path, i + 1)

            elapsed_time = time.time() - start_time
            avg_time_per_file = elapsed_time / stats["processed"]
            estimated_time_remaining = avg_time_per_file * (len(file_list) - stats["processed"])

            print(f"Progress: {stats['processed']}/{len(file_list)} files processed")
            print(f"Elapsed time: {elapsed_time:.2f} seconds")
            print(f"Estimated time remaining: {estimated_time_remaining:.2f} seconds")
            
    end_time = time.time()
    total_time = end_time - start_time
    avg_time_per_file = total_time / stats["processed"] if stats["processed"] > 0 else 0

    generate_report(output_dir, output_file, stats, total_time, avg_time_per_file)

    print(f"\n{Fore.GREEN}Processing finished. Check {output_dir} for the full report.")

class CustomHelpFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        return text.splitlines()

    def _fill_text(self, text, width, indent):
        return ''.join(indent + line for line in text.splitlines(keepends=True))
    
def parse_arguments():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=CustomHelpFormatter,
        add_help=False
    )
    parser.add_argument(
        '-h', '--help',
        action='help',
        default=argparse.SUPPRESS,
        help='Show this help message and exit'
    )
    parser.add_argument("-r", "--resume", help="Resume processing from a file list")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input", help="Path to the folder containing video files to analyze")
    input_group.add_argument("-f", "--file-list", help="Path to a text file containing a list of video files to analyze")
    parser.add_argument("-e", "--extensions", default="mkv,mp4,avi", 
                        help="Comma-separated list of video file extensions to analyze (default: mkv,mp4,avi)")
    parser.add_argument("-o", "--output", default="output", 
                        help="Base output folder for the results (a timestamped subfolder will be created)")
    parser.add_argument("-D", "--delimiter", default="\t", 
                        help="Delimiter for the CSV file (default: tab)")
    parser.add_argument("-c", "--concat", default="; ", help="Separator for concatenating text (default: '; ')")
    parser.add_argument("-t", "--duration", type=float, default=None, 
                        help="Duration of each transcode simulation in seconds (default: full file duration)")
    parser.add_argument("-s", "--samples", type=int, default=1, 
                        help="Number of transcode samples to take (default: 1, 0 to skip transcoding)")
    parser.add_argument("--hwaccel", choices=['auto', 'none', 'cuda', 'qsv', 'videotoolbox'], default='none',
                        help="Specify hardware accelerator to use (default: none)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet mode (less verbose output)")
    parser.add_argument("-d", "--debug", type=int, choices=[0, 1, 2], default=0,
                        help="Debug level: 0 (Error, default), 1 (Warning), 2 (Debug)")
    
    args = parser.parse_args()

    # Validate arguments
    if args.resume and not os.path.isfile(args.resume):
        parser.error(f"Resume file does not exist: {args.resume}")
    if args.input and not os.path.isdir(args.input):
        parser.error(f"Input directory does not exist: {args.input}")
    if args.file_list and not os.path.isfile(args.file_list):
        parser.error(f"File list does not exist: {args.file_list}")
    if args.samples < 0:
        parser.error("Number of samples cannot be negative")
    if args.duration is not None and args.duration <= 0:
        parser.error("Duration must be greater than 0")
    if not args.extensions:
        parser.error("At least one file extension must be specified")
    if len(args.delimiter) != 1:
        parser.error("Delimiter must be a single character")

    return args

if __name__ == "__main__":
    args = parse_arguments()
    extensions = tuple(f".{ext.lower().strip()}" for ext in args.extensions.split(','))

    try:
        if args.resume:
            main(args.resume, None, os.path.dirname(os.path.dirname(args.resume)), 
                 args.quiet, args.delimiter, args.concat, args.duration, args.samples, 
                 args.hwaccel, args.debug, resume_file=args.resume)
        elif args.input:
            main(args.input, extensions, args.output, args.quiet, args.delimiter, 
                 args.concat, args.duration, args.samples, args.hwaccel, args.debug)
        elif args.file_list:
            main(args.file_list, extensions, args.output, args.quiet, args.delimiter, 
                 args.concat, args.duration, args.samples, args.hwaccel, args.debug, is_file_list=True)
    except Exception as e:
        if args.debug >= 1:
            print(f"{Fore.RED}An error occurred: {e}")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception traceback: {traceback.format_exc()}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
        print("If this error persists, please check your input and try again.")