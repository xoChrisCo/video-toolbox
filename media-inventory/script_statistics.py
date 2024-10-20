import time
from collections import Counter
from utils import safe_float, safe_decimal, format_number, format_large_number
from config import RESOLUTION_CATEGORIES, MAX_AUDIO_STREAMS
from decimal import Decimal, ROUND_HALF_UP

def generate_statistics(root_folder, start_time, processed_files, failed_files, metadata_list):
    """
    Generate statistics from the processed video files.

    Args:
    root_folder (str): The root folder that was scanned.
    start_time (float): The start time of the script execution.
    processed_files (list): List of successfully processed files.
    failed_files (list): List of files that failed to process.
    metadata_list (list): List of metadata dictionaries for all processed files.

    Returns:
    dict: A dictionary containing various statistics about the processed files.
    """
    end_time = time.time()
    execution_time = end_time - start_time
    total_file_size = sum(safe_float(m['Filesize (in GB)']) for m in metadata_list)
    
    stats = {
        "script": {
            "folder_scanned": root_folder,
            "execution_time": execution_time,
            "files_processed": len(processed_files),
            "files_failed": len(failed_files),
            "failed_files_list": failed_files[:10],  # Store up to 10 failed files
            "total_file_size": total_file_size,
        },
        "file": {
            "formats": Counter(),
            "largest_file": None,
            "smallest_file": None,
            "longest_playtime": None,
            "shortest_playtime": None,
            "all_files": metadata_list,
        },
        "video": {
            "codecs": Counter(),
            "bits": Counter(),
            "color_spaces": Counter(),
            "hdr_count": 0,
            "sdr_count": 0,
            "highest_bitrate": None,
            "lowest_bitrate": None,
            "average_bitrate": 0,
            "resolutions": Counter(),
            "resolution_categories": Counter(),
        },
        'audio': {
            'soundtrack_counts': Counter(),
            'language_counts': Counter(),
            'commentary_tracks': 0,
            'languages': Counter(),
            'single_language_files': Counter(),
            'channel_formats': Counter(),
            'channel_layouts': Counter(),
            'audio_formats': Counter(),
        },
        "subtitles": {
            "in_file": {
                "total_count": 0,
                "languages": Counter(),
                "formats": Counter(),
            },
            "in_folder": {
                "languages": Counter(),
            },
            "combined": {
                "languages": Counter(),
            },
            "missing_subtitles": 0,
            "missing_eng_subtitles": 0,
            "missing_nor_subtitles": 0,
            "forced_subtitles": 0,
        },
        "errors": [],
    }

    for m in metadata_list:
        try:
            # File statistics
            stats['file']['formats'][m['Container Format']] += 1
            
            # Video statistics
            stats['video']['codecs'][m['Video Codec']] += 1
            stats['video']['bits'][m['Bits']] += 1
            stats['video']['color_spaces'][m['Color Space']] += 1
            stats['video']['hdr_count'] += 1 if m['HDR'] == 'Yes' else 0
            stats['video']['sdr_count'] += 1 if m['HDR'] == 'No' else 0
            
            width, height = int(safe_float(m['Width'])), int(safe_float(m['Height']))
            stats['video']['resolutions'][f"{width}x{height}"] += 1
            
            # Resolution categories
            for category, (min_width, min_height) in RESOLUTION_CATEGORIES.items():
                if width >= min_width and height >= min_height:
                    stats['video']['resolution_categories'][category] += 1
                    break
            
            # Audio statistics
            soundtrack_count = int(m['Audio Stream Count'])
            languages = set(lang.strip() for lang in m['Audio Languages'].split(','))
            language_count = len(languages)
            
            stats['audio']['soundtrack_counts'][min(soundtrack_count, MAX_AUDIO_STREAMS)] += 1
            stats['audio']['language_counts'][min(language_count, MAX_AUDIO_STREAMS)] += 1
            
            if 'commentary' in m['Audio Languages'].lower():
                stats['audio']['commentary_tracks'] += 1
            
            stats['audio']['languages'].update(languages)
            
            if language_count == 1:
                stats['audio']['single_language_files'][list(languages)[0]] += 1
            
            stats['audio']['channel_formats'].update(set(ch.strip() for ch in m['Audio Channels'].split(',')))
            stats['audio']['channel_layouts'].update(set(layout.strip() for layout in m['Audio Channel Layouts'].split(',')))
            stats['audio']['audio_formats'].update(set(codec.strip() for codec in m['Audio Codecs'].split(',')))
            
            # Subtitle statistics
            stats['subtitles']['in_file']['total_count'] += int(m['Subtitle stream count in file'])
            stats['subtitles']['in_file']['languages'].update(lang.strip() for lang in m['Subtitle languages in file'].split(',') if lang.strip())
            stats['subtitles']['in_file']['formats'].update(format.strip() for format in m['Subtitle formats in file'].split(',') if format.strip())
            stats['subtitles']['in_folder']['languages'].update(lang.strip() for lang in m.get('Subtitles in file and folder', '').split(',') if lang.strip())
            stats['subtitles']['combined']['languages'].update(lang.strip() for lang in (m['Subtitle languages in file'] + ',' + m.get('Subtitles in file and folder', '')).split(',') if lang.strip())
            
            if m['Subtitle stream count in file'] == '0' and not m.get('Subtitles in file and folder'):
                stats['subtitles']['missing_subtitles'] += 1
            
            if 'eng' not in m['Subtitle languages in file'] and 'en' not in m['Subtitle languages in file'] and 'eng' not in m.get('Subtitles in file and folder', '') and 'en' not in m.get('Subtitles in file and folder', ''):
                stats['subtitles']['missing_eng_subtitles'] += 1
            
            if 'nor' not in m['Subtitle languages in file'] and 'no' not in m['Subtitle languages in file'] and 'nor' not in m.get('Subtitles in file and folder', '') and 'no' not in m.get('Subtitles in file and folder', ''):
                stats['subtitles']['missing_nor_subtitles'] += 1
            
            if 'forced' in m['Subtitle languages in file'].lower() or 'forced' in m.get('Subtitles in file and folder', '').lower():
                stats['subtitles']['forced_subtitles'] += 1

        except Exception as e:
            stats['errors'].append(f"Error processing file {m.get('File', 'Unknown')}: {str(e)}")

    try:
        stats['script']['total_frames'] = sum(int(safe_float(m['Duration']) * safe_float(m['Frame Rate'])) for m in metadata_list if m['Duration'] != 'unknown' and m['Frame Rate'] != 'unknown')
    except Exception as e:
        stats['errors'].append(f"Error calculating total frames: {str(e)}")
        stats['script']['total_frames'] = "Error"

    try:
        total_pixels = sum(safe_decimal(m['Duration']) * safe_decimal(m['Frame Rate']) * safe_decimal(m['Width']) * safe_decimal(m['Height']) 
                           for m in metadata_list 
                           if all(m[key] != 'unknown' for key in ['Duration', 'Frame Rate', 'Width', 'Height']))
        stats['script']['total_pixels'] = total_pixels.to_integral_value(rounding=ROUND_HALF_UP)
    except Exception as e:
        stats['errors'].append(f"Error calculating total pixels: {str(e)}")
        stats['script']['total_pixels'] = "Error"

    try:
        stats['script']['total_runtime'] = sum(safe_float(m['Duration']) for m in metadata_list)
        stats['script']['average_runtime'] = stats['script']['total_runtime'] / len(metadata_list) if metadata_list else 0
    except Exception as e:
        stats['errors'].append(f"Error calculating runtime statistics: {str(e)}")
        stats['script']['total_runtime'] = "Error"
        stats['script']['average_runtime'] = "Error"

    try:
        stats['script']['files_per_second'] = len(processed_files) / execution_time if execution_time > 0 else 0
        stats['script']['seconds_per_file'] = execution_time / len(processed_files) if processed_files else 0
        stats['script']['gigabytes_per_second'] = total_file_size / execution_time if execution_time > 0 else 0
    except Exception as e:
        stats['errors'].append(f"Error calculating processing speed statistics: {str(e)}")

    try:
        stats['file']['largest_file'] = max((m for m in metadata_list if m['Filesize (in GB)'] != 'unknown'), key=lambda x: safe_float(x['Filesize (in GB)']))
        stats['file']['smallest_file'] = min((m for m in metadata_list if m['Filesize (in GB)'] != 'unknown'), key=lambda x: safe_float(x['Filesize (in GB)']))
        stats['file']['longest_playtime'] = max((m for m in metadata_list if m['Duration'] != 'unknown'), key=lambda x: safe_float(x['Duration']))
        stats['file']['shortest_playtime'] = min((m for m in metadata_list if m['Duration'] != 'unknown'), key=lambda x: safe_float(x['Duration']))
    except ValueError as e:
        stats['errors'].append(f"Error calculating file size and playtime statistics: {str(e)}")
        stats['file']['largest_file'] = stats['file']['smallest_file'] = stats['file']['longest_playtime'] = stats['file']['shortest_playtime'] = None

    try:
        valid_bitrate_files = [m for m in metadata_list if m['Video bitrate (in mbps)'] != 'unknown']
        if valid_bitrate_files:
            stats['video']['highest_bitrate'] = max(valid_bitrate_files, key=lambda x: safe_float(x['Video bitrate (in mbps)']))
            stats['video']['lowest_bitrate'] = min(valid_bitrate_files, key=lambda x: safe_float(x['Video bitrate (in mbps)']))
            stats['video']['average_bitrate'] = sum(safe_float(m['Video bitrate (in mbps)']) for m in valid_bitrate_files) / len(valid_bitrate_files)
        else:
            stats['video']['highest_bitrate'] = stats['video']['lowest_bitrate'] = stats['video']['average_bitrate'] = None
    except Exception as e:
        stats['errors'].append(f"Error calculating video bitrate statistics: {str(e)}")
        stats['video']['highest_bitrate'] = stats['video']['lowest_bitrate'] = stats['video']['average_bitrate'] = None

    return stats

def process_audio_streams(stats, metadata_list):
    """
    Process audio streams to detect Atmos tracks.

    Args:
    stats (dict): The statistics dictionary to update.
    metadata_list (list): List of metadata dictionaries for all processed files.

    Returns:
    None
    """
    atmos_count = 0
    for metadata in metadata_list:
        raw_output = metadata.get('Raw ffprobe output', '{}')
        try:
            data = eval(raw_output)  # Be cautious with eval, ensure raw_output is safe
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    if detect_atmos(stream):
                        atmos_count += 1
                        break  # Count only one Atmos track per file
        except Exception as e:
            stats['errors'].append(f"Error processing audio streams for file {metadata.get('File', 'Unknown')}: {str(e)}")
    
    stats['audio']['atmos_count'] = atmos_count

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