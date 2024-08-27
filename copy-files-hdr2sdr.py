import os
import shutil

def process_file(file_path):
    # Get the directory and filename
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    # Check if there's a "to_be_deleted" file in the same directory
    if any("to_be_deleted" in f for f in os.listdir(directory)):
        print(f"'to_be_deleted' has been detected, ignoring: {file_path}")
    else:
        # Copy file to the target directory
        target_dir = "/Volumes/media/to_be_processed_by_tdarr/hdr_to_sdr_copies"
        target_path = os.path.join(target_dir, filename)
        
        try:
            shutil.copy2(file_path, target_path)
            print(f"File needs processing, copying to hdr_to_sdr: {file_path}")
        except shutil.SameFileError:
            print(f"File already exists in target directory: {file_path}")
        except Exception as e:
            print(f"Error copying {file_path}: {str(e)}")

def main():
    input_file = "/Users/chris/Projects/video-analysis/hdr-video-files_all.txt"

    # Read the input file
    with open(input_file, 'r') as f:
        file_list = f.read().splitlines()

    # Process each file
    for file_path in file_list:
        process_file(file_path)

if __name__ == "__main__":
    main()