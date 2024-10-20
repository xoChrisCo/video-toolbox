from colorama import Fore, Style # type: ignore
from utils import format_time, format_number, format_large_number, safe_get_stat, combine_language_counts
from decimal import Decimal
from config import TOP_BOTTOM_COUNT


def print_and_write_statistics(stats, output_file):
    """
    Print statistics to the console and write them to a file.

    Args:
    stats (dict): The statistics dictionary to output.
    output_file (str): The path to the file where statistics will be written.

    Returns:
    None
    """
    with open(output_file, 'w') as f:
        def print_and_write(message, file_obj):
            print(message)
            file_obj.write(message + '\n')

        def print_stat(label, value=None, unit="", indent=0, is_header=False, file_only=False, file_obj=None):
            label_width = 45
            total_indent = indent * 2  # 2 spaces per indent level
            if is_header:
                message = f"{'  ' * indent}{Fore.YELLOW}{label}{Style.RESET_ALL}"
            elif value is not None:
                if isinstance(value, (int, float, Decimal)):
                    value_str = format_large_number(value)
                elif value == "Error":
                    value_str = f"{Fore.RED}Error{Style.RESET_ALL}"
                else:
                    value_str = str(value)
                formatted_label = f"{'  ' * indent}{label:<{label_width - total_indent}}"
                formatted_value = f"{Fore.LIGHTWHITE_EX}{value_str} {unit}{Style.RESET_ALL}"
                message = f"{formatted_label}{formatted_value}"
            else:
                message = f"{'  ' * indent}{label}"
            
            if file_obj:
                file_obj.write(message.replace(Fore.YELLOW, '').replace(Fore.LIGHTWHITE_EX, '').replace(Fore.RED, '').replace(Style.RESET_ALL, '') + '\n')
            if not file_only:
                print(message)

        # Main statistics printing
        print_and_write("\n" + "="*50, f)
        print_and_write(f"{Fore.CYAN}Media Inventory Statistics{Style.RESET_ALL}", f)
        print_and_write("="*50 + "\n", f)

        print_script_statistics(stats, lambda *args, **kwargs: print_stat(*args, **kwargs, file_obj=f))
        print_file_statistics(stats, lambda *args, **kwargs: print_stat(*args, **kwargs, file_obj=f))
        print_video_statistics(stats, lambda *args, **kwargs: print_stat(*args, **kwargs, file_obj=f))
        print_audio_statistics(stats, lambda *args, **kwargs: print_stat(*args, **kwargs, file_obj=f))
        print_subtitle_statistics(stats, lambda *args, **kwargs: print_stat(*args, **kwargs, file_obj=f))
        print_errors(stats, lambda message: print_and_write(message, f))

