import subprocess
import os
from datetime import datetime
from colorama import init, Fore, Style # type: ignore
import sys
import re

# Initialize colorama
init(autoreset=True)

# Set default encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Set the working folder
WORKING_FOLDER = 'C:\\Users\\rdp\\Desktop\\hdr2sdr\\'

# Paths to your files and executable
file_list_path = os.path.join(WORKING_FOLDER, 'hdr-video-files.txt')
preset_file_path = os.path.join(WORKING_FOLDER, '4k-mkv-HDR-to-SDR.json')
handbrake_cli_path = os.path.join(WORKING_FOLDER, 'HandBrakeCLI.exe')

# Create logs folder
logs_folder = os.path.join(WORKING_FOLDER, 'logs')
os.makedirs(logs_folder, exist_ok=True)

# Create a timestamp for log files
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
command_log_file = os.path.join(logs_folder, f'{timestamp}_commands.log')

# Read the list of files
try:
    with open(file_list_path, 'r', encoding='utf-8') as file:
        files = [line.strip() for line in file.readlines() if not line.strip().startswith('#')]
except Exception as e:
    print(f"Failed to read file list: {e}")
    exit(1)

def create_log_file(input_file):
    filename = os.path.basename(input_file)
    log_filename = f'{timestamp}_{filename}_handbrake.log'
    return os.path.join(logs_folder, log_filename)

# Function to transcode a single file
def transcode_file(input_file, idx, total_files):
    output_file = input_file.rsplit('.', 1)[0] + ' SDR Handbrake.mkv'
    temp_file = input_file.rsplit('.', 1)[0] + ' SDR Handbrake.temp.mkv'
    log_file = create_log_file(input_file)

    if os.path.exists(output_file):
        print(f"{Fore.GREEN}Processing file {idx + 1}/{total_files}: {input_file} - Skipped (already exists)")
        return

    if os.path.exists(temp_file):
        os.remove(temp_file)

    command = [
        handbrake_cli_path,
        '--preset-import-file', preset_file_path,
        '--preset', '4k hdr to sdr win',
        '-i', input_file,
        '-o', temp_file
    ]

    print(f"Starting to process file {idx + 1}/{total_files}: {input_file}")
    print(f"Running command: {' '.join(command)}")
    
    with open(command_log_file, 'a', encoding='utf-8') as cmd_log:
        cmd_log.write(f"{' '.join(command)}\n")

    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"Starting transcoding: {input_file}\n")
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True, encoding='utf-8', errors='replace')

            progress_pattern = re.compile(r'Encoding: task (\d+) of (\d+), (\d+\.\d+) % \((\d+\.\d+) fps, avg (\d+\.\d+) fps, ETA (\w+)\)')
            last_percentage = 0
            current_pass = 1

            for line in iter(process.stdout.readline, ''):
                match = progress_pattern.search(line)
                if match:
                    task, total_tasks, percentage, fps, avg_fps, eta = match.groups()
                    percentage = float(percentage)
                    
                    # Update pass information
                    if int(task) > current_pass:
                        current_pass = int(task)
                        last_percentage = 0
                    
                    # Only print if the percentage has changed by at least 0.5%
                    if percentage - last_percentage >= 0.5:
                        print(f"\rFile {idx + 1}/{total_files}: {os.path.basename(input_file)} - Pass {task}/{total_tasks} - {percentage:.2f}% (FPS: {fps}, Avg FPS: {avg_fps}, ETA: {eta})", end='', flush=True)
                        last_percentage = percentage
                
                log.write(line)
                log.flush()

            print()  # New line after progress is complete
            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                if os.path.exists(temp_file):
                    os.rename(temp_file, output_file)
                    os.rename(input_file, input_file + '.to_be_deleted')
                    print(f"{Fore.GREEN}Processing file {idx + 1}/{total_files}: {input_file} Completed")
                    log.write(f"Transcoding completed: {output_file}\n")
            else:
                print(f"{Fore.RED}Processing file {idx + 1}/{total_files}: {input_file} - Failed")
                log.write(f"Failed to transcode: {input_file}\n")
        except Exception as e:
            print(f"Error running command: {e}")
            log.write(f"Error running command for {input_file}: {e}\n")

total_files = len(files)
print(f"Total files to process: {total_files}")
for idx, input_file in enumerate(files):
    transcode_file(input_file, idx, total_files)

print("All files have been processed.")