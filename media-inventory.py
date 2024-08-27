#!/usr/bin/env python3
"""
Media Inventory and Transcode Simulation Script
===============================================

This script analyzes video files, extracting metadata using ffprobe and simulating Plex transcoding
using FFmpeg with hardware acceleration (Intel QuickSync on Windows/Linux, VideoToolbox on Mac).
The results are saved in a CSV file.

Usage:
    python3 media-inventory.py -i <input_folder> [-e <extensions>] [-o <output>] [-q] 
                               [-d <duration>] [-s <samples>] [-c <concat>] [--delimiter <delimiter>]
                               [--mac]

Arguments:
    -i,  --input          : Path to the folder containing video files to analyze.
    -e,  --extensions     : Comma-separated list of video file extensions to analyze (default: mkv,mp4,avi).
    -o,  --output         : Custom output folder for the CSV file, the file list, and the end report (default: output-media-inventory/TIMESTAMP).
    -q,  --quiet          : Enable quiet mode (less verbose output).
    -d,  --duration       : Duration of each transcode simulation in seconds (default: full file duration).
    -s,  --samples        : Number of transcode samples to take (default: 1, 0 to skip transcoding).
    -c,  --concat         : Separator for concatenating text in issue descriptions (default: '; ').
    --delimiter           : Delimiter for the CSV file (default: tab).
    --mac                 : Use Mac-specific hardware acceleration (VideoToolbox). (default: Intel QuickSync)
    -h,  --help           : Display this help message.

Features:
    - Analyzes video files from a specified folder
    - Extracts detailed metadata for each video file using ffprobe
    - Simulates Plex transcoding using FFmpeg with hardware acceleration
      (Intel QuickSync on Windows/Linux, VideoToolbox on Mac)
    - Allows multiple transcode samples at different positions in the file
    - Calculates transcode speed ratio (transcode speed / video frame rate)
    - Categorizes transcode performance (Error, Failed, Low, Medium, High)
    - Saves results in a CSV file with a timestamp in the filename
    - Displays detailed progress information by default (use -q for less verbose output)
    - Customizable CSV delimiter and text concatenation separator
    - Mac support with VideoToolbox hardware acceleration

Output:
    - Creates a CSV file in the specified output folder with a timestamp in the filename.
    - The CSV includes columns for various video metadata, transcode simulation results,
      transcode speed ratios, and performance categories.
    - Creates a file list text file for resuming the process from the last cursor position.
    - Creates an end report after the process is complete with a summary of the results.

Requirements:
    - Python 3.6+
    - ffprobe and ffmpeg installed and accessible in the system PATH
    - For Windows/Linux: Running on a system with Intel QuickSync support (12th gen Intel i7 or compatible)
    - For Mac: Running on a Mac with Apple Silicon or recent Intel processor
    - Run pip3 install -r requirements.txt


Note: Ensure you have the necessary permissions to read the video files and write to the output directory.

Examples:
    1. Basic usage (analyze all supported video files in a folder):
       python3 media-inventory.py -i /path/to/videos

    2. Analyze specific file types with 3 transcode samples:
       python3 media-inventory.py -i /path/to/videos -e mkv,mp4 -s 3

    3. Use custom output folder and CSV delimiter:
       python3 media-inventory.py -i /path/to/videos -o /path/to/output --delimiter ","

    4. Analyze files without transcoding simulation:
       python3 media-inventory.py -i /path/to/videos -s 0

    5. Analyze files with custom transcode duration and quiet mode:
       python3 media-inventory.py -i /path/to/videos -d 30 -q

    6. Analyze files on a Mac using VideoToolbox:
       python3 media-inventory.py -i /path/to/videos --mac
"""

import os
import json
import subprocess
import csv
from datetime import datetime
import argparse
import re
import random
import sys
import argparse
import textwrap
import time
from colorama import init, Fore, Back, Style # type: ignore

init(autoreset=True)  # Initialize colorama

def create_output_folder(base_output_dir):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_output_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def generate_file_list(search_dir, extensions, output_dir, original_command):
    file_list = []
    for root, _, files in os.walk(search_dir):
        for file in sorted(files):
            if file.lower().endswith(tuple(extensions)):
                file_list.append(os.path.join(root, file))
    
    file_list_path = os.path.join(output_dir, "file_list.txt")
    
    with open(file_list_path, 'w', encoding='utf-8') as f:
        f.write(f"# Resume command: {original_command} -r {file_list_path}\n")
        f.write("# Cursor: 0\n")
        f.write("# You can use '#' for single-line comments and '\"\"\"' for multi-line comments\n")
        f.write("# Files commented out will be skipped during processing\n\n")
        for file_path in file_list:
            f.write(f"{file_path}\n")
    
    return file_list_path, len(file_list)

