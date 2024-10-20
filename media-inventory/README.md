# Media Inventory

Media Inventory is a Python script that generates a comprehensive csv file of video files. It analyzes video files in a specified directory, extracting detailed metadata and generating data about your media collection.

## Features

- Scans directories recursively for video files
- Extracts detailed metadata using FFprobe
- Generates statistics on various aspects of your media collection:
  - File formats and sizes
  - Video codecs, resolutions, and bitrates
  - Audio tracks, languages, and formats
  - Subtitle information
- Outputs results to CSV and text files
- Provides a summary of the analysis process

## Requirements

- Python 3.6+
- FFprobe (part of the FFmpeg package)
- Required Python packages:
  - colorama
  - tqdm

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/media-inventory.git
   cd media-inventory
   ```

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Ensure FFprobe is installed and accessible in your system PATH.

## Usage

Run the script from the command line:

```bash
python main.py /path/to/your/media/folder [options]
```

### Options

- `-v`, `--verbosity`: Set verbosity level (0: quiet, 1: normal, 2: verbose)
- `-o`, `--output`: Specify a custom output file name
- `-d`, `--output-dir`: Specify a custom output directory
- `--delimiter`: Set a custom delimiter for CSV output (default is tab)
- `--full-ffprobe`: Include full FFprobe output in the results
- `--pretty-json`: Output raw JSON data in multi-line format

### Example

```bash
python main.py /home/user/movies -v 2 -o my_movie_inventory.csv --full-ffprobe
```

## Output

The script generates two main output files:

1. A CSV file containing detailed information about each video file.
2. A text file with overall statistics about the media collection.

These files are saved in the `output` directory by default, or in the specified custom output directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FFmpeg team for FFprobe
- All contributors and users of this project
