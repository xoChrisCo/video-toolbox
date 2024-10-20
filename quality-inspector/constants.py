# Default video file extensions to process
DEFAULT_VIDEO_EXTENSIONS = (
    '.mkv', '.mp4', '.avi', '.mov', '.wmv', 
    '.flv', '.webm', '.m4v', '.mpeg', '.mpg', 
    '.m2ts', '.ts'
)

# Default path to save samples
DEFAULT_SAMPLE_PATH = "./samples"

# Default path to save csv file
DEFAULT_SAMPLE_CSV_PATH = "./csv"

# Timeout for ffmpeg commands (in seconds)
FFMPEG_TIMEOUT = 30

# Default number of screenshot samples to take
DEFAULT_SCREENSHOT_SAMPLES = 5

# Default number of video samples to take
DEFAULT_VIDEO_SAMPLES = 3

# Default length of video samples in seconds
DEFAULT_VIDEO_LENGTH = 10

# Default lower threshold for bitrate difference in percent
DEFAULT_LOWER_THRESHOLD = 60

# Default upper threshold for bitrate difference in percent
DEFAULT_UPPER_THRESHOLD = 105

# Colors for console output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    LIGHT_BLUE = "\033[94m"

# Styles for console output
class Styles:
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    ITALIC = "\033[3m"

# Error messages
ERROR_MESSAGES = {
    'path_not_exist': "Error: The path {path} does not exist.",
    'invalid_extension': "Error: Invalid file extension. Supported extensions are: {extensions}",
    'ffmpeg_error': "Error executing FFmpeg command: {error}",
    'ffprobe_error': "Error executing FFprobe command: {error}",
}

# Success messages
SUCCESS_MESSAGES = {
    'processing_complete': "Processing complete. Files processed: {processed}, skipped: {skipped}, failed: {failed}\nTotal screenshots generated: {total_screenshots}\nTotal video samples generated: {total_video_samples}",
    'screenshot_created': "Created screenshot {index}/{total} for {filename}",
    'video_info_written': "Video information written to {filename}",
    'samples_created': "Created {screenshots} screenshots and {video_samples} video samples for {filename}"
}

# Progress messages
PROGRESS_MESSAGES = {
    'scanning_directory': "Scanning directory: {directory}",
    'processing_file': "Processing {index}/{total}: {filename}",
    'creating_screenshots': "Creating screenshots: {index}/{total} ({progress:.2f}%) - {current}/{samples} - {filename}",
}

# FFmpeg command template for video sample extraction
FFMPEG_VIDEO_SAMPLE_CMD = [
    'ffmpeg', '-ss', '{timestamp}', '-i', '{input_file}',
    '-t', '{duration}', '-c', 'copy', '{output_file}'
]

# FFmpeg command templates
FFMPEG_SCREENSHOT_CMD = [
    'ffmpeg', '-ss', '{timestamp}', '-i', '{input_file}',
    '-vframes', '1', '{output_file}'
]

# FFprobe command template
FFPROBE_INFO_CMD = [
    'ffprobe', '-v', 'quiet', '-print_format', 'json',
    '-show_format', '-show_streams', '{input_file}'
]