def print_script_statistics(stats, print_stat):
    print_stat(f"{Fore.CYAN}Script Statistics:{Style.RESET_ALL}", is_header=True)
    print_stat("Folder scanned:", safe_get_stat(stats, 'script', 'folder_scanned'))
    print_stat("Time to execute script:", format_time(safe_get_stat(stats, 'script', 'execution_time')))
    print_stat("Files processed:", format_number(safe_get_stat(stats, 'script', 'files_processed')))
    print_stat("Files failed:", format_number(safe_get_stat(stats, 'script', 'files_failed')))
    
    files_processed = safe_get_stat(stats, 'script', 'files_processed', default=0)
    execution_time = safe_get_stat(stats, 'script', 'execution_time', default=0)

    if safe_get_stat(stats, 'script', 'files_failed', default=0) > 0:
        print_stat("Failed files (up to 10):", is_header=True)
        for file_path, error_message in safe_get_stat(stats, 'script', 'failed_files_list', default=[]):
            print_stat(f"{file_path}", f"{error_message}", indent=2)
        
        if safe_get_stat(stats, 'script', 'files_failed', default=0) > 10:
            print_stat(f"... and {safe_get_stat(stats, 'script', 'files_failed', default=0) - 10} more", indent=2)

    total_file_size = safe_get_stat(stats, 'script', 'total_file_size', default=0)
    if total_file_size >= 1024:
        print_stat("Total file size processed:", f"{total_file_size / 1024:.2f}", "TB")
    else:
        print_stat("Total file size processed:", f"{total_file_size:.2f}", "GB")

    total_frames = safe_get_stat(stats, 'script', 'total_frames')
    print_stat("Total amount of frames:", f"{format_number(total_frames)} ({format_large_number(total_frames)})")

    total_pixels = safe_get_stat(stats, 'script', 'total_pixels')
    print_stat("Total number of pixels:", f"{format_number(total_pixels)} ({format_large_number(total_pixels)})")

    total_runtime = safe_get_stat(stats, 'script', 'total_runtime')
    print_stat("Total runtime:", format_time(total_runtime))

    average_runtime = safe_get_stat(stats, 'script', 'average_runtime')
    print_stat("Average runtime:", format_time(average_runtime))

    if files_processed > 0 and execution_time > 0:
        print_stat("Files / second:", f"{files_processed / execution_time:.2f}")
        print_stat("Seconds / file:", f"{execution_time / files_processed:.2f}")
    else:
        print_stat("Files / second:", "N/A")
        print_stat("Seconds / file:", "N/A")

    total_file_size = safe_get_stat(stats, 'script', 'total_file_size', default=0)
    if total_file_size > 0 and execution_time > 0:
        print_stat("Gigabytes / second:", f"{total_file_size / execution_time:.2f}")
    else:
        print_stat("Gigabytes / second:", "N/A")

    print_stat("")

def print_file_statistics(stats, print_stat):
    print_stat(f"\n{Fore.CYAN}File Statistics:{Style.RESET_ALL}", is_header=True)
    print_stat("File formats:", is_header=True, indent=0)
    for format, count in sorted(stats['file']['formats'].items(), key=lambda x: x[1], reverse=True):
        print_stat(format, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)
    
    print_top_bottom("Largest/Smallest files:", 
                 [f for f in stats['file']['all_files'] if isinstance(f.get('Filesize (in GB)'), (int, float))],
                 lambda x: x['Filesize (in GB)'], print_stat, value_format="{:.2f}", unit="GB")
    invalid_filesize_count = sum(1 for f in stats['file']['all_files'] if not isinstance(f.get('Filesize (in GB)'), (int, float)))
    if invalid_filesize_count > 0:
        print_stat(f"Files with invalid file size:", invalid_filesize_count)

    print_top_bottom("Longest/Shortest playtimes:", 
                 [f for f in stats['file']['all_files'] if f['Duration'] != 'unknown'],
                 lambda x: float(x['Duration']), print_stat, time_format=True)
    unknown_duration_count = sum(1 for f in stats['file']['all_files'] if f['Duration'] == 'unknown')
    if unknown_duration_count > 0:
        print_stat(f"Files with unknown duration:", unknown_duration_count)

def print_video_statistics(stats, print_stat):
    print_stat(f"\n{Fore.CYAN}Video Statistics:{Style.RESET_ALL}", is_header=True)
    print_stat("Codecs:", is_header=True)
    for codec, count in sorted(stats['video']['codecs'].items(), key=lambda x: x[1], reverse=True):
        print_stat(codec, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)
    print_stat("Bits:", is_header=True)
    for bits, count in sorted(stats['video']['bits'].items(), key=lambda x: x[1], reverse=True):
        print_stat(bits, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)
    print_stat("Color spaces:", is_header=True)
    for space, count in sorted(stats['video']['color_spaces'].items(), key=lambda x: x[1], reverse=True):
        print_stat(space, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)
    print_stat("HDR files:", f"{format_number(stats['video']['hdr_count'])} ({stats['video']['hdr_count']/stats['script']['files_processed']*100:.2f}%)")
    print_stat("SDR files:", f"{format_number(stats['video']['sdr_count'])} ({stats['video']['sdr_count']/stats['script']['files_processed']*100:.2f}%)")
    
    print_top_bottom("Top/bottom bitrates:", stats['file']['all_files'], lambda x: float(x['Video bitrate (in mbps)']), print_stat, unit="Mbps")

    print_stat("Average bitrate:", f"{stats['video']['average_bitrate']:.2f}", "Mbps")
    print_resolution_categories(stats, print_stat)
    print_resolutions(stats, print_stat)

