import os
import subprocess
import json

def analyze_file(file_path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path], 
                                capture_output=True, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        return None

def check_file(file_path):
    data = analyze_file(file_path)
    if not data:
        return f"Error: {file_path} - Unable to analyze file"
    
    issues = []
    
    # Check video codec
    video_stream = next((stream for stream in data['streams'] if stream['codec_type'] == 'video'), None)
    if video_stream:
        if video_stream['codec_name'] not in ['h264', 'hevc']:
            issues.append(f"Non-standard video codec: {video_stream['codec_name']}")
    else:
        issues.append("No video stream found")
    
    # Check audio codec
    audio_stream = next((stream for stream in data['streams'] if stream['codec_type'] == 'audio'), None)
    if audio_stream:
        if audio_stream['codec_name'] not in ['aac', 'ac3', 'mp3']:
            issues.append(f"Non-standard audio codec: {audio_stream['codec_name']}")
    else:
        issues.append("No audio stream found")
    
    # Check container format
    if data['format']['format_name'] not in ['matroska,webm', 'mov,mp4,m4a,3gp,3g2,mj2']:
        issues.append(f"Non-standard container format: {data['format']['format_name']}")
    
    if issues:
        return f"Issues found in {file_path}: {', '.join(issues)}"
    else:
        return f"No issues found in {file_path}"

def scan_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.mkv', '.mp4', '.avi', '.mov')):
                file_path = os.path.join(root, file)
                print(check_file(file_path))

# Usage
scan_directory('/Volumes/media/media/movies/Pulp Fiction (1994)')