#!/usr/bin/env python3
"""
HDR to SDR Video Transcoding Script
===================================

This script automates the process of transcoding HDR (High Dynamic Range) videos
to SDR (Standard Dynamic Range) format, specifically converting from bt2020nc
color profile to bt709. It's designed to improve compatibility with Plex media server,
addressing issues with slow playback and scrubbing of HDR content.

Usage:
    python3 transcode-hdr-to-sdr.py (-i <input_folder> | -f <file_list>) [-p <preset_file>] [-o <output_folder>] [-q] [-h]

Arguments:
    -i,  --input          : Path to the folder containing video files to transcode (working folder).
    -f,  --file_list      : Path to the text file containing the list of files to transcode.
    -p,  --preset         : Path to the HandBrake preset file (default: '4k mkv HDR to SDR.json' in the script's directory).
    -o,  --output         : Custom output folder for transcoded files (default: same as input files).
    -q,  --quiet          : Enable quiet mode (less verbose output).
    -h,  --help           : Display this help message.

Note: Either -i or -f must be provided. If both are given, -f takes precedence.

Key features:
    - Processes a list of files specified in the file list
    - Uses HandBrakeCLI for transcoding, maintaining all metadata, subtitles, and audio tracks
    - Provides real-time progress updates including ETA and FPS
    - Logs detailed information for each transcoding operation
    - Supports both ARM Macs and Windows
    - Continues where it stopped if aborted (looking for *.to_be_deleted files)

Note: Ensure HandBrakeCLI is installed and accessible in your system PATH.

Author: Christopher Conradi
Date: 2024-08-07
Version: 4
"""

import argparse
import os
import sys
import subprocess
import os
import time
import re
import argparse
from datetime import datetime, timedelta
from tqdm import tqdm # type: ignore
from colorama import init, Fore, Style # type: ignore

# Initialize colorama
init(autoreset=True)

def parse_time(time_str):
    hours, minutes, seconds = time_str.split('h')[0], time_str.split('h')[1].split('m')[0], time_str.split('m')[1].split('s')[0]
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

def format_eta(seconds):
    return str(timedelta(seconds=int(seconds))).split('.')[0].zfill(8).replace(':', 'h', 1).replace(':', 'm', 1) + 's'

