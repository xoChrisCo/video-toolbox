import json
import subprocess
import shlex
import os

from utils import debug_print
from constants import FFPROBE_INFO_CMD, ERROR_MESSAGES

def get_video_info(file_path, debug=False):
    cmd = FFPROBE_INFO_CMD.copy()
    cmd[-1] = cmd[-1].format(input_file=file_path)
    debug_print(f"Executing command: {' '.join(shlex.quote(arg) for arg in cmd)}", debug)
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(ERROR_MESSAGES['ffprobe_error'].format(error=str(e)))

def get_video_bitrate(file_path):
    info = get_video_info(file_path)
    video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    if video_stream and 'bit_rate' in video_stream:
        return int(video_stream['bit_rate'])
    elif 'bit_rate' in info['format']:
        return int(info['format']['bit_rate'])
    return None

def get_video_duration(file_path):
    info = get_video_info(file_path)
    return float(info['format']['duration'])

def get_file_size(file_path):
    return os.path.getsize(file_path)