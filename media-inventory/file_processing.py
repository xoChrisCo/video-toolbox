import os
import json
import subprocess
from datetime import datetime
import re
import random
from colorama import init, Fore, Back, Style # type: ignore
import traceback
import shlex
from utils import (
    format_duration, normalize_path, get_json_value, is_empty_or_na,
    calculate_transcode_speed_ratio, get_transcode_speed_group, get_video_duration
)
import time
import signal

def process_file(file, duration, samples, concat_separator, hwaccel, debug_level):
    """Main function to process a video file."""
    file = normalize_path(file)
    print_debug(f"\nProcessing file: {file}", debug_level, 1)

    details = analyze_file_metadata(file, debug_level)
    if details is None:
        print(f"{Fore.RED}Error: Unable to analyze file metadata.{Style.RESET_ALL}")
        return ["Error"] * 40

    file_info = extract_file_info(file, details)
    video_info = extract_video_info(details)
    audio_info = extract_audio_info(details)
    subtitle_info = extract_subtitle_info(details)

    # Check if duration is valid
    file_duration = file_info.get('duration')
    if file_duration is None or not isinstance(file_duration, (int, float)) or file_duration <= 0:
        print(f"{Fore.RED}Error: Invalid file duration: {file_duration}{Style.RESET_ALL}")
        return ["Error"] * 40

    issues, issue_descriptions = detect_issues(file_info, video_info, audio_info, subtitle_info)

    # Only simulate transcoding if samples > 0
    if samples > 0:
        transcode_results = simulate_transcoding(
            file, 
            file_duration, 
            duration, 
            samples, 
            hwaccel, 
            video_info['frame_rate'], 
            debug_level
        )
    else:
        # If no samples are requested, return empty lists for transcode results
        transcode_results = ([], [], [])

    return compile_results(file_info, video_info, audio_info, subtitle_info, issues, issue_descriptions, transcode_results, concat_separator)

def analyze_file_metadata(file_path, debug_level):
    """Run ffprobe to analyze file metadata."""
    print_debug("Analyzing file metadata...", debug_level, 1)
    ffprobe_command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-show_format',
        '-show_frames',
        '-read_intervals', '%+#1',
        '-i', file_path
    ]
    return run_ffprobe(ffprobe_command, debug_level)

def extract_file_info(file, details):
    """Extract basic file information."""
    return {
        'file': file,
        'extension': os.path.splitext(file)[1][1:],
        'path': os.path.dirname(file),
        'filename': os.path.basename(file),
        'size': os.path.getsize(file),
        'creation_date': os.path.getctime(file),
        'modification_date': os.path.getmtime(file),
        'container_format': get_json_value(details, 'format.format_name'),
        'duration': float(get_json_value(details, 'format.duration', 0))
    }

def extract_video_info(details):
    """Extract video stream information."""
    video_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'video']
    video_info = {
        'codec': get_json_value(video_streams, '0.codec_name'),
        'codec_long_name': get_json_value(video_streams, '0.codec_long_name'),
        'profile': get_json_value(video_streams, '0.profile'),
        'level': get_json_value(video_streams, '0.level'),
        'bitrate': get_json_value(details, 'format.bit_rate'),
        'width': get_json_value(video_streams, '0.width'),
        'height': get_json_value(video_streams, '0.height'),
        'color_space': get_json_value(video_streams, '0.color_space'),
        'color_primaries': get_json_value(video_streams, '0.color_primaries'),
        'color_transfer': get_json_value(video_streams, '0.color_transfer'),
        'color_range': get_json_value(video_streams, '0.color_range'),
        'chroma_location': get_json_value(video_streams, '0.chroma_location'),
        'field_order': get_json_value(video_streams, '0.field_order'),
        'refs': get_json_value(video_streams, '0.refs'),
        'bits_per_raw_sample': get_json_value(video_streams, '0.bits_per_raw_sample'),
        'pix_fmt': get_json_value(video_streams, '0.pix_fmt'),
        'frame_rate': parse_frame_rate(get_json_value(video_streams, '0.avg_frame_rate')),
        'stream_count': len(video_streams),
        'dolby_vision_profile': detect_dolby_vision_profile(video_streams)
    }
    video_info['hdr'] = detect_hdr(video_info['color_transfer'])
    video_info['bit_depth'] = detect_bit_depth(video_info['pix_fmt'], video_info['bits_per_raw_sample'])
    return video_info