def read_file_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove multi-line comments
    content = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)

    lines = content.split('\n')
    file_list = []
    cursor = 0

    for line in lines:
        line = line.strip()
        if line.startswith("# Cursor:"):
            try:
                cursor = int(line.split(":")[1].strip())
            except ValueError:
                cursor = 0
        elif not line.startswith('#') and line:
            file_list.append(line)

    return file_list, cursor

def update_cursor(file_path, new_cursor):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith("# Cursor:"):
            lines[i] = f"# Cursor: {new_cursor}\n"
            break
    else:
        lines.insert(1, f"# Cursor: {new_cursor}\n")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def get_video_duration(file_path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path], capture_output=True, text=True, check=True)
        return float(result.stdout)
    except (subprocess.CalledProcessError, ValueError):
        return None

def is_empty_or_na(value):
    return value in (None, "", "N/A", "null", "NULL", "Null")

def normalize_path(path):
    return os.path.abspath(path)

def get_json_value(json_data, key_path):
    try:
        for key in key_path.split('.'):
            if key.isdigit():
                json_data = json_data[int(key)]
            else:
                json_data = json_data[key]
        return json_data
    except (KeyError, IndexError, TypeError):
        return "N/A"

def count_files(search_dir, extensions, quiet):
    total = 0
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.lower().endswith(tuple(extensions)):
                total += 1
                if not quiet and total % 100 == 0:
                    print(f"\rCounting files... {total} found. Current folder: {root}", end='', flush=True)
    print(f"\nTotal files to process: {total}")
    return total

def simulate_plex_transcoding(file_path, start_time, duration, use_mac):
    try:
        if use_mac:
            command = [
                'ffmpeg',
                '-hwaccel', 'videotoolbox',  # Use VideoToolbox hardware acceleration
                '-i', file_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'hevc_videotoolbox',  # Use VideoToolbox HEVC encoder
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-f', 'null',
                '-'
            ]
        else:
            command = [
                'ffmpeg',
                '-hwaccel', 'qsv',  # Use QuickSync hardware acceleration
                '-i', file_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'h264_qsv',  # Use QuickSync H.264 encoder
                '-preset', 'veryfast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-f', 'null',
                '-'
            ]

        result = subprocess.run(command, capture_output=True, text=True, check=True)

        match = re.search(r'speed=\s*([\d.]+)x', result.stderr)
        if match:
            speed = float(match.group(1))
            return speed
        else:
            return "N/A"
    except subprocess.CalledProcessError:
        return "Error"
    
def calculate_transcode_speed_ratio(transcode_speed, frame_rate):
    try:
        frame_rate = float(frame_rate)
    except (ValueError, TypeError):
        frame_rate = 24.0  # Default to 24 fps if frame_rate is not a valid number
    
    try:
        transcode_speed = float(transcode_speed)
        return transcode_speed / frame_rate
    except (ValueError, TypeError, ZeroDivisionError):
        return "Error"

def get_transcode_speed_group(speed_ratio):
    if speed_ratio == "Error":
        return "Error"
    try:
        speed_ratio = float(speed_ratio)
        if speed_ratio < 1.2:
            return "Failed"
        elif 1.2 <= speed_ratio < 2:
            return "Low"
        elif 2 <= speed_ratio < 3:
            return "Medium"
        else:
            return "High"
    except (ValueError, TypeError):
        return "Error"