def print_audio_statistics(stats, print_stat):
    print_stat(f"\n{Fore.CYAN}Audio Statistics:{Style.RESET_ALL}", is_header=True)
    print_stat("Soundtrack counts:", is_header=True)
    for count in range(5):
        key = count if count < 4 else 'more'
        value = stats['audio']['soundtrack_counts'][key]
        print_stat(f"Files with {key} soundtrack{'s' if key != 1 else ''}:", f"{format_number(value)} ({value/stats['script']['files_processed']*100:.2f}%)", indent=2)
    print_stat("Audio language counts:", is_header=True)
    for count in range(5):
        key = count if count < 4 else 'more'
        value = stats['audio']['language_counts'][key]
        print_stat(f"Files with {key} audio language{'s' if key != 1 else ''}:", f"{format_number(value)} ({value/stats['script']['files_processed']*100:.2f}%)", indent=2)
    
    print_stat("Files with Atmos audio:", f"{format_number(stats['audio']['atmos_count'])} ({stats['audio']['atmos_count']/stats['script']['files_processed']*100:.2f}%)")
    print_stat("Files with commentary track:", f"{format_number(stats['audio']['commentary_tracks'])} ({stats['audio']['commentary_tracks']/stats['script']['files_processed']*100:.2f}%)", indent=1)
    print_stat("Audio languages:", is_header=True)
    for lang, count in sorted(stats['audio']['languages'].items(), key=lambda x: x[1], reverse=True):
        print_stat(lang, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)

    print_stat("Channel formats:", is_header=True)
    for format, count in sorted(stats['audio']['channel_formats'].items(), key=lambda x: x[1], reverse=True):
        print_stat(format, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)

    print_stat("Channel layouts:", is_header=True)
    for layout, count in sorted(stats['audio']['channel_layouts'].items(), key=lambda x: x[1], reverse=True):
        print_stat(layout, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)

    print_stat("Audio formats:", is_header=True)
    for format, count in sorted(stats['audio']['audio_formats'].items(), key=lambda x: x[1], reverse=True):
        print_stat(format, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)

def print_subtitle_statistics(stats, print_stat):
    print_stat(f"\n{Fore.CYAN}Subtitle Statistics:{Style.RESET_ALL}", is_header=True)

    print_subtitle_stats(stats, 'in_file', print_stat)
    print_subtitle_stats(stats, 'in_folder', print_stat)
    print_subtitle_stats(stats, 'combined', print_stat)

    print_stat("Files missing subtitles (file+folder):", f"{format_number(stats['subtitles']['missing_subtitles'])} ({stats['subtitles']['missing_subtitles']/stats['script']['files_processed']*100:.2f}%)")
    print_stat("Files missing eng subtitles (file+folder):", f"{format_number(stats['subtitles']['missing_eng_subtitles'])} ({stats['subtitles']['missing_eng_subtitles']/stats['script']['files_processed']*100:.2f}%)")
    print_stat("Files missing nor subtitles (file+folder):", f"{format_number(stats['subtitles']['missing_nor_subtitles'])} ({stats['subtitles']['missing_nor_subtitles']/stats['script']['files_processed']*100:.2f}%)")
    print_stat("Files with forced subtitles (file/folder):", f"{format_number(stats['subtitles']['forced_subtitles'])} ({stats['subtitles']['forced_subtitles']/stats['script']['files_processed']*100:.2f}%)")

def print_errors(stats, print_and_write):
    if stats['errors']:
        print_and_write(f"\n{Fore.RED}Errors encountered during statistics generation:{Style.RESET_ALL}")
        for error in stats['errors']:
            print_and_write(f"  {error}")

    print_and_write("")

