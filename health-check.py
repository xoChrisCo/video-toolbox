"""
Advanced Video Health Check Script
==================================

This script performs a health check on video files in a specified directory and its subdirectories,
allowing for multiple samples at different points in each video. Files are processed in alphabetical order.

Usage:
    python3 health_check.py -i <input_folder> [-s <samples>] [-d <duration>] [-e <extensions>] [-o <output>] [-q] [-h]

Arguments:
    -i,  --input          : Path to the folder containing video files to check.
    -s,  --samples        : Number of samples to check per video (default: 1).
    -d,  --duration       : Duration of each sample in seconds (default: full video).
    -e,  --extensions     : Comma-separated list of video file extensions to check (default: mp4,mkv,avi,mov,flv,wmv).
    -o,  --output         : Custom output folder for the CSV file (default: output-healt-hcheck).
    -q,  --quiet          : Enable quiet mode (less verbose output).
    -h,  --help           : Display this help message.

Features:
    - Recursively checks all video files in the specified folder and subfolders.
    - Processes files in alphabetical order.
    - Uses ffmpeg to analyze each video file for the specified number of samples and duration.
    - Creates a CSV file with the results, including filename, path, any errors, and check duration.
    - Displays detailed progress information by default (use -q for less verbose output).
    - Output filename includes information about samples and duration.

Output:
    - Creates a CSV file in the specified output folder (or 'output-healthcheck' by default) with a timestamp, 
      sample count, and duration in the filename.
    - The CSV includes columns: Filename, Full Path, Path, Sample, Start Time, Error, ffmpeg Output, and Check Duration (seconds).

Requirements:
    - Python 3
    - ffmpeg (must be installed and accessible in the system PATH)
"""

import os
import sys
import csv
import subprocess
import time
import random
import argparse
from datetime import datetime

def get_video_duration(file_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        print(f"Warning: Could not determine duration for {file_path}. Skipping this file.")
        return None

def run_ffmpeg_check(file_path, start_time, duration):
    check_start_time = time.time()
    command = ['ffmpeg', '-v', 'error', '-ss', str(start_time), '-t', str(duration), '-i', file_path, '-f', 'null', '-']
    result = subprocess.run(command, capture_output=True, text=True)
    check_duration = round(time.time() - check_start_time, 2)
    return result.stderr.strip(), check_duration

def count_video_files(folder_path, extensions, quiet):
    count = 0
    print("Counting video files...")
    for root, _, files in os.walk(folder_path):
        for file in sorted(files):
            if file.lower().endswith(tuple(extensions)):
                count += 1
                if not quiet and count % 100 == 0:  # Update every 100 files if not in quiet mode
                    print(f"Found {count} video files...")
    print(f"Found {count} files in folder {folder_path}")
    return count

def check_videos(folder_path, num_samples, sample_duration, extensions, output_folder, quiet):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_folder, exist_ok=True)
    
    duration_info = f"{sample_duration}s" if sample_duration else "full"
    filename = f"health_check_{timestamp}_samples{num_samples}_duration{duration_info}.csv"
    csv_file = os.path.join(output_folder, filename)

    total_files = count_video_files(folder_path, extensions, quiet)
    print(f"Starting health check on {total_files} video files.")

    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Full Path", "Path", "Sample", "Start Time", "Error", "Output", "Check Duration (s)"])

        checked_files = 0
        all_files = []
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith(tuple(extensions)):
                    all_files.append((root, filename))
        
        # Sort the files alphabetically
        all_files.sort(key=lambda x: x[1].lower())

        for root, filename in all_files:
            checked_files += 1
            full_path = os.path.join(root, filename)
            if not quiet:
                print(f"Checking file {checked_files}/{total_files}: {filename}")
            
            video_duration = get_video_duration(full_path)
            if video_duration is None:
                continue  # Skip this file if we couldn't determine its duration

            sample_dur = sample_duration if sample_duration else video_duration

            for sample in range(num_samples):
                if sample == 0 or num_samples == 1:
                    start_time = 0
                else:
                    max_start = max(0, video_duration - sample_dur)
                    start_time = random.uniform(0, max_start)
                
                output, check_duration = run_ffmpeg_check(full_path, start_time, sample_dur)
                error = "yes" if output else "no"
                
                writer.writerow([
                    filename,
                    full_path,
                    root,
                    sample + 1,
                    round(start_time, 2),
                    error,
                    output,
                    check_duration
                ])

    print(f"Health check completed. Results saved to {csv_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Advanced Video Health Check Script",
        epilog="Note: The -h or --help option is automatically added by argparse and will display this help message."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to the folder containing video files to check")
    parser.add_argument("-s", "--samples", type=int, default=1, help="Number of samples to check per video (default: 1)")
    parser.add_argument("-d", "--duration", type=int, help="Duration of each sample in seconds (default: full video)")
    parser.add_argument("-e", "--extensions", default="mp4,mkv,avi,mov,flv,wmv", 
                        help="Comma-separated list of video file extensions to check (default: mp4,mkv,avi,mov,flv,wmv)")
    parser.add_argument("-o", "--output", default="output-health-check", help="Custom output folder for the CSV file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet mode (less verbose output)")
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"Error: {args.input} is not a valid directory")
        sys.exit(1)

    extensions = tuple(f".{ext.lower().strip()}" for ext in args.extensions.split(','))
    check_videos(args.input, args.samples, args.duration, extensions, args.output, args.quiet)

if __name__ == "__main__":
    main()