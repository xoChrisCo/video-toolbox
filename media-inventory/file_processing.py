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

    file = normalize_path(file)
    print(f"\n{Fore.CYAN}Processing file: {file}{Style.RESET_ALL}")
    
    if debug_level >= 1:
        print(f"{Fore.YELLOW}Analyzing file metadata...{Style.RESET_ALL}")
    details = run_ffprobe(file, debug_level)
    
    if details is None:
        print(f"{Fore.RED}Error: Unable to analyze file metadata.{Style.RESET_ALL}")
        return ["Error"] * 39

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

    file_duration = get_json_value(details, 'format.duration')
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

    print(f"{Fore.YELLOW}Detecting potential issues...{Style.RESET_ALL}")

        # Issue detection
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
        "Multiple audio streams": False
    }

    issue_descriptions = []

    # Check for unknown or empty values
    if any(is_empty_or_na(value) for value in [codec, audio_codecs, subtitle_formats]):
        issues["Unknown metadata"] = True
        issue_descriptions.append("Some file information couldn't be determined")

    # Video codec check
    standard_video_codecs = ['h264', 'hevc', 'vp9', 'av1']
    if codec.lower() not in standard_video_codecs:
        issues["Non-standard video codec"] = True
        issue_descriptions.append(f"Non-standard video codec: {codec}")

    # Audio codec check
    standard_audio_codecs = ['aac', 'ac3', 'eac3', 'mp3', 'opus']
    audio_codec_list = [ac.strip().lower() for ac in audio_codecs.split(',')]
    non_standard_audio = [ac for ac in audio_codec_list if ac not in standard_audio_codecs]
    if non_standard_audio:
        issues["Non-standard audio codec"] = True
        issue_descriptions.append(f"Non-standard audio codec(s): {', '.join(non_standard_audio)}")

    # Subtitle format check
    problematic_subtitle_formats = ['dvd_subtitle', 'hdmv_pgs_subtitle', 'dvb_subtitle']
    subtitle_format_list = [sf.strip().lower() for sf in subtitle_formats.split(',')]
    problematic_subs = [sf for sf in subtitle_format_list if sf in problematic_subtitle_formats]
    if problematic_subs:
        issues["Problematic subtitle format"] = True
        issue_descriptions.append(f"Potentially problematic subtitle format(s): {', '.join(problematic_subs)}")

    # Bitrate check
    try:
        bitrate_value = int(bitrate)
        if bitrate_value > 20000000:  # 20 Mbps
            issues["High bitrate"] = True
            issue_descriptions.append(f"High bitrate ({bitrate_value/1000000:.2f} Mbps) may cause buffering")
        elif bitrate_value < 1000000:  # 1 Mbps
            issues["Low bitrate"] = True
            issue_descriptions.append(f"Low bitrate ({bitrate_value/1000000:.2f} Mbps) may result in poor quality")
    except ValueError:
        if not is_empty_or_na(bitrate):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse bitrate: {bitrate}")

    # Resolution check
    try:
        width_value, height_value = int(width), int(height)
        if (width_value, height_value) not in [(1920, 1080), (3840, 2160), (1280, 720), (720, 480), (720, 576)]:
            issues["Non-standard resolution"] = True
            issue_descriptions.append(f"Non-standard resolution: {width_value}x{height_value}")
    except ValueError:
        if not (is_empty_or_na(width) or is_empty_or_na(height)):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse resolution: {width}x{height}")

    # Frame rate check
    try:
        fps = float(frame_rate)
        if fps not in [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]:
            issues["Non-standard frame rate"] = True
            issue_descriptions.append(f"Non-standard frame rate: {fps} fps")
    except ValueError:
        if not is_empty_or_na(frame_rate):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse frame rate: {frame_rate}")

    # Check for high bit depth
    if bit_depth not in ["8", "N/A"]:
        issues["High bit depth"] = True
        issue_descriptions.append(f"High bit depth video: {bit_depth}-bit")

    # Check for HDR content
    if hdr == "Yes":
        issues["HDR content"] = True
        issue_descriptions.append("HDR content may require tone-mapping")

    # Check for 4K resolution
    if width == "3840" and height == "2160":
        issues["4K content"] = True
        issue_descriptions.append("4K content may be demanding to transcode")

    # Check for complex video profiles
    complex_profiles = ["High 4:2:2", "High 4:4:4"]
    if any(cp in profile for cp in complex_profiles):
        issues["Complex video profile"] = True
        issue_descriptions.append(f"Complex video profile: {profile}")

    # Check for variable frame rate
    if "," in frame_rate or "/" in frame_rate:
        issues["Variable frame rate"] = True
        issue_descriptions.append("Possibly variable frame rate")

    # Check for interlaced content
    if field_order not in ["progressive", "N/A"]:
        issues["Interlaced content"] = True
        issue_descriptions.append(f"Interlaced content: {field_order}")

    # Check for multiple subtitle streams
    try:
        if isinstance(subtitle_stream_count, (int, float)) and subtitle_stream_count > 5:
            issues["High subtitle stream count"] = True
            issue_descriptions.append(f"High number of subtitle streams: {subtitle_stream_count}")
        elif isinstance(subtitle_stream_count, str) and subtitle_stream_count.isdigit() and int(subtitle_stream_count) > 5:
            issues["High subtitle stream count"] = True
            issue_descriptions.append(f"High number of subtitle streams: {subtitle_stream_count}")
    except (ValueError, AttributeError):
        issues["Unknown metadata"] = True
        issue_descriptions.append(f"Unable to parse subtitle stream count: {subtitle_stream_count}")

    # Check for less common container formats
    common_containers = ["matroska", "mov", "mp4", "avi", "mpegts"]
    if not any(cf in str(container_format).lower() for cf in common_containers):
        issues["Uncommon container format"] = True
        issue_descriptions.append(f"Less common container format: {container_format}")

    # Check for very high bitrate
    try:
        bitrate_value = int(bitrate) if isinstance(bitrate, str) else bitrate
        if bitrate_value > 100000000:  # 100 Mbps
            issues["Very high bitrate"] = True
            issue_descriptions.append(f"Very high bitrate ({bitrate_value/1000000:.2f} Mbps) may slow transcoding")
    except (ValueError, TypeError):
        if not is_empty_or_na(bitrate):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse bitrate: {bitrate}")

    # Check for multiple audio streams
    try:
        audio_stream_count_value = int(audio_stream_count) if isinstance(audio_stream_count, str) else audio_stream_count
        if audio_stream_count_value > 3:
            issues["Multiple audio streams"] = True
            issue_descriptions.append(f"Multiple audio streams: {audio_stream_count_value}")
    except (ValueError, TypeError):
        if not is_empty_or_na(audio_stream_count):
            issues["Unknown metadata"] = True
            issue_descriptions.append(f"Unable to parse audio stream count: {audio_stream_count}")

    # Combine issues into a single string
    issue_descriptions.sort()  # Sort the issue descriptions
    issue_description = concat_separator.join(issue_descriptions) if issue_descriptions else "None"

    if file_duration is not None:
        file_duration = float(file_duration)

    if duration is not None:
        try:
            user_duration = float(duration)
        except ValueError:
            print(f"{Fore.RED}Error: Invalid duration specified. Using full file duration.{Style.RESET_ALL}")
            user_duration = file_duration
    else:
        user_duration = file_duration

    # Ensure sample_duration doesn't exceed file_duration
    sample_duration = min(user_duration, file_duration)

    print(f"{Fore.YELLOW}Starting transcode simulation...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Sampling {samples} {'sample' if samples == 1 else 'samples'} of {format_duration(sample_duration)} each{Style.RESET_ALL}")
    

    # Transcode simulation
    transcode_speeds = []
    transcode_speed_ratios = []
    transcode_speed_groups = []
    if samples > 0:
        if file_duration is not None:
            for i in range(samples):
                if i == 0:
                    start_time = 0
                else:
                    max_start = max(0, file_duration - sample_duration)
                    start_time = random.uniform(0, max_start)
                print(f"{Fore.YELLOW}Running transcode simulation {i+1}/{samples} (starting at {format_duration(start_time)})...{Style.RESET_ALL}")
                speed = simulate_plex_transcoding(file, start_time, sample_duration, hwaccel, debug_level)

                if speed == "Aborted":
                    print(f"{Fore.YELLOW}Transcode simulation {i+1} aborted due to exceeding time limit.{Style.RESET_ALL}")
                    transcode_speeds.append("<1")
                    transcode_speed_ratios.append("<1")
                    transcode_speed_groups.append("Low")
                else:
                    transcode_speeds.append(speed)
                    speed_ratio = calculate_transcode_speed_ratio(speed, frame_rate)
                    transcode_speed_ratios.append(speed_ratio)
                    transcode_speed_groups.append(get_transcode_speed_group(speed_ratio))

                print(f"{Fore.GREEN}Transcode simulation {i+1} complete. Speed: {speed}x{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Error: Unable to determine file duration.{Style.RESET_ALL}")
            transcode_speeds = ["Error"] * samples
            transcode_speed_ratios = ["Error"] * samples
            transcode_speed_groups = ["Error"] * samples

    print(f"{Fore.GREEN}File processing complete.{Style.RESET_ALL}")

    try:
        return [
            file, file_extension, file_path, filename, filesize, container_format,
            codec, codec_long_name, profile, level, bitrate, width, height,
            color_space, color_primaries, color_transfer, color_range, chroma_location,
            field_order, refs, bits_per_raw_sample, pix_fmt, hdr, bit_depth,
            duration, frame_rate, audio_codecs, audio_codec_long_names, audio_channels,
            audio_sample_rates, audio_bitrates, audio_bit_depth, audio_stream_count,
            subtitle_languages, subtitle_formats, subtitle_stream_count,
            creation_date, modification_date,
            "1" if any(issues.values()) else "0",
            issue_description,  
        ] + [str(int(issues[key])) for key in issues] + transcode_speeds + transcode_speed_ratios + transcode_speed_groups
    
    except Exception as e:
        error_message = f"Error processing file: {str(e)}"
        if debug_level >= 1:
            print(f"\n{Fore.RED}{error_message}")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception traceback: {traceback.format_exc()}{Style.RESET_ALL}")
        error_return = ["Error"] * (39 + len(issues) + len(transcode_speeds) + len(transcode_speed_ratios) + len(transcode_speed_groups))
        error_return[0] = file_path 
        error_return[-1] = error_message 
        return error_return