def process_file(file, duration, samples, concat_separator, use_mac):
    file = normalize_path(file)
    result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file], capture_output=True, text=True)
    details = json.loads(result.stdout)

    file_extension = os.path.splitext(file)[1][1:]
    file_path = os.path.dirname(file)
    filename = os.path.basename(file)
    filesize = os.path.getsize(file)
    creation_date = os.path.getctime(file)
    modification_date = os.path.getmtime(file)

    # Video stream details
    video_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'video']
    codec = get_json_value(video_streams, '0.codec_name')
    codec_long_name = get_json_value(video_streams, '0.codec_long_name')
    profile = get_json_value(video_streams, '0.profile')
    level = get_json_value(video_streams, '0.level')
    bitrate = get_json_value(details, 'format.bit_rate')
    width = get_json_value(video_streams, '0.width')
    height = get_json_value(video_streams, '0.height')
    color_space = get_json_value(video_streams, '0.color_space')
    color_primaries = get_json_value(video_streams, '0.color_primaries')
    color_transfer = get_json_value(video_streams, '0.color_transfer')
    color_range = get_json_value(video_streams, '0.color_range')
    chroma_location = get_json_value(video_streams, '0.chroma_location')
    field_order = get_json_value(video_streams, '0.field_order')
    refs = get_json_value(video_streams, '0.refs')
    bits_per_raw_sample = get_json_value(video_streams, '0.bits_per_raw_sample')
    pix_fmt = get_json_value(video_streams, '0.pix_fmt')

    # Handle multiple video streams
    video_stream_count = len(video_streams)
    if video_stream_count > 1:
        codec = f"{codec} (+{video_stream_count-1})"
        codec_long_name = f"{codec_long_name} (+{video_stream_count-1})"
        profile = f"{profile} (+{video_stream_count-1})"
        level = f"{level} (+{video_stream_count-1})"

    # Detect HDR
    hdr = "Yes" if 'smpte2084' in str(color_transfer).lower() or 'hlg' in str(color_transfer).lower() else "No"

    # Detect bit depth
    bit_depth = "10" if '10' in str(pix_fmt) else bits_per_raw_sample if bits_per_raw_sample != "N/A" else "N/A"

    duration = get_json_value(details, 'format.duration')
    frame_rate = get_json_value(video_streams, '0.avg_frame_rate')
    
    # Convert fractional frame rate to decimal
    if isinstance(frame_rate, str):
        if '/' in frame_rate:
            try:
                num, den = map(int, frame_rate.split('/'))
                frame_rate = f"{num/den:.3f}" if den != 0 else "N/A"
            except ValueError:
                frame_rate = "N/A"
        elif frame_rate.replace('.', '', 1).isdigit():  # Check if it's already a decimal number
            frame_rate = f"{float(frame_rate):.3f}"
        else:
            frame_rate = "N/A"
    else:
        frame_rate = "N/A"

    # Audio details
    audio_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'audio']
    audio_codecs = ", ".join(str(stream.get('codec_name', 'N/A')) for stream in audio_streams)
    audio_codec_long_names = ", ".join(str(stream.get('codec_long_name', 'N/A')) for stream in audio_streams)
    audio_channels = ", ".join(str(stream.get('channels', 'N/A')) for stream in audio_streams)
    audio_sample_rates = ", ".join(str(stream.get('sample_rate', 'N/A')) for stream in audio_streams)
    audio_bitrates = ", ".join(str(stream.get('bit_rate', 'N/A')) for stream in audio_streams)
    audio_bit_depth = ", ".join(str(stream.get('bits_per_raw_sample', 'N/A')) for stream in audio_streams)
    audio_stream_count = len(audio_streams)

    # Subtitle details
    subtitle_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'subtitle']
    subtitle_languages = ", ".join(str(stream.get('tags', {}).get('language', 'N/A')) for stream in subtitle_streams)
    subtitle_formats = ", ".join(str(stream.get('codec_name', 'N/A')) for stream in subtitle_streams)
    subtitle_stream_count = len(subtitle_streams)

    # Container format
    container_format = get_json_value(details, 'format.format_name')

        # Issue detection
    issues = {
        "Unknown metadata": False,
        "Non-standard video codec": False,
        "Non-standard audio codec": False,
        "Problematic subtitle format": False,
        "High bitrate": False,
        "Low bitrate": False,
        "Non-standard resolution": False,
        "Non-standard frame rate": False,
        "High bit depth": False,
        "HDR content": False,
        "4K content": False,
        "Complex video profile": False,
        "Variable frame rate": False,
        "Interlaced content": False,
        "High subtitle stream count": False,
        "Uncommon container format": False,
        "Very high bitrate": False,
        "Multiple audio streams": False
    }

    issue_descriptions = []

    # Check for unknown or empty values
    if any(is_empty_or_na(value) for value in [codec, audio_codecs, subtitle_formats]):
        issues["Unknown metadata"] = True
        issue_descriptions.append("Some file information couldn't be determined")

    # Video codec check
    standard_video_codecs = ['h264', 'hevc', 'vp9', 'av1']
    if codec.lower() not in standard_video_codecs:
        issues["Non-standard video codec"] = True
        issue_descriptions.append(f"Non-standard video codec: {codec}")

    # Audio codec check
    standard_audio_codecs = ['aac', 'ac3', 'eac3', 'mp3', 'opus']
    audio_codec_list = [ac.strip().lower() for ac in audio_codecs.split(',')]
    non_standard_audio = [ac for ac in audio_codec_list if ac not in standard_audio_codecs]
    if non_standard_audio:
        issues["Non-standard audio codec"] = True
        issue_descriptions.append(f"Non-standard audio codec(s): {', '.join(non_standard_audio)}")

    # Subtitle format check
    problematic_subtitle_formats = ['dvd_subtitle', 'hdmv_pgs_subtitle', 'dvb_subtitle']
    subtitle_format_list = [sf.strip().lower() for sf in subtitle_formats.split(',')]
    problematic_subs = [sf for sf in subtitle_format_list if sf in problematic_subtitle_formats]
    if problematic_subs:
        issues["Problematic subtitle format"] = True
        issue_descriptions.append(f"Potentially problematic subtitle format(s): {', '.join(problematic_subs)}")

    # Bitrate check
    try:
        bitrate_value = int(bitrate)
        if bitrate_value > 20000000:  # 20 Mbps
            issues["High bitrate"] = True
            issue_descriptions.append(f"High bitrate ({bitrate_value/1000000:.2f} Mbps) may cause buffering")
        elif bitrate_value < 1000000:  # 1 Mbps
            issues["Low bitrate"] = True
            issue_descriptions.append(f"Low bitrate ({bitrate_value/1000000:.2f} Mbps) may result in poor quality")
    except ValueError:
        if not is_empty_or_na(bitrate):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse bitrate: {bitrate}")

    # Resolution check
    try:
        width_value, height_value = int(width), int(height)
        if (width_value, height_value) not in [(1920, 1080), (3840, 2160), (1280, 720), (720, 480), (720, 576)]:
            issues["Non-standard resolution"] = True
            issue_descriptions.append(f"Non-standard resolution: {width_value}x{height_value}")
    except ValueError:
        if not (is_empty_or_na(width) or is_empty_or_na(height)):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse resolution: {width}x{height}")

    # Frame rate check
    try:
        fps = float(frame_rate)
        if fps not in [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]:
            issues["Non-standard frame rate"] = True
            issue_descriptions.append(f"Non-standard frame rate: {fps} fps")
    except ValueError:
        if not is_empty_or_na(frame_rate):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse frame rate: {frame_rate}")

    # Check for high bit depth
    if bit_depth not in ["8", "N/A"]:
        issues["High bit depth"] = True
        issue_descriptions.append(f"High bit depth video: {bit_depth}-bit")

    # Check for HDR content
    if hdr == "Yes":
        issues["HDR content"] = True
        issue_descriptions.append("HDR content may require tone-mapping")

    # Check for 4K resolution
    if width == "3840" and height == "2160":
        issues["4K content"] = True
        issue_descriptions.append("4K content may be demanding to transcode")

    # Check for complex video profiles
    complex_profiles = ["High 4:2:2", "High 4:4:4"]
    if any(cp in profile for cp in complex_profiles):
        issues["Complex video profile"] = True
        issue_descriptions.append(f"Complex video profile: {profile}")

    # Check for variable frame rate
    if "," in frame_rate or "/" in frame_rate:
        issues["Variable frame rate"] = True
        issue_descriptions.append("Possibly variable frame rate")

    # Check for interlaced content
    if field_order not in ["progressive", "N/A"]:
        issues["Interlaced content"] = True
        issue_descriptions.append(f"Interlaced content: {field_order}")

    # Check for multiple subtitle streams
    try:
        if isinstance(subtitle_stream_count, (int, float)) and subtitle_stream_count > 5:
            issues["High subtitle stream count"] = True
            issue_descriptions.append(f"High number of subtitle streams: {subtitle_stream_count}")
        elif isinstance(subtitle_stream_count, str) and subtitle_stream_count.isdigit() and int(subtitle_stream_count) > 5:
            issues["High subtitle stream count"] = True
            issue_descriptions.append(f"High number of subtitle streams: {subtitle_stream_count}")
    except (ValueError, AttributeError):
        issues["Unknown metadata"] = True
        issue_descriptions.append(f"Unable to parse subtitle stream count: {subtitle_stream_count}")

    # Check for less common container formats
    common_containers = ["matroska", "mov", "mp4", "avi", "mpegts"]
    if not any(cf in str(container_format).lower() for cf in common_containers):
        issues["Uncommon container format"] = True
        issue_descriptions.append(f"Less common container format: {container_format}")

    # Check for very high bitrate
    try:
        bitrate_value = int(bitrate) if isinstance(bitrate, str) else bitrate
        if bitrate_value > 100000000:  # 100 Mbps
            issues["Very high bitrate"] = True
            issue_descriptions.append(f"Very high bitrate ({bitrate_value/1000000:.2f} Mbps) may slow transcoding")
    except (ValueError, TypeError):
        if not is_empty_or_na(bitrate):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse bitrate: {bitrate}")

    # Check for multiple audio streams
    try:
        audio_stream_count_value = int(audio_stream_count) if isinstance(audio_stream_count, str) else audio_stream_count
        if audio_stream_count_value > 3:
            issues["Multiple audio streams"] = True
            issue_descriptions.append(f"Multiple audio streams: {audio_stream_count_value}")
    except (ValueError, TypeError):
        if not is_empty_or_na(audio_stream_count):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse audio stream count: {audio_stream_count}")

    # Combine issues into a single string
    issue_descriptions.sort()  # Sort the issue descriptions
    issue_description = concat_separator.join(issue_descriptions) if issue_descriptions else "None"


    # Transcode simulation
    transcode_speeds = []
    transcode_speed_ratios = []
    transcode_speed_groups = []
    if samples > 0:
        file_duration = get_video_duration(file)
        if file_duration is not None:
            sample_duration = duration if duration is not None else file_duration
            for i in range(samples):
                if i == 0:
                    start_time = 0
                else:
                    max_start = max(0, file_duration - sample_duration)
                    start_time = random.uniform(0, max_start)
                speed = simulate_plex_transcoding(file, start_time, sample_duration, use_mac)

                transcode_speeds.append(speed)
                speed_ratio = calculate_transcode_speed_ratio(speed, frame_rate)
                transcode_speed_ratios.append(speed_ratio)
                transcode_speed_groups.append(get_transcode_speed_group(speed_ratio))
        else:
            transcode_speeds = ["Error"] * samples
            transcode_speed_ratios = ["Error"] * samples
            transcode_speed_groups = ["Error"] * samples

    return [
        file, file_extension, file_path, filename, filesize, container_format,
        codec, codec_long_name, profile, level, bitrate, width, height,
        color_space, color_primaries, color_transfer, color_range, chroma_location,
        field_order, refs, bits_per_raw_sample, pix_fmt, hdr, bit_depth,
        duration, frame_rate, audio_codecs, audio_codec_long_names, audio_channels,
        audio_sample_rates, audio_bitrates, audio_bit_depth, audio_stream_count,
        subtitle_languages, subtitle_formats, subtitle_stream_count,
        creation_date, modification_date,
        "1" if any(issues.values()) else "0",
        issue_description,  
    ] + [str(int(issues[key])) for key in issues] + transcode_speeds + transcode_speed_ratios + transcode_speed_groups

