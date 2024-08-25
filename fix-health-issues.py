#!/usr/bin/env python3
"""
Fix Health Issues Script
========================

This script processes a list of video files using ffmpeg to fix common health issues.
It uses hardware-accelerated encoding with Apple's VideoToolbox.

Usage:
    python3 fix-health-issues.py -f <file_list> [-q] [-h]

Arguments:
    -f,  --file_list      : Path to the text file containing the list of files to process.
    -q,  --quiet          : Enable quiet mode (less verbose output).
    -h,  --help           : Display this help message.

The script processes each file using the following ffmpeg command:
ffmpeg -i input.mkv -c:v hevc_videotoolbox -q:v 50 -c:a copy -c:s copy output.mkv

File handling:
1. Output is saved as ORIGINAL_FILENAME.fix_health_check_temp.mkv
2. On completion, the original file is renamed to ORIGINAL_FILENAME.to_be_deleted_health_fixed
3. The temp file is then renamed to the original filename
4. If a .to_be_deleted_health_fixed file exists, the file is skipped (resume functionality)
5. If a .fix_health_check_temp.mkv file exists at start, it's deleted before processing

Author: Christopher Conradi
Date: 2024-08-07
Version: 3
"""

import argparse
import os
import subprocess
import sys
import time
from tqdm import tqdm # type: ignore

def clean_temp_files(file_path):
    temp_file = file_path + '.fix_health_check_temp.mkv'
    if os.path.exists(temp_file):
        os.remove(temp_file)
        print(f"Removed existing temp file: {temp_file}")

def get_duration(file_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        print(f"Warning: Couldn't determine duration for {file_path}")
        return None

def process_file(input_file, file_number, total_files):
    # Check if file has already been processed
    if os.path.exists(input_file + '.to_be_deleted_health_fixed'):
        print(f"Skipping {input_file} (already processed)")
        return True

    # Clean any existing temp files
    clean_temp_files(input_file)

    # Use .mkv extension for the temp file
    output_file = input_file + '.fix_health_check_temp.mkv'
    
    # Get the duration of the input file
    duration = get_duration(input_file)
    
    command = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'hevc_videotoolbox',  # Use VideoToolbox for video encoding
        '-q:v', '50',
        '-c:a', 'aac',  # Re-encode audio to AAC
        '-b:a', '384k',  # Set audio bitrate
        '-af', 'aresample=async=1000',  # Correct audio sync issues
        '-max_muxing_queue_size', '9999',  # Increase muxing queue size
        '-fflags', '+genpts',  # Generate presentation timestamps
        '-c:s', 'copy',  # Copy subtitles
        '-f', 'matroska',
        output_file
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    print(f"\nProcessing file {file_number}/{total_files}: {os.path.basename(input_file)}")
    if duration:
        pbar = tqdm(total=int(duration), unit='sec', desc="Progress")
    else:
        pbar = tqdm(total=100, unit='%', desc="Progress")
    
    start_time = time.time()
    last_update = start_time

    while True:
        output = process.stderr.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # Parse ffmpeg output for progress information
            if "time=" in output:
                time_match = output.split("time=")[1].split()[0].split(':')
                try:
                    current_time = int(time_match[0]) * 3600 + int(time_match[1]) * 60 + float(time_match[2])
                    if duration:
                        pbar.n = int(current_time)
                    else:
                        pbar.n = min(int((current_time / (duration or 3600)) * 100), 100)
                    pbar.refresh()
                except (ValueError, IndexError):
                    pass

            # Update ETA and speed every 5 seconds
            current_time = time.time()
            if current_time - last_update > 5:
                elapsed = current_time - start_time
                if pbar.n > 0:
                    eta = (elapsed / pbar.n) * (pbar.total - pbar.n)
                    speed = pbar.n / elapsed
                    pbar.set_postfix_str(f"ETA: {eta:.0f}s, Speed: {speed:.2f}x")
                last_update = current_time

    pbar.close()
    process.wait()

    if process.returncode != 0:
        print(f"Error processing {input_file}:")
        print(process.stderr.read())
        # Clean up the temp file if it was created
        if os.path.exists(output_file):
            os.remove(output_file)
        return False

    # Rename files
    os.rename(input_file, input_file + '.to_be_deleted_health_fixed')
    os.rename(output_file, input_file)

    return True

def main(args):
    with open(args.file_list, 'r') as file:
        files = [line.strip() for line in file if line.strip()]

    total_files = len(files)
    processed_files = 0
    failed_files = []

    print(f"Total files to process: {total_files}")

    for idx, input_file in enumerate(files, 1):
        if process_file(input_file, idx, total_files):
            processed_files += 1
        else:
            failed_files.append(input_file)
        
        print(f"Overall progress: {processed_files}/{total_files} files processed")

    if failed_files:
        print("\nThe following files failed to process:")
        for file in failed_files:
            print(file)
    else:
        print("\nAll files processed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix Health Issues Script", 
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="Note: This script requires ffmpeg to be installed and accessible in your system PATH.")
    parser.add_argument("-f", "--file_list", required=True, help="Path to the text file containing the list of files to process")
    
    args = parser.parse_args()

    if not os.path.exists(args.file_list):
        print(f"Error: File list not found: {args.file_list}")
        sys.exit(1)

    main(args)