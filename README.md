# Video Toolbox

This repository contains a set of tools for analyzing, health-checking, and transcoding video files, with a focus on maintaining a healthy media library and improving compatibility with Plex media server.

## Contents

1. [health-check.py](#health-checkpy)
2. [media-inventory.py](#media-inventorypy)
3. [transcode-hdr-to-sdr.py](#transcode-hdr-to-sdrpy)
4. [create_symlinks.py](#create_symlinkspy)

## health-check.py

This Python script performs health checks on video files in a specified directory and its subdirectories, using ffmpeg to analyze multiple samples of each video.

### Usage

```bash
python3 health-check.py -i <input_folder> [-s <samples>] [-d <duration>] [-e <extensions>] [-o <output>] [-q] [-h]
```

### Key Features

- Recursively checks video files in the specified folder and subfolders
- Allows for multiple samples at different points in each video
- Creates a CSV file with the results, including filename, path, any errors, and check duration
- Displays detailed progress information by default (use -q for less verbose output)

## media-inventory.py

This Python script analyzes video files in a specified directory and its subdirectories, extracting various metadata using ffprobe and generating a CSV file with detailed information.

### Usage

```bash
python3 media-inventory.py -i <input_folder> [-e <extensions>] [-o <output>] [-q] [-h]
```

### Key Features

- Recursively searches for video files in the specified directory
- Extracts detailed metadata for each video file using ffprobe
- Saves results in a CSV file with a timestamp in the filename
- Displays detailed progress information by default (use -q for less verbose output)

## transcode-hdr-to-sdr.py

This Python script automates the process of transcoding HDR videos to SDR format, specifically converting from bt2020nc color profile to bt709. It's designed to fix issues where Plex is unable to play bt2020nc 10-bit color profile videos.

### Usage

1. Run `media-inventory.py` to generate a CSV of video file information.
2. Filter the CSV to identify files for transcoding.
3. Copy the filtered list into 'hdr-video-files.txt'.
4. Run the script:

```bash
python3 transcode-hdr-to-sdr.py
```

### Key Features

- Processes a list of files specified in 'hdr-video-files.txt'
- Uses HandBrakeCLI for transcoding, maintaining all metadata, subtitles, and audio tracks
- Provides real-time progress updates including ETA and FPS
- Logs detailed information for each transcoding operation

## create_symlinks.py

This Python script creates a folder of symlinks based on a list of file paths. It's designed to help prepare a set of files for processing with Tdarr, allowing you to create a temporary library from a specific list of files rather than an entire folder.

### Usage

```bash
python3 create_symlinks.py -f <input_file> [-o <output_folder>] [-q]
python3 create_symlinks.py -h
```

### Key Features

- Creates symlinks from a list of file paths provided in a text file
- Allows specification of output directory for symlinks (default: ./symlinks)
- Provides detailed feedback on the process, including number of files processed and symlinks created
- Includes a quiet mode option to suppress informational output
- Handles errors gracefully, providing warnings for non-existent files or already existing symlinks

## Folder Structure

- `health-check.py`: Script for checking the health of video files
- `media-inventory.py`: Script for analyzing video files and generating metadata CSV
- `transcode-hdr-to-sdr.py`: Script for transcoding HDR videos to SDR
- `create_symlinks.py`: Script for creating symlinks from a list of files
- `output-healthcheck/`: Output folder for health check results (not tracked in git)
- `output-media-inventory/`: Output folder for media inventory results (not tracked in git)
- `logs/`: Folder for log files (not tracked in git)

## Why Use This Toolkit?

This toolkit provides a comprehensive set of tools to maintain a healthy media library and address common issues with Plex playback. It allows for:

- Identifying potentially corrupt or problematic video files
- Gathering detailed metadata about your video collection
- Addressing specific playback issues related to HDR content on Plex
- Preparing specific sets of files for processing with Tdarr

## Prerequisites

- Python 3.x
- ffmpeg and ffprobe
- HandBrakeCLI (for transcoding)

## Contributing

Contributions to improve these scripts or add new features are welcome. Please feel free to submit pull requests or open issues for any bugs or feature requests.

## Author

Created by Christopher Conradi (https://github.com/xoChrisCo) as a toolbox to maintain a healthy media library and debug Plex playback issues.

## License

[Specify your license here, e.g., MIT, GPL, etc.]
