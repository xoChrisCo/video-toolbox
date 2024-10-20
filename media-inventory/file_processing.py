import json
import os
import csv
from colorama import Fore, Style # type: ignore
from video_analysis import get_video_metadata
from utils import print_progress, count_files
from config import VIDEO_EXTENSIONS, CSV_FIELDNAMES, CSV_DELIMITER

def process_videos(root_folder, output_folder, output_file, verbosity, delimiter, full_ffprobe_output, pretty_json):
    """
    Process video files in the given folder and its subfolders, extracting metadata and writing to a CSV file.
    
    Args:
    root_folder (str): The path to the root folder to search.
    output_folder (str): The folder where output files will be saved.
    output_file (str): The name of the output CSV file.
    verbosity (int): The level of output detail (0, 1, or 2).
    full_ffprobe_output (bool): Whether to include full ffprobe output in the Raw ffprobe output column.
    pretty_json (bool): Whether to format JSON output for readability.

    Returns:
    tuple: A tuple containing lists of processed files, failed files, and all metadata.
    """
    total_files = count_files(root_folder, verbosity)
    processed_files = []
    failed_files = []
    metadata_list = []

    print(f"{Fore.CYAN}Found {total_files} video files to process.{Style.RESET_ALL}")

    os.makedirs(output_folder, exist_ok=True)
    csv_path = os.path.join(output_folder, output_file)

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES, delimiter=CSV_DELIMITER, 
                                quoting=csv.QUOTE_MINIMAL, quotechar='"', escapechar='\\')
        writer.writeheader()

        for root, _, files in os.walk(root_folder):
            for file in files:
                if file.lower().endswith(VIDEO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    
                    if verbosity == 1:
                        progress = f"{len(processed_files) + len(failed_files) + 1}/{total_files} ({(len(processed_files) + len(failed_files) + 1)/total_files*100:.2f}%) - {file}"
                        print_progress(progress)
                    elif verbosity >= 2:
                        print(f"\n{Fore.GREEN}Processing {len(processed_files) + len(failed_files) + 1}/{total_files}: {file}{Style.RESET_ALL}")
                    
                    try:
                        metadata = get_video_metadata(file_path, full_ffprobe_output, pretty_json)
                        
                        if metadata:
                            # Handle 'Raw ffprobe output' separately
                            raw_output = metadata.pop('Raw ffprobe output', '')
                            # Convert metadata to a list of values, maintaining the order of fieldnames
                            row_values = [metadata.get(field, '') for field in CSV_FIELDNAMES[:-1]]  # Exclude 'Raw ffprobe output' from fieldnames
                            # Manually write the row as a string, including the raw ffprobe output
                            row_string = CSV_DELIMITER.join(str(value) for value in row_values)
                            row_string += CSV_DELIMITER + json.dumps(raw_output, indent=2 if pretty_json else None)
                            csvfile.write(row_string + '\n')
                            
                            metadata_list.append(metadata)
                            processed_files.append(file_path)
                            
                            if verbosity >= 2:
                                print(f"{Fore.YELLOW}Metadata: {metadata}{Style.RESET_ALL}")
                                
                    except Exception as e:
                        error_message = f"Error processing {file_path}: {str(e)}"
                        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
                        failed_files.append((file_path, error_message))
                    
                    if verbosity >= 2:
                        print(f"{Fore.GREEN}Progress: {len(processed_files) + len(failed_files)}/{total_files} ({(len(processed_files) + len(failed_files))/total_files*100:.2f}%){Style.RESET_ALL}")

    if verbosity >= 1:
        print()  # Move to the next line after processing

    return processed_files, failed_files, metadata_list