def extract_audio_info(details):
    """Extract audio stream information."""
    audio_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'audio']
    return {
        'codecs': ", ".join(str(stream.get('codec_name', 'N/A')) for stream in audio_streams),
        'codec_long_names': ", ".join(str(stream.get('codec_long_name', 'N/A')) for stream in audio_streams),
        'channels': ", ".join(str(stream.get('channels', 'N/A')) for stream in audio_streams),
        'sample_rates': ", ".join(str(stream.get('sample_rate', 'N/A')) for stream in audio_streams),
        'bitrates': ", ".join(str(stream.get('bit_rate', 'N/A')) for stream in audio_streams),
        'bit_depth': ", ".join(str(stream.get('bits_per_raw_sample', 'N/A')) for stream in audio_streams),
        'stream_count': len(audio_streams)
    }

def extract_subtitle_info(details):
    """Extract subtitle stream information."""
    subtitle_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'subtitle']
    return {
        'languages': ", ".join(str(stream.get('tags', {}).get('language', 'N/A')) for stream in subtitle_streams),
        'formats': ", ".join(str(stream.get('codec_name', 'N/A')) for stream in subtitle_streams),
        'stream_count': len(subtitle_streams)
    }

def detect_issues(file_info, video_info, audio_info, subtitle_info):
    """Detect potential issues with the video file."""
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
        "Multiple audio streams": False,
        "Dolby Vision Profile 5": False
    }
    issue_descriptions = []

    # Check for unknown or empty values
    if any(is_empty_or_na(value) for value in [video_info['codec'], audio_info['codecs'], subtitle_info['formats']]):
        issues["Unknown metadata"] = True
        issue_descriptions.append("Some file information couldn't be determined")

    # Video codec check
    standard_video_codecs = ['h264', 'hevc', 'vp9', 'av1']
    if video_info['codec'].lower() not in standard_video_codecs:
        issues["Non-standard video codec"] = True
        issue_descriptions.append(f"Non-standard video codec: {video_info['codec']}")

    # Audio codec check
    standard_audio_codecs = ['aac', 'ac3', 'eac3', 'mp3', 'opus']
    audio_codec_list = [ac.strip().lower() for ac in audio_info['codecs'].split(',')]
    non_standard_audio = [ac for ac in audio_codec_list if ac not in standard_audio_codecs]
    if non_standard_audio:
        issues["Non-standard audio codec"] = True
        issue_descriptions.append(f"Non-standard audio codec(s): {', '.join(non_standard_audio)}")

    # Subtitle format check
    problematic_subtitle_formats = ['dvd_subtitle', 'hdmv_pgs_subtitle', 'dvb_subtitle']
    subtitle_format_list = [sf.strip().lower() for sf in subtitle_info['formats'].split(',')]
    problematic_subs = [sf for sf in subtitle_format_list if sf in problematic_subtitle_formats]
    if problematic_subs:
        issues["Problematic subtitle format"] = True
        issue_descriptions.append(f"Potentially problematic subtitle format(s): {', '.join(problematic_subs)}")

    # Bitrate check
    try:
        bitrate_value = int(video_info['bitrate'])
        if bitrate_value > 20000000:  # 20 Mbps
            issues["High bitrate"] = True
            issue_descriptions.append(f"High bitrate ({bitrate_value/1000000:.2f} Mbps) may cause buffering")
        elif bitrate_value < 1000000:  # 1 Mbps
            issues["Low bitrate"] = True
            issue_descriptions.append(f"Low bitrate ({bitrate_value/1000000:.2f} Mbps) may result in poor quality")
    except ValueError:
        if not is_empty_or_na(video_info['bitrate']):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse bitrate: {video_info['bitrate']}")

    # Resolution check
    try:
        width_value, height_value = int(video_info['width']), int(video_info['height'])
        if (width_value, height_value) not in [(1920, 1080), (3840, 2160), (1280, 720), (720, 480), (720, 576)]:
            issues["Non-standard resolution"] = True
            issue_descriptions.append(f"Non-standard resolution: {width_value}x{height_value}")
    except ValueError:
        if not (is_empty_or_na(video_info['width']) or is_empty_or_na(video_info['height'])):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse resolution: {video_info['width']}x{video_info['height']}")

    # Frame rate check
    try:
        fps = float(video_info['frame_rate'])
        if fps not in [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]:
            issues["Non-standard frame rate"] = True
            issue_descriptions.append(f"Non-standard frame rate: {fps} fps")
    except ValueError:
        if not is_empty_or_na(video_info['frame_rate']):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse frame rate: {video_info['frame_rate']}")

    # Check for high bit depth
    if video_info['bit_depth'] not in ["8", "N/A"]:
        issues["High bit depth"] = True
        issue_descriptions.append(f"High bit depth video: {video_info['bit_depth']}-bit")

    # Check for HDR content
    if video_info['hdr'] == "Yes":
        issues["HDR content"] = True
        issue_descriptions.append("HDR content may require tone-mapping")

    # Check for 4K resolution
    if video_info['width'] == "3840" and video_info['height'] == "2160":
        issues["4K content"] = True
        issue_descriptions.append("4K content may be demanding to transcode")

    # Check for complex video profiles
    complex_profiles = ["High 4:2:2", "High 4:4:4"]
    if any(cp in video_info['profile'] for cp in complex_profiles):
        issues["Complex video profile"] = True
        issue_descriptions.append(f"Complex video profile: {video_info['profile']}")

    # Check for variable frame rate
    if "," in video_info['frame_rate'] or "/" in video_info['frame_rate']:
        issues["Variable frame rate"] = True
        issue_descriptions.append("Possibly variable frame rate")

    # Check for interlaced content
    if video_info['field_order'] not in ["progressive", "N/A"]:
        issues["Interlaced content"] = True
        issue_descriptions.append(f"Interlaced content: {video_info['field_order']}")

    # Check for multiple subtitle streams
    try:
        subtitle_stream_count = int(subtitle_info['stream_count'])
        if subtitle_stream_count > 5:
            issues["High subtitle stream count"] = True
            issue_descriptions.append(f"High number of subtitle streams: {subtitle_stream_count}")
    except ValueError:
        if not is_empty_or_na(subtitle_info['stream_count']):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse subtitle stream count: {subtitle_info['stream_count']}")

    # Check for less common container formats
    common_containers = ["matroska", "mov", "mp4", "avi", "mpegts"]
    if not any(cf in str(file_info['container_format']).lower() for cf in common_containers):
        issues["Uncommon container format"] = True
        issue_descriptions.append(f"Less common container format: {file_info['container_format']}")

    # Check for very high bitrate
    try:
        bitrate_value = int(video_info['bitrate'])
        if bitrate_value > 100000000:  # 100 Mbps
            issues["Very high bitrate"] = True
            issue_descriptions.append(f"Very high bitrate ({bitrate_value/1000000:.2f} Mbps) may slow transcoding")
    except ValueError:
        if not is_empty_or_na(video_info['bitrate']):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse bitrate: {video_info['bitrate']}")

    # Check for multiple audio streams
    try:
        audio_stream_count = int(audio_info['stream_count'])
        if audio_stream_count > 3:
            issues["Multiple audio streams"] = True
            issue_descriptions.append(f"Multiple audio streams: {audio_stream_count}")
    except ValueError:
        if not is_empty_or_na(audio_info['stream_count']):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse audio stream count: {audio_info['stream_count']}")
    
    # Check for Dolby Vision Profile 5
    if video_info['dolby_vision_profile'] == 5:
        issues["Dolby Vision Profile 5"] = True
        issue_descriptions.append("Dolby Vision Profile 5 detected (unplayable in Plex)")

    return issues, issue_descriptions