def print_resolution_categories(stats, print_stat):
    print_stat("Resolution categories:", is_header=True)
    # Define the order we want
    order = ['8K', '4K', '1080p', '720p', '480p', 'SD']
    # Sort the items based on this order
    sorted_items = sorted(stats['video']['resolution_categories'].items(), 
                        key=lambda x: order.index(x[0]) if x[0] in order else len(order))
    for category, count in sorted_items:
        print_stat(category, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)

def print_resolutions(stats, print_stat):
    print_stat("Specific resolutions:", is_header=True)
    sorted_resolutions = sorted(stats['video']['resolutions'].items(), key=lambda x: x[1], reverse=True)
    for i, (resolution, count) in enumerate(sorted_resolutions):
        if i < 5:
            print_stat(resolution, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2)
        else:
            print_stat("(Full list in statistics file)", indent=2)
            break
    for resolution, count in sorted_resolutions:
        print_stat(resolution, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=2, file_only=True)

def print_top_bottom(title, items, key, print_stat, reverse=True, value_format="{}", unit="", time_format=False):
    print_stat(title, is_header=True)
    sorted_items = sorted(items, key=key, reverse=reverse)
    
    if time_format:
        max_value_length = max(len(format_time(key(item))) for item in sorted_items[:TOP_BOTTOM_COUNT] + sorted_items[-TOP_BOTTOM_COUNT:])
    else:
        max_value_length = max(len(value_format.format(key(item))) for item in sorted_items[:TOP_BOTTOM_COUNT] + sorted_items[-TOP_BOTTOM_COUNT:])
    
    for i, item in enumerate(sorted_items[:TOP_BOTTOM_COUNT]):
        value = key(item)
        if time_format:
            formatted_value = format_time(value)
        else:
            formatted_value = value_format.format(value)
        print_stat(f"{formatted_value.rjust(max_value_length)} {unit}", f"{item['File']}", indent=2)
    
    print_stat("...", indent=2)
    
    for i, item in enumerate(sorted_items[-TOP_BOTTOM_COUNT:]):
        value = key(item)
        if time_format:
            formatted_value = format_time(value)
        else:
            formatted_value = value_format.format(value)
        print_stat(f"{formatted_value.rjust(max_value_length)} {unit}", f"{item['File']}", indent=2)
    
    print_stat("(Longer list in statistics file)", indent=2)
    
    for i, item in enumerate(sorted_items[:TOP_BOTTOM_COUNT] + sorted_items[-TOP_BOTTOM_COUNT:]):
        value = key(item)
        if time_format:
            formatted_value = format_time(value)
        else:
            formatted_value = value_format.format(value)
        print_stat(f"{formatted_value.rjust(max_value_length)} {unit}", f"{item['File']}", indent=2, file_only=True)


def print_subtitle_stats(stats, category, print_stat):
    print_stat(f"Subtitles {category}:", is_header=True)
    
    if category == 'in_file':
        print_stat("Total subtitles found:", format_number(stats['subtitles']['in_file']['total_count']), indent=2)
    
    print_stat("Languages:", is_header=True, indent=2)
    combined_langs = combine_language_counts(stats['subtitles'][category]['languages'])
    sorted_langs = sorted(combined_langs.items(), key=lambda x: x[1], reverse=True)
    
    for i, (lang, count) in enumerate(sorted_langs):
        if i < TOP_BOTTOM_COUNT:
            print_stat(lang, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=3)
        else:
            print_stat("(Full list in statistics file)", indent=3)
            break
    
    # Write full list to file
    for lang, count in sorted_langs:
        print_stat(lang, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=3, file_only=True)
    
    if category == 'in_file':
        print_stat("Formats:", is_header=True, indent=2)
        for format, count in sorted(stats['subtitles']['in_file']['formats'].items(), key=lambda x: x[1], reverse=True):
            if format:
                print_stat(format, f"{format_number(count)} ({count/stats['script']['files_processed']*100:.2f}%)", indent=3)
