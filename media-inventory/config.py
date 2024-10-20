# File extensions
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov')
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.idx', '.ass', '.ssa')

# FFprobe settings
FFPROBE_PATH = 'ffprobe'  # Assumes ffprobe is in PATH. Change if needed.

# Output settings
DEFAULT_OUTPUT_FOLDER = 'output'
DEFAULT_CSV_FILENAME = 'media_inventory.csv'
DEFAULT_STATS_FILENAME = 'media_inventory_statistics.txt'

# CSV settings
CSV_DELIMITER = '\t'  # Tab-delimited by default

# Verbosity levels
VERBOSITY_QUIET = 0
VERBOSITY_NORMAL = 1
VERBOSITY_VERBOSE = 2

# Performance settings
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for file reading

# Statistics settings
TOP_BOTTOM_COUNT = 10  # Number of top/bottom items to show in statistics

# Language mapping for subtitles and audio
LANGUAGE_MAPPING = {
    'en': 'eng', 
    'no': 'nor', 
    'da': 'dan', 
    'sv': 'swe', 
    'fi': 'fin',
    'fr': 'fre', 
    'de': 'ger', 
    'es': 'spa',
    'pt': 'por', 
    'nl': 'dut',
    'pl': 'pol', 
    'cs': 'cze', 
    'el': 'gre', 
    'tr': 'tur', 
    'ko': 'kor',
    'it': 'ita', 
    'ru': 'rus', 
    'ar': 'ara', 
    'ja': 'jpn', 
    'zh': 'chi',
    'he': 'heb', 
    'hu': 'hun', 
    'ro': 'rum', 
    'sk': 'slo', 
    'sl': 'slv',
    'uk': 'ukr', 
    'id': 'ind', 
    'th': 'tha', 
    'vi': 'vie', 
    'bg': 'bul',
    'is': 'ice', 
    'hr': 'hrv', 
    'lt': 'lit', 
    'lv': 'lav', 
    'et': 'est',
    'hi': 'hin', 
    'ca': 'cat', 
    'gl': 'glg', 
    'eu': 'baq', 
    'sr': 'srp',
    'fa': 'per', 
    'mk': 'mac', 
    'te': 'tel', 
    'ta': 'tam', 
    'ml': 'mal',
    'kn': 'kan', 
    'bn': 'ben'
}

# Resolution categories
RESOLUTION_CATEGORIES = {
    '8K': (7680, 4320),
    '4K': (3840, 2160),
    '1080p': (1920, 1080),
    '720p': (1280, 720),
    '480p': (720, 480),
    'SD': (0, 0)  # Anything below 480p
}

# HDR formats
HDR_FORMATS = ['smpte2084', 'arib-std-b67']

# Audio settings
MAX_AUDIO_STREAMS = 4  # Maximum number of audio streams to consider separately in statistics

# CSV field names
CSV_FIELDNAMES = [
    'File', 'Extension', 'Path', 'Filesize (in GB)', 'Container Format',
    'Video Codec', 'Profile', 'Level', 'Overall Bitrate (in mbps)', 'Video bitrate (in mbps)',
    'BPPPF', 'Width', 'Height', 'Color Space', 'HDR', 'Bits', 'Duration', 'Frame Rate',
    'Audio Languages', 'Audio Languages dedup', 'Non eng/nor languages', 'Audio Languages details', 'Default language', 'Audio Codecs',
    'Audio Channels', 'Audio Channel Layouts', 'Audio Sample Rates', 'Audio Bitrates', 'Audio Stream Count',
    'Subtitle Languages', 'Subtitle languages in file', 'Subtitle formats in file', 'Subtitle stream count in file',
    'Subtitles in file and folder', 'Creation Date', 'Modification Date', 'Raw ffprobe output'
]