def simulate_transcoding(file, file_duration, user_duration, samples, hwaccel, frame_rate, debug_level):
    """Simulate Plex transcoding and collect speed data."""
    print_debug("Starting transcode simulation...", debug_level, 1)
    
    # Error checking
    if file_duration is None or user_duration is None:
        print_debug(f"Error: Invalid duration. file_duration: {file_duration}, user_duration: {user_duration}", debug_level, 1)
        return [], [], []
    
    try:
        file_duration = float(file_duration)
        user_duration = float(user_duration)
    except ValueError:
        print_debug(f"Error: Unable to convert durations to float. file_duration: {file_duration}, user_duration: {user_duration}", debug_level, 1)
        return [], [], []
    
    sample_duration = min(user_duration, file_duration)
    
    if sample_duration <= 0:
        print_debug(f"Error: Invalid sample duration: {sample_duration}", debug_level, 1)
        return [], [], []
    
    if samples > 0:
        print(f"Sampling {samples} {'sample' if samples == 1 else 'samples'} of {format_duration(sample_duration)} each", end='')

    transcode_speeds = []
    transcode_speed_ratios = []
    transcode_speed_groups = []

    for i in range(samples):
        start_time = 0 if i == 0 else random.uniform(0, max(0, file_duration - sample_duration))
        print_debug(f"\nRunning transcode simulation {i+1}/{samples} (starting at {format_duration(start_time)})...", debug_level, 1)
        
        speed = simulate_plex_transcoding(file, start_time, sample_duration, hwaccel, debug_level)
        
        if speed == "Aborted":
            print_debug(f"Transcode simulation {i+1} aborted due to exceeding time limit.", debug_level, 1)
            transcode_speeds.append("<1")
            transcode_speed_ratios.append("<1")
            transcode_speed_groups.append("Low")
        else:
            transcode_speeds.append(speed)
            speed_ratio = calculate_transcode_speed_ratio(speed, frame_rate)
            transcode_speed_ratios.append(speed_ratio)
            transcode_speed_groups.append(get_transcode_speed_group(speed_ratio))

        print_debug(f"Transcode simulation {i+1} complete. Speed: {speed}x", debug_level, 1)

    return transcode_speeds, transcode_speed_ratios, transcode_speed_groups