def generate_report(output_dir, output_file, stats, total_time, avg_time_per_file):
    report = f"""
{Fore.YELLOW}{Style.BRIGHT}Process Report
{Fore.YELLOW}{'=' * 50}

{Fore.CYAN}Files Processed: {Fore.WHITE}{stats['processed']} / {stats['total']}
{Fore.CYAN}Time Taken: {Fore.WHITE}{total_time:.2f} seconds
{Fore.CYAN}Avg Time per File: {Fore.WHITE}{avg_time_per_file:.2f} seconds

{Fore.YELLOW}Transcode Performance:
{Fore.CYAN}Error: {Fore.WHITE}{stats['error']} ({stats['error']/stats['processed']*100:.2f}%)
{Fore.CYAN}Failed: {Fore.WHITE}{stats['failed']} ({stats['failed']/stats['processed']*100:.2f}%)
{Fore.CYAN}Low: {Fore.WHITE}{stats['low']} ({stats['low']/stats['processed']*100:.2f}%)
{Fore.CYAN}Medium: {Fore.WHITE}{stats['medium']} ({stats['medium']/stats['processed']*100:.2f}%)
{Fore.CYAN}High: {Fore.WHITE}{stats['high']} ({stats['high']/stats['processed']*100:.2f}%)

{Fore.YELLOW}Issues:
{Fore.CYAN}Files with No Issues: {Fore.WHITE}{stats['no_issues']} ({stats['no_issues']/stats['processed']*100:.2f}%)
{Fore.CYAN}Files with Issues: {Fore.WHITE}{stats['with_issues']} ({stats['with_issues']/stats['processed']*100:.2f}%)
"""
    
    print(report)
    
    # Write report to file (without color codes)
    report_file = os.path.join(output_dir, 'process_report.txt')
    with open(report_file, 'w') as f:
        f.write(report.replace(Fore.YELLOW, '').replace(Fore.CYAN, '').replace(Fore.WHITE, '').replace(Style.BRIGHT, ''))



