import subprocess
import time
import os
import random

def run_ffprobe(file_path, debug_level):
    start_time = time.time()
    
    ffprobe_command = ['ffprobe']
    if debug_level >= 2:
        ffprobe_command.extend(['-v', 'debug'])
    elif debug_level == 1:
        ffprobe_command.extend(['-v', 'warning'])
    else:
        ffprobe_command.extend(['-v', 'error'])
    
    ffprobe_command.extend(['-print_format', 'json', '-show_format', '-show_streams', file_path])
    
    print(f"Running command: {' '.join(ffprobe_command)}")
    
    try:
        result = subprocess.run(ffprobe_command, capture_output=True, text=True, check=True)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"FFprobe execution time: {execution_time:.2f} seconds")
        print(f"FFprobe output size: {len(result.stdout)} bytes")
        return execution_time, len(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"FFprobe command failed: {e}")
        print(f"FFprobe stderr: {e.stderr}")
        return None, None

def get_file_size(file_path):
    return os.path.getsize(file_path)

if __name__ == "__main__":
    file_path = "/Volumes/media/media/movies/Pulp Fiction (1994)/Pulp Fiction (1994) Remux-2160p.mkv"
    debug_levels = [0, 1, 2]
    runs_per_level = 3
    
    file_size = get_file_size(file_path)
    print(f"File size: {file_size / (1024*1024*1024):.2f} GB")
    
    results = {level: [] for level in debug_levels}
    
    # Run each debug level multiple times in random order
    for _ in range(runs_per_level):
        random.shuffle(debug_levels)
        for level in debug_levels:
            print(f"\nRunning FFprobe with debug level {level}")
            execution_time, output_size = run_ffprobe(file_path, level)
            if execution_time is not None:
                results[level].append(execution_time)
                print(f"FFprobe completed successfully at debug level {level}")
            else:
                print(f"FFprobe failed at debug level {level}")
    
    # Print average execution times
    print("\nAverage execution times:")
    for level in debug_levels:
        avg_time = sum(results[level]) / len(results[level])
        print(f"Debug level {level}: {avg_time:.2f} seconds")