def transcode_file(input_file, output_folder, preset_file, idx, total_files, quiet):
    # Define output file names
    output_file = os.path.join(output_folder, os.path.basename(input_file).rsplit('.', 1)[0] + ' SDR Handbrake.mkv')
    temp_file = output_file.rsplit('.', 1)[0] + '.temp.mkv'

    # Skip if the output file already exists
    if os.path.exists(output_file):
        if not quiet:
            tqdm.write(f"{Fore.GREEN}Processing file {idx + 1}/{total_files}: {input_file} - Skipped (already exists)")
        return

    # Remove temp file if it exists
    if os.path.exists(temp_file):
        if not quiet:
            print(f"Removing existing temp file: {temp_file}")
        os.remove(temp_file)

    # HandBrakeCLI command
    command = [
        'HandBrakeCLI',
        '--preset-import-file', preset_file,
        '--preset', '4k mkv HDR to SDR',
        '-i', input_file,
        '-o', temp_file,
    ]

    # Output the command being run
    print(f"\n{Fore.CYAN}Running command:")
    print(f"{Fore.YELLOW}{' '.join(command)}")

    # Create a timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_folder = os.path.join(os.path.dirname(input_file), 'logs')
    os.makedirs(logs_folder, exist_ok=True)
    log_file = os.path.join(logs_folder, f"{timestamp}_{os.path.basename(input_file)}_handbrake.log")

    # Execute the command and log progress
    with open(log_file, 'w') as log:
        log.write(f"Starting transcoding: {input_file}\n")
        log.write(f"Command: {' '.join(command)}\n")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        start_time = time.time()
        current_task = 1
        total_tasks = 2  # Assuming 2-pass encoding, adjust if needed

        for line in process.stdout:
            log.write(line)
            if line.startswith('Encoding:'):
                try:
                    # Parse the basic information
                    match = re.search(r'Encoding: task (\d+) of (\d+), ([\d.]+) %', line)
                    if match:
                        current_task = int(match.group(1))
                        total_tasks = int(match.group(2))
                        progress = float(match.group(3))
                        
                        # Check if there's additional FPS and ETA information
                        fps_match = re.search(r'\(([\d.]+) fps, avg ([\d.]+) fps, ETA ([\dh]+m[\d]+s)\)', line)
                        if fps_match:
                            current_fps = float(fps_match.group(1))
                            avg_fps = float(fps_match.group(2))
                            eta_seconds = parse_time(fps_match.group(3))
                            eta_formatted = format_eta(eta_seconds)
                            status = f"Task {current_task}/{total_tasks} - {progress:.2f}% ({current_fps:.2f} fps, avg {avg_fps:.2f} fps, ETA: {eta_formatted})"
                        else:
                            status = f"Task {current_task}/{total_tasks} - {progress:.2f}%"
                        
                        if not quiet:
                            print(f"\rProcessing file {idx + 1}/{total_files}: {os.path.basename(input_file)} - {status}", end='', flush=True)
                except Exception as e:
                    log.write(f"Error parsing line: {line}\n")
                    log.write(f"Error details: {str(e)}\n")
                    if not quiet:
                        print(f"\rProcessing file {idx + 1}/{total_files}: {os.path.basename(input_file)} - Error parsing output", end='', flush=True)
        
        process.wait()
        stderr_output = process.stderr.read()
        log.write(stderr_output)

        end_time = time.time()
        duration = end_time - start_time

        if process.returncode == 0:
            if os.path.exists(temp_file):
                os.rename(temp_file, output_file)
                os.rename(input_file, input_file + '.to_be_deleted')
                if not quiet:
                    print(f"\r{Fore.GREEN}Processing file {idx + 1}/{total_files}: {os.path.basename(input_file)} - Completed in {format_eta(duration)}")
                log.write(f"Transcoding completed: {output_file}\n")
        else:
            if not quiet:
                print(f"\r{Fore.RED}Processing file {idx + 1}/{total_files}: {os.path.basename(input_file)} - Failed")
                if stderr_output:
                    print(f"{Fore.RED}{stderr_output}")
            log.write(f"Failed to transcode: {input_file}\n")

def main(args):
    # Determine the working folder
    if args.file_list:
        working_folder = os.path.dirname(args.file_list)
    elif args.input:
        working_folder = args.input
    else:
        print("Error: Either -i/--input or -f/--file_list must be provided.")
        sys.exit(1)

    # Set default values based on the working folder
    if not args.preset:
        # Default preset file is in the same directory as the script
        args.preset = os.path.join(os.path.dirname(os.path.abspath(__file__)), '4k mkv HDR to SDR.json')
    if not args.file_list:
        args.file_list = os.path.join(working_folder, 'hdr-video-files.txt')

    # Check if the required files exist
    if not os.path.exists(args.file_list):
        print(f"Error: File list not found: {args.file_list}")
        sys.exit(1)
    if not os.path.exists(args.preset):
        print(f"Error: Preset file not found: {args.preset}")
        sys.exit(1)

    # Read the list of files
    with open(args.file_list, 'r') as file:
        files = [line.strip() for line in file.readlines() if not line.strip().startswith('#')]

    # Transcode each file and log progress
    total_files = len(files)
    for idx, input_file in enumerate(files):
        transcode_file(input_file, args.output or os.path.dirname(input_file), args.preset, idx, total_files, args.quiet)

    print("All files have been processed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HDR to SDR Video Transcoding Script", 
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="Note: Ensure HandBrakeCLI is installed and accessible in your system PATH.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input", help="Path to the folder containing video files to transcode (working folder)")
    input_group.add_argument("-f", "--file_list", help="Path to the text file containing the list of files to transcode")
    parser.add_argument("-p", "--preset", help="Path to the HandBrake preset file")
    parser.add_argument("-o", "--output", help="Custom output folder for transcoded files")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet mode (less verbose output)")
    
    args = parser.parse_args()

    main(args)