def detect_dolby_vision_profile(video_streams):
    """Detect Dolby Vision profile from video streams."""
    for stream in video_streams:
        # Check in side_data_list
        side_data_list = stream.get('side_data_list', [])
        for side_data in side_data_list:
            if side_data.get('side_data_type') == 'DOVI configuration record':
                return side_data.get('dv_profile')
        
        # Check in tags
        tags = stream.get('tags', {})
        if 'DOVI_PROFILE' in tags:
            return tags['DOVI_PROFILE']
        
        # Check directly in stream
        if 'dv_profile' in stream:
            return stream['dv_profile']
    
    return None

def compile_results(file_info, video_info, audio_info, subtitle_info, issues, issue_descriptions, transcode_results, concat_separator=", "):
    """Compile all gathered information into a single result list."""
    transcode_speeds, transcode_speed_ratios, transcode_speed_groups = transcode_results
    
    return [
        file_info['file'], file_info['extension'], file_info['path'], file_info['filename'],
        file_info['size'], file_info['container_format'],
        video_info['codec'], video_info['codec_long_name'], video_info['profile'], video_info['level'],
        video_info['bitrate'], video_info['width'], video_info['height'],
        video_info['color_space'], video_info['color_primaries'], video_info['color_transfer'],
        video_info['color_range'], video_info['chroma_location'],
        video_info['field_order'], video_info['refs'], video_info['bits_per_raw_sample'],
        video_info['pix_fmt'], video_info['hdr'], video_info['bit_depth'],
        file_info['duration'], video_info['frame_rate'],
        audio_info['codecs'], audio_info['codec_long_names'], audio_info['channels'],
        audio_info['sample_rates'], audio_info['bitrates'], audio_info['bit_depth'],
        audio_info['stream_count'],
        subtitle_info['languages'], subtitle_info['formats'], subtitle_info['stream_count'],
        file_info['creation_date'], file_info['modification_date'],
        "1" if any(issues.values()) else "0",
        concat_separator.join(sorted(issue_descriptions)) if issue_descriptions else "None",
    ] + [str(int(issues[key])) for key in issues] + transcode_speeds + transcode_speed_ratios + transcode_speed_groups


# Helper functions

def print_debug(message, debug_level, required_level):
    """Print debug messages if the debug level is high enough."""
    if debug_level >= required_level:
        print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

def construct_ffprobe_command(file_path, debug_level):
    """Construct the ffprobe command based on the debug level."""
    command = ['ffprobe']
    if debug_level >= 2:
        command.extend(['-v', 'debug'])
    elif debug_level == 1:
        command.extend(['-v', 'warning'])
    else:
        command.extend(['-v', 'error'])
    command.extend(['-print_format', 'json', '-show_format', '-show_streams', file_path])
    return command