def run_ffprobe(file_path, debug_level):
    ffprobe_command = ['ffprobe']

    if debug_level >= 2:
        ffprobe_command.extend(['-v', 'debug'])
    elif debug_level == 1:
        ffprobe_command.extend(['-v', 'warning'])
    else:
        ffprobe_command.extend(['-v', 'error'])

    ffprobe_command.extend(['-print_format', 'json', '-show_format', '-show_streams', file_path])

    if debug_level >= 2:
        print(f"{Fore.GREEN}Running FFprobe command: {' '.join(shlex.quote(str(arg)) for arg in ffprobe_command)}{Style.RESET_ALL}")

    try:
        result = subprocess.run(ffprobe_command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        if debug_level >= 1:
            print(f"{Fore.YELLOW}FFprobe command failed: {e}")
            print(f"FFprobe stderr: {e.stderr}{Style.RESET_ALL}")
        return None

def simulate_plex_transcoding(file_path, start_time, duration, hwaccel, debug_level):
    command = ['ffmpeg']

    if debug_level >= 2:
        command.extend(['-v', 'debug'])
    elif debug_level == 1:
        command.extend(['-v', 'warning'])
    else:
        command.extend(['-v', 'error'])

    command.extend(['-hwaccel', hwaccel])

    # Add input file
    command.extend(['-i', file_path])

    # Add start time
    command.extend(['-ss', str(start_time)])

    # Add duration
    command.extend(['-t', str(duration)])

    if hwaccel == 'qsv':
        command.extend([
            '-c:v', 'h264_qsv',
            '-preset', 'veryfast',
            '-crf', '23',
        ])
    elif hwaccel == 'videotoolbox':
        command.extend([
            '-c:v', 'hevc_videotoolbox',
            '-preset', 'fast',
            '-crf', '23',
        ])
    else:  # No hardware acceleration
        command.extend([
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
        ])

    command.extend([
        '-c:a', 'aac',
        '-b:a', '128k',
        '-f', 'null',
        '-'
    ])

    if debug_level >= 2:
        print(f"{Fore.CYAN}Running FFmpeg command: {' '.join(shlex.quote(str(arg)) for arg in command)}{Style.RESET_ALL}")

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
                print(f"{Fore.YELLOW}FFmpeg command failed with return code {return_code}")
                print(f"FFmpeg stderr: {stderr}{Style.RESET_ALL}")
            return "Error"
    except Exception as e:
        if debug_level >= 1:
            print(f"{Fore.YELLOW}An error occurred: {str(e)}{Style.RESET_ALL}")
        return "Error"