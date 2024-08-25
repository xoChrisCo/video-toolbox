#!/usr/bin/env python3
"""
Media Inventory Script
======================

This script analyzes video files in a specified directory and its subdirectories,
extracting various metadata using ffprobe. The results are saved in a CSV file.

Usage:
    python3 media-inventory.py -i <input_folder> [-e <extensions>] [-o <output>] [-q] [-h]

Arguments:
    -i,  --input          : Path to the folder containing video files to analyze.
    -e,  --extensions     : Comma-separated list of video file extensions to analyze (default: mkv,mp4,avi).
    -o,  --output         : Custom output folder for the CSV file (default: output-media-inventory).
    -q,  --quiet          : Enable quiet mode (less verbose output).
    -h,  --help           : Display this help message.

Features:
    - Recursively searches for video files in the specified directory
    - Extracts detailed metadata for each video file using ffprobe
    - Saves results in a CSV file with a timestamp in the filename
    - Displays detailed progress information by default (use -q for less verbose output)

Output:
    - Creates a CSV file in the specified output folder (or 'output-media-inventory' by default) 
      with a timestamp in the filename.
    - The CSV includes columns for various video metadata (see script for full list).

Requirements:
    - Python 3.6+
    - ffprobe (part of FFmpeg) installed and accessible in the system PATH

Note: Ensure you have the necessary permissions to read the video files and
write to the output directory.
"""

import os
import json
import subprocess
import csv
from datetime import datetime
import argparse

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

def process_file(file):
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

    return [
        file, file_extension, file_path, filename, filesize, container_format,
        codec, codec_long_name, profile, level, bitrate, width, height,
        color_space, color_primaries, color_transfer, color_range, chroma_location,
        field_order, refs, bits_per_raw_sample, pix_fmt, hdr, bit_depth,
        duration, frame_rate, audio_codecs, audio_codec_long_names, audio_channels,
        audio_sample_rates, audio_bitrates, audio_bit_depth, audio_stream_count,
        subtitle_languages, subtitle_formats, subtitle_stream_count,
        creation_date, modification_date
    ]

def main(search_dir, extensions, output_dir, quiet):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{timestamp}-video_files.csv")

    total_files = count_files(search_dir, extensions, quiet)
    count = 0

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter='\t')
        writer.writerow([
            "File", "Extension", "File Path", "Filename", "File Size", "Container Format",
            "Codec", "Codec Long Name", "Profile", "Level", "Bitrate", "Width", "Height",
            "Color Space", "Color Primaries", "Color Transfer", "Color Range", "Chroma Location",
            "Field Order", "Refs", "Bits per Raw Sample", "Pixel Format", "HDR", "Bit Depth",
            "Duration", "Frame Rate", "Audio Codecs", "Audio Codec Long Names", "Audio Channels",
            "Audio Sample Rates", "Audio Bitrates", "Audio Bit Depth", "Audio Stream Count",
            "Subtitle Languages", "Subtitle Formats", "Subtitle Stream Count",
            "Creation Date", "Modification Date"
        ])

        for root, _, files in os.walk(search_dir):
            for file in sorted(files):  # Sort files alphabetically
                if file.lower().endswith(tuple(extensions)):
                    full_path = os.path.join(root, file)
                    writer.writerow(process_file(full_path))
                    count += 1
                    if not quiet:
                        print(f"\rProcessed {count} of {total_files} files: {full_path}", end='', flush=True)

    print(f"\nTotal files processed: {count} of {total_files}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Video File Inventory Script",
        epilog="Note: The -h or --help option is automatically added by argparse and will display this help message."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to the folder containing video files to analyze")
    parser.add_argument("-e", "--extensions", default="mkv,mp4,avi", 
                        help="Comma-separated list of video file extensions to analyze (default: mkv,mp4,avi)")
    parser.add_argument("-o", "--output", default="output-media-inventory", help="Custom output folder for the CSV file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet mode (less verbose output)")
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"Error: {args.input} is not a valid directory")
        sys.exit(1)

    extensions = tuple(f".{ext.lower().strip()}" for ext in args.extensions.split(','))
    main(args.input, extensions, args.output, args.quiet)