def run_ffprobe(command, debug_level):
    """Run the ffprobe command and return the results."""
    if debug_level >= 2:
        print(f"{Fore.GREEN}Running FFprobe command: {' '.join(shlex.quote(str(arg)) for arg in command)}{Style.RESET_ALL}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print_debug(f"FFprobe command failed: {e}\nFFprobe stderr: {e.stderr}", debug_level, 1)
        return None

def parse_frame_rate(frame_rate):
    """Parse and convert frame rate to a decimal number."""
    if isinstance(frame_rate, str):
        if '/' in frame_rate:
            try:
                num, den = map(int, frame_rate.split('/'))
                return f"{num/den:.3f}" if den != 0 else "N/A"
            except ValueError:
                return "N/A"
        elif frame_rate.replace('.', '', 1).isdigit():
            return f"{float(frame_rate):.3f}"
    return "N/A"

def detect_hdr(color_transfer):
    """Detect if the video has HDR content."""
    return "Yes" if 'smpte2084' in str(color_transfer).lower() or 'hlg' in str(color_transfer).lower() else "No"

def detect_bit_depth(pix_fmt, bits_per_raw_sample):
    """Detect the bit depth of the video."""
    return "10" if '10' in str(pix_fmt) else bits_per_raw_sample if bits_per_raw_sample != "N/A" else "N/A"

def detect_dolby_vision_profile_5(details):
    """Detect if the video has Dolby Vision Profile 5."""
    video_streams = [stream for stream in details.get('streams', []) if stream.get('codec_type') == 'video']
    for stream in video_streams:
        if 'dolby_vision_profile' in stream and stream['dolby_vision_profile'] == '5':
            return True
    return False


def simulate_plex_transcoding(file_path, start_time, duration, hwaccel, debug_level):
    plex_transcoder = '/usr/lib/plexmediaserver/Plex Transcoder'
    command = [plex_transcoder]

    if debug_level >= 2:
        command.extend(['-v', 'debug'])
    elif debug_level == 1:
        command.extend(['-v', 'warning'])
    else:
        command.extend(['-v', 'error'])

    # Add input file
    command.extend(['-i', file_path])

    # Add start time
    command.extend(['-ss', str(start_time)])

    # Add duration
    command.extend(['-t', str(duration)])

    # Hardware acceleration
    if hwaccel == 'qsv':
        command.extend(['-hwaccel', 'qsv'])
    elif hwaccel == 'videotoolbox':
        command.extend(['-hwaccel', 'videotoolbox'])
    # For other acceleration types, you may need to adjust based on Plex Transcoder's capabilities

    # Output settings (adjust these based on your Plex settings)
    command.extend([
        '-c:v', 'libx264',  # You might need to change this based on Plex Transcoder's available codecs
        '-preset', 'veryfast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-f', 'null',
        '-'
    ])

    if debug_level >= 2:
        print(f"{Fore.CYAN}Running Plex Transcoder command: {' '.join(shlex.quote(str(arg)) for arg in command)}{Style.RESET_ALL}")

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        start_time = time.time()

        while True:
            return_code = process.poll()
            if return_code is not None:
                # Process has finished
                break
            
            # Check if we've exceeded the duration
            if time.time() - start_time > duration + 5:  # Add 5 seconds buffer
                print(f"{Fore.YELLOW}Transcode taking too long. Aborting...{Style.RESET_ALL}")
                process.send_signal(signal.SIGINT)  # Send interrupt signal
                time.sleep(1)  # Give it a second to clean up
                if process.poll() is None:  # If it's still running
                    process.terminate()  # Terminate more forcefully
                return "Aborted"

            time.sleep(0.1)  # Check every 0.1 seconds

        stdout, stderr = process.communicate()
        
        if return_code == 0:
            match = re.search(r'speed=\s*([\d.]+)x', stderr)
            if match:
                return float(match.group(1))
            else:
                return "N/A"
        else:
            if debug_level >= 1:
                print(f"{Fore.YELLOW}Plex Transcoder command failed with return code {return_code}")
                print(f"Plex Transcoder stderr: {stderr}{Style.RESET_ALL}")
            return "Error"
    except Exception as e:
        if debug_level >= 1:
            print(f"{Fore.YELLOW}An error occurred: {str(e)}{Style.RESET_ALL}")
        return "Error"