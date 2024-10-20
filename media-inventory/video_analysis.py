import os
import json
import subprocess
from datetime import datetime
from colorama import Fore, Style # type: ignore

from utils import safe_float, remove_statistics_tags
from config import FFPROBE_PATH, SUBTITLE_EXTENSIONS, HDR_FORMATS, LANGUAGE_MAPPING

def get_video_metadata(file_path, full_ffprobe_output=False, pretty_json=False):
    """
    Extract metadata from a video file using ffprobe.

    Args:
    file_path (str): Path to the video file.
    full_ffprobe_output (bool): Whether to include full ffprobe output.
    pretty_json (bool): Whether to format JSON output for readability.

    Returns:
    dict: A dictionary containing the extracted metadata.
    """
    try:
        # Run ffprobe command
        cmd = [
            FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse the JSON output
        data = json.loads(result.stdout)
        
        # Extract required metadata
        format_info = data['format']
        video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
        audio_streams = [s for s in data['streams'] if s['codec_type'] == 'audio']
        subtitle_streams = [s for s in data['streams'] if s['codec_type'] == 'subtitle']
        
        # Calculate video bitrate
        duration = safe_float(format_info.get('duration', 0))
        file_size = safe_float(format_info.get('size', 0))
        video_bitrate = (file_size * 8) / (duration * 1000000) if duration > 0 else 0
        
        # Calculate BPPPF
        width = safe_float(video_stream.get('width', 0))
        height = safe_float(video_stream.get('height', 0))
        frame_rate = safe_float(video_stream.get('avg_frame_rate', '0/1').split('/')[0]) / safe_float(video_stream.get('avg_frame_rate', '0/1').split('/')[1])
        bpppf = (video_bitrate * 1000000) / (width * height * frame_rate) if all([width, height, frame_rate]) else 0

        # Check for HDR content
        hdr = 'Yes' if video_stream.get('color_transfer', '').lower() in HDR_FORMATS else 'No'
        
        # Gather audio information
        audio_languages = [s.get('tags', {}).get('language', 'und') for s in audio_streams]
        audio_codecs = [s.get('codec_name', 'unknown') for s in audio_streams]
        audio_channels = [s.get('channels', 0) for s in audio_streams]
        audio_channel_layouts = [s.get('channel_layout', 'unknown') for s in audio_streams]
        audio_sample_rates = [s.get('sample_rate', 'unknown') for s in audio_streams]
        audio_bitrates = [float(s.get('bit_rate', 0)) / 1000 for s in audio_streams]  # Convert to kbps
        
        # Gather subtitle information
        subtitle_languages_file = [s.get('tags', {}).get('language', 'und') for s in subtitle_streams]
        subtitle_formats_file = [s.get('codec_name', 'unknown') for s in subtitle_streams]
        
        # Get subtitles in folder
        folder_path = os.path.dirname(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        subtitles_in_folder = []
        subtitle_languages_folder = []

        for f in os.listdir(folder_path):
            if any(f.lower().endswith(ext) for ext in SUBTITLE_EXTENSIONS):
                if f.startswith(file_name):
                    subtitles_in_folder.append(f)
                    # Extract language code
                    parts = os.path.splitext(f)[0].split('.')
                    if len(parts) > 1:
                        lang = parts[-1]
                        if len(lang) == 2 or len(lang) == 3:  # Assuming 2 or 3 letter language codes
                            subtitle_languages_folder.append(lang)

        # Combine and deduplicate subtitle languages
        all_subtitle_languages = list(set(subtitle_languages_file + subtitle_languages_folder))
        
        # Subtitles in both file and folder
        subtitles_in_file_and_folder = list(set(subtitle_languages_file + subtitle_languages_folder))
        
        # Audio languages dedup
        audio_languages_dedup = list(dict.fromkeys(audio_languages))
        
        # Non eng/nor languages
        non_eng_nor_languages = list(set([lang for lang in audio_languages_dedup if lang not in ['eng', 'nor', 'und']]))

        # Get bits
        bits = get_video_bits(video_stream)

        # Prepare the raw ffprobe output JSON
        if full_ffprobe_output:
            raw_output = json.dumps(data, indent=2 if pretty_json else None)
        else:
            raw_output = json.dumps(prepare_reduced_raw_output(format_info, video_stream, audio_streams, subtitle_streams), indent=2 if pretty_json else None)

        metadata = {
            'File': os.path.basename(file_path),
            'Extension': os.path.splitext(file_path)[1],
            'Path': os.path.dirname(file_path),
            'Filesize (in GB)': round(float(format_info.get('size', 0)) / (1024 * 1024 * 1024), 2),
            'Container Format': format_info.get('format_name', 'unknown'),
            'Video Codec': video_stream.get('codec_name', 'unknown'),
            'Profile': video_stream.get('profile', 'unknown'),
            'Level': video_stream.get('level', 'unknown'),
            'Overall Bitrate (in mbps)': round(float(format_info.get('bit_rate', 0)) / 1_000_000, 2),
            'Video bitrate (in mbps)': round(video_bitrate, 2),
            'BPPPF': round(bpppf, 6),
            'Width': width,
            'Height': height,
            'Color Space': video_stream.get('color_space', 'unknown'),
            'HDR': 'Yes' if video_stream.get('color_transfer', '').lower() in ['smpte2084', 'arib-std-b67'] else 'No',
            'Bits': bits,
            'Duration': format_info.get('duration', 'unknown'),
            'Frame Rate': round(frame_rate, 2),
            'Audio Languages': ', '.join(audio_languages),
            'Audio Languages details': ', '.join([f"{lang}: {codec}, {ch}ch ({layout}), {sr}Hz, {br:.0f}kbps" 
                for lang, codec, ch, layout, sr, br in zip(audio_languages, audio_codecs, audio_channels, audio_channel_layouts, audio_sample_rates, audio_bitrates)]),
            'Audio Channels': ', '.join([str(ch) for ch in audio_channels]),
            'Audio Channel Layouts': ', '.join(audio_channel_layouts),
            'Audio Languages dedup': ', '.join(audio_languages_dedup),
            'Non eng/nor languages': ', '.join(non_eng_nor_languages),
            'Default language': next((s.get('tags', {}).get('language', 'und') for s in audio_streams if s.get('disposition', {}).get('default') == 1), 'unknown'),
            'Audio Codecs': ', '.join(audio_codecs),
            'Audio Sample Rates': ', '.join(audio_sample_rates),
            'Audio Bitrates': ', '.join([f"{br:.0f}" for br in audio_bitrates]),
            'Audio Stream Count': len(audio_streams),
            'Subtitle Languages': ', '.join(all_subtitle_languages),
            'Subtitle languages in file': ', '.join(subtitle_languages_file),
            'Subtitle formats in file': ', '.join(subtitle_formats_file),
            'Subtitle stream count in file': len(subtitle_streams),
            'Subtitles in file and folder': ', '.join(subtitles_in_file_and_folder),
            'Creation Date': format_info.get('tags', {}).get('creation_time', 'unknown'),
            'Modification Date': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'Raw ffprobe output': raw_output
        }
        
        return metadata
    except Exception as e:
        print(f"{Fore.RED}Error processing {file_path}: {str(e)}{Style.RESET_ALL}")
        return None

def detect_atmos(audio_stream):
    """
    Detect if an audio stream is Atmos.

    Args:
    audio_stream (dict): The audio stream data from ffprobe.

    Returns:
    bool: True if Atmos is detected, False otherwise.
    """
    # Check for Atmos in audio tags
    if 'tags' in audio_stream:
        for tag, value in audio_stream['tags'].items():
            if 'atmos' in str(value).lower():
                return True
    # Check for Atmos in codec name
    if 'codec_name' in audio_stream and 'atmos' in audio_stream['codec_name'].lower():
        return True
    return False

def get_video_bits(video_stream):
    """
    Get the bit depth of the video stream.

    Args:
    video_stream (dict): The video stream data from ffprobe.

    Returns:
    str: The bit depth of the video, or 'unknown' if it can't be determined.
    """
    bits = video_stream.get('bits_per_raw_sample') or \
           video_stream.get('bit_depth') or \
           video_stream.get('bits_per_sample')
    
    if not bits:
        # Check in pix_fmt for bit depth
        pix_fmt = video_stream.get('pix_fmt', '')
        if 'p10' in pix_fmt:
            bits = '10'
        elif 'p12' in pix_fmt:
            bits = '12'
        elif 'p14' in pix_fmt:
            bits = '14'
        elif 'p16' in pix_fmt:
            bits = '16'
        elif any(x in pix_fmt for x in ['yuv420p', 'yuvj420p', 'yuv444p', 'yuvj444p']):
            bits = '8'
    
    if not bits:
        # Check in profile for bit depth
        profile = video_stream.get('profile', '').lower()
        if '10 bit' in profile or 'high10' in profile:
            bits = '10'
        elif '12 bit' in profile or 'high12' in profile:
            bits = '12'
        elif '8 bit' in profile or 'high' in profile:
            bits = '8'
    
    return bits or 'unknown'

def prepare_reduced_raw_output(format_info, video_stream, audio_streams, subtitle_streams):
    """
    Prepare a reduced version of the raw ffprobe output.

    Args:
    format_info (dict): Format information from ffprobe.
    video_stream (dict): Video stream data from ffprobe.
    audio_streams (list): List of audio stream data from ffprobe.
    subtitle_streams (list): List of subtitle stream data from ffprobe.

    Returns:
    dict: A reduced version of the ffprobe output.
    """
    reduced_raw_output = {
        'format': {
            'filename': format_info.get('filename'),
            'format_name': format_info.get('format_name'),
            'duration': format_info.get('duration'),
            'bit_rate': format_info.get('bit_rate'),
            'tags': remove_statistics_tags(format_info.get('tags', {}))
        },
        'streams': []
    }

    if video_stream:
        reduced_raw_output['streams'].append({
            'index': video_stream.get('index'),
            'codec_type': 'video',
            'codec_name': video_stream.get('codec_name'),
            'width': video_stream.get('width'),
            'height': video_stream.get('height'),
            'avg_frame_rate': video_stream.get('avg_frame_rate'),
            'bit_rate': video_stream.get('bit_rate'),
            'profile': video_stream.get('profile'),
            'level': video_stream.get('level'),
            'color_space': video_stream.get('color_space'),
            'color_transfer': video_stream.get('color_transfer'),
            'bits_per_raw_sample': video_stream.get('bits_per_raw_sample'),
            'tags': remove_statistics_tags(video_stream.get('tags', {}))
        })

    for audio_stream in audio_streams:
        reduced_raw_output['streams'].append({
            'index': audio_stream.get('index'),
            'codec_type': 'audio',
            'codec_name': audio_stream.get('codec_name'),
            'channels': audio_stream.get('channels'),
            'channel_layout': audio_stream.get('channel_layout'),
            'sample_rate': audio_stream.get('sample_rate'),
            'bit_rate': audio_stream.get('bit_rate'),
            'tags': remove_statistics_tags(audio_stream.get('tags', {})),
            'disposition': audio_stream.get('disposition', {})
        })

    for subtitle_stream in subtitle_streams:
        reduced_raw_output['streams'].append({
            'index': subtitle_stream.get('index'),
            'codec_type': 'subtitle',
            'codec_name': subtitle_stream.get('codec_name'),
            'tags': remove_statistics_tags(subtitle_stream.get('tags', {}))
        })

    return reduced_raw_output