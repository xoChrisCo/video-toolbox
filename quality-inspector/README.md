# Video Quality Inspection Tool

This Python script generates screenshot and video samples from video files in a given folder. Good for comparing a transcoded video file with the original. It can operate in two modes:

1. Single folder mode: Generate samples from a single input folder
2. Comparison mode: Compare transcoded video files with their originals

## Features

- Generate screenshot samples from video files
- Create video samples of specified length
- Compare transcoded videos with original versions
- Customizable bitrate thresholds for sample generation
- Support for multiple video file extensions
- Verbose and debug output options
- Force regeneration of existing samples

## Requirements

- Python 3.x
- FFmpeg (must be installed and available in the system PATH)
- Required Python packages (install using `pip install -r requirements.txt`):
  - colorama==0.4.6
  - tqdm==4.65.0

## Installation

1. Clone this repository or download the source code.
2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Ensure FFmpeg is installed and available in your system PATH.

## Usage

```bash
python3 video_quality_inspect.py [-h] [-s SCREENSHOT_PATH] [-ns SCREENSHOT_SAMPLES]
                                 [-nv VIDEO_SAMPLES] [-l VIDEO_LENGTH] [-v] [-f]
                                 [-e EXTENSIONS [EXTENSIONS ...]] [-c COMPARE_PATH]
                                 [-lt LOWER_THRESHOLD] [-ut UPPER_THRESHOLD]
                                 [--ignore-thresholds] [--force-video-samples]
                                 [--force-all] [-d]
                                 input_path
```

### Arguments

- `input_path`: Path to the video files (or transcoded files in comparison mode)

### Options

- `-h, --help`: Show the help message and exit
- `-s, --screenshot_path SCREENSHOT_PATH`: Path to save screenshots and video samples (default: ./screenshots)
- `-ns, --screenshot_samples SCREENSHOT_SAMPLES`: Number of screenshot samples to take (default: 5)
- `-nv, --video_samples VIDEO_SAMPLES`: Number of video samples to take (default: 3)
- `-l, --video_length VIDEO_LENGTH`: Length of video samples in seconds (default: 7)
- `-v, --verbose`: Enable verbose output
- `-f, --force`: Force regeneration of samples, even if they already exist
- `-e, --extensions EXTENSIONS [EXTENSIONS ...]`: List of video file extensions to process (default: .mkv .mp4 .avi .mov .wmv .flv .webm .m4v .mpeg .mpg .m2ts .ts)
- `-c, --compare_path COMPARE_PATH`: Path to the original video files for comparison mode
- `-lt, --lower_threshold LOWER_THRESHOLD`: Lower bitrate threshold in percent for video generation (default: 60)
- `-ut, --upper_threshold UPPER_THRESHOLD`: Upper bitrate threshold in percent for video generation (default: 105)
- `--ignore-thresholds`: Ignore bitrate thresholds and create video samples for all files
- `--force-video-samples`: Force creation of video samples even if bitrates are within thresholds
- `--force-all`: Force processing of all videos, even if bitrates are identical
- `-d, --debug`: Enable debug mode with additional output

## Examples

- Process all video files in a directory:

```bash
python3 video_quality_inspect.py /path/to/videos
```

- Process only MKV and AVI files, save screenshots in a custom directory:

```bash
python3 video_quality_inspect.py /path/to/videos -e mkv avi -s /path/to/custom/screenshots
```

- Compare transcoded videos with originals:

```bash
python3 video_quality_inspect.py /path/to/transcoded -c /path/to/original
```

- Generate more samples with longer video clips:

```bash
python3 video_quality_inspect.py /path/to/videos -ns 5 -nv 5 -l 10
```

- Use custom bitrate thresholds and force video sample creation:

```bash
python3 video_quality_inspect.py /path/to/videos -lt 80 -ut 120 --force-video-samples
```

- Process all videos, ignoring thresholds and existing samples:

```bash
python3 video_quality_inspect.py /path/to/videos --ignore-thresholds --force-all
```

- Debug mode with verbose output:

```bash
python3 video_quality_inspect.py /path/to/videos -v -d
```

## Output

- Screenshot samples and video samples are saved in the specified screenshot_path
- Output folder structure: screenshot_path/input_folder/video_name
- Filename pattern: scr-52-00_02_40_331-original
  - scr: screenshot or vid for video sample
  - 52: bitrate ratio (transcoded/original)
  - 00_02_40_331: timestamp (hours_minutes_seconds_milliseconds)
  - original: for comparison mode, otherwise screen for single folder mode
- Summary of processed, skipped, and failed files
- Detailed logs if verbose or debug mode is enabled

## Notes

- Use the -f flag to force regeneration of all samples, deleting existing ones.
- In comparison mode, ensure that the directory structure in both input and compare paths match.
- Bitrate thresholds determine when video samples are generated in comparison mode.
- The --force-all flag processes all videos, even if their bitrates are identical.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any problems or have any questions, please open an issue in the GitHub repository.
