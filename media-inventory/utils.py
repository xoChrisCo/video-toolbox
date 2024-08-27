import os
from datetime import datetime
import re
import subprocess

def create_output_folder(base_output_dir):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_output_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def read_file_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
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

def format_duration(seconds):
    try:
        seconds = float(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)} hours, {int(minutes)} minutes, and {seconds:.2f} seconds"
        elif minutes > 0:
            return f"{int(minutes)} minutes and {seconds:.2f} seconds"
        else:
            return f"{seconds:.2f} seconds"
    except (ValueError, TypeError):
        return "unknown duration"

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

def is_empty_or_na(value):
    return value in (None, "", "N/A", "null", "NULL", "Null")

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

def get_video_duration(file_path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path], capture_output=True, text=True, check=True)
        duration = float(result.stdout)
        return duration
    except (subprocess.CalledProcessError, ValueError) as e:
        return None