def main(input_path, extensions, base_output_dir, quiet, csv_delimiter, concat_separator, duration, samples, use_mac, resume_file=None):
    start_time = time.time()
    
    if resume_file:
        output_dir = os.path.dirname(resume_file)
        file_list, cursor = read_file_list(resume_file)
        print(f"{Fore.YELLOW}Resuming process from file {cursor + 1}")
    else:
        output_dir = create_output_folder(base_output_dir)
        print(f"{Fore.CYAN}Indexing media files in {input_path}")
        print(f"{Fore.CYAN}Using arguments: {' '.join(sys.argv[1:])}")
        print(f"{Fore.CYAN}Counting files to process...")
        file_list_path, total_files = generate_file_list(input_path, extensions, output_dir, ' '.join(sys.argv))
        file_list, cursor = read_file_list(file_list_path)
        print(f"{Fore.GREEN}Found {len(file_list)} files to process")
        print(f"{Fore.YELLOW}To resume this process, use: python3 {sys.argv[0]} -r {file_list_path}")

    output_file = os.path.join(output_dir, "video_files.csv")
    print(f"{Fore.CYAN}Starting processing. Output file: {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=csv_delimiter)
        # Write headers (as before)
        
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
            result = process_file(file_path, duration, samples, concat_separator, use_mac)
            writer.writerow(result)
            stats["processed"] += 1
            
            # Update stats based on result
            if result[-1] == "Error":
                stats["error"] += 1
            elif result[-1] == "Failed":
                stats["failed"] += 1
            elif result[-1] == "Low":
                stats["low"] += 1
            elif result[-1] == "Medium":
                stats["medium"] += 1
            elif result[-1] == "High":
                stats["high"] += 1
            
            if result[36] == "0":  # Assuming "Issue Detected" is at index 36
                stats["no_issues"] += 1
            else:
                stats["with_issues"] += 1
            
            # Update cursor in file_list.txt
            update_cursor(file_list_path, i + 1)
            
            if not quiet:
                print(f"\r{Fore.CYAN}Processed {stats['processed']} of {stats['total']} files: {file_path}", end='', flush=True)

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

if __name__ == "__main__":
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
    parser.add_argument("-i", "--input", required=True, help="Path to the folder containing video files to analyze")
    parser.add_argument("-e", "--extensions", default="mkv,mp4,avi", 
                        help="Comma-separated list of video file extensions to analyze (default: mkv,mp4,avi)")
    parser.add_argument("-o", "--output", default="output-media-inventory", 
                        help="Base output folder for the results (a timestamped subfolder will be created)")
    parser.add_argument("-d", "--delimiter", default="\t", help="Delimiter for the CSV file (default: tab)")
    parser.add_argument("-c", "--concat", default="; ", help="Separator for concatenating text (default: '; ')")
    parser.add_argument("-t", "--duration", type=float, default=None, help="Duration of each transcode simulation in seconds (default: full file duration)")
    parser.add_argument("-s", "--samples", type=int, default=1, help="Number of transcode samples to take (default: 1, 0 to skip transcoding)")
    parser.add_argument("--mac", action="store_true", help="Use Mac-specific hardware acceleration (VideoToolbox)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet mode (less verbose output)")
    args = parser.parse_args()

    if args.resume:
        main(args.resume, None, os.path.dirname(os.path.dirname(args.resume)), args.quiet, args.delimiter, args.concat, args.duration, args.samples, args.mac, resume_file=args.resume)
    else:
        extensions = tuple(f".{ext.lower().strip()}" for ext in args.extensions.split(','))
        main(args.input, extensions, args.output, args.quiet, args.delimiter, args.concat, args.duration, args.samples, args.mac)

    if not os.path.isdir(args.input):
        print(f"Error: {args.input} is not a valid directory")
        sys.exit(1)

    extensions = tuple(f".{ext.lower().strip()}" for ext in args.extensions.split(','))
    main(args.input, extensions, args.output, args.quiet, args.delimiter, args.concat, args.duration, args.samples, args.mac)