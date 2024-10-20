import os
import random
import subprocess
import shlex
import json

from video_info import get_video_bitrate, get_video_duration, get_file_size
from utils import clear_line, print_progress, debug_print, count_directories
from constants import (
    Colors,
    FFMPEG_SCREENSHOT_CMD,
    FFMPEG_TIMEOUT,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    PROGRESS_MESSAGES,
    FFMPEG_VIDEO_SAMPLE_CMD
)

class VideoProcessor:
    def __init__(self, args):
        self.input_path = args.input_path
        self.compare_path = args.compare_path
        self.screenshot_path = args.screenshot_path
        self.screenshot_samples = args.screenshot_samples
        self.video_samples = args.video_samples
        self.video_length = args.video_length
        self.force = args.force
        self.force_all = args.force_all
        self.extensions = args.extensions
        self.verbose = args.verbose
        self.debug = args.debug
        self.comparison_mode = bool(self.compare_path)
        self.info_filename = "video_info.json"
        self.lower_threshold = args.lower_threshold / 100
        self.upper_threshold = args.upper_threshold / 100
        self.ignore_thresholds = args.ignore_thresholds
        self.force_video_samples = args.force_video_samples
        self.total_screenshots = 0
        self.total_video_samples = 0
        
        # Create root folder for samples
        self.root_folder_name = os.path.basename(os.path.normpath(self.input_path))
        self.root_sample_path = os.path.join(self.screenshot_path, self.root_folder_name)
        os.makedirs(self.root_sample_path, exist_ok=True)

    def debug_print(self, message):
        if self.debug:
            print(f"Debug: {message}")

    def verbose_print(self, message):
        if self.verbose:
            print(message)

    def run(self):
        video_queue = self.scan_for_videos()
        self.debug_print(f"Video queue size: {len(video_queue)}")
        self.process_video_queue(video_queue)

    def scan_for_videos(self):
        video_queue = []
        print(f"{Colors.GREEN}Scanning {Colors.RESET} {self.input_path}")
        
        if not os.path.exists(self.input_path):
            print(f"{Colors.RED}{ERROR_MESSAGES['path_not_exist'].format(path=self.input_path)}{Colors.RESET}")
            return video_queue

        print(f"{Colors.YELLOW}Counting directories under {self.input_path}{Colors.RESET}")
        total_dirs = self.count_directories_with_progress(self.input_path)
        print(f"{Colors.GREEN}Total directories to scan:{Colors.RESET} {total_dirs}")

        processed_dirs = 0
        total_files = 0
        queued_files = 0

        for root, dirs, files in os.walk(self.input_path):
            processed_dirs += 1
            rel_path = os.path.relpath(root, self.input_path)
            
            video_files = [f for f in files if f.lower().endswith(self.extensions)]
            total_files += len(video_files)
            
            if self.verbose:
                print(f"\n{Colors.CYAN}Scanning directory {processed_dirs}/{total_dirs}: {rel_path}{Colors.RESET}")
                print(f"Found {len(video_files)} video files in this directory")
            
            for file in video_files:
                input_file = os.path.join(root, file)
                if self.comparison_mode:
                    compare_file = os.path.join(self.compare_path, rel_path, file)
                    if not os.path.exists(compare_file):
                        if self.verbose:
                            print(f"{Colors.YELLOW}Skipping {file} - No matching file in compare path{Colors.RESET}")
                        continue
                else:
                    compare_file = None
                
                file_name_without_ext = os.path.splitext(file)[0]
                screenshot_dir = os.path.join(self.root_sample_path, rel_path, file_name_without_ext)
                
                should_process_screenshots, should_process_video = self.should_process_video(input_file, compare_file, screenshot_dir)
                
                if should_process_screenshots or should_process_video:
                    video_queue.append((input_file, compare_file, screenshot_dir, should_process_screenshots, should_process_video))
                    queued_files += 1
                    if self.verbose:
                        print(f"{Colors.GREEN}Added to queue: {file} (Screenshots: {'Yes' if should_process_screenshots else 'No'}, Video: {'Yes' if should_process_video else 'No'}){Colors.RESET}")
                elif self.verbose:
                    print(f"{Colors.YELLOW}Skipping {file} - Already processed or unchanged{Colors.RESET}")
            
            if self.verbose:
                print(f"{Colors.MAGENTA}Directory summary:{Colors.RESET}")
                print(f"  - Files in queue: {queued_files}")
                print(f"  - Files added from this directory: {queued_files - (total_files - len(video_files))}")
                print(f"  - Files skipped in this directory: {len(video_files) - (queued_files - (total_files - len(video_files)))}")
            else:
                clear_line()
                print(f"\rTotal video files: {total_files}, Files in queue: {queued_files}, Scanning directory {processed_dirs}/{total_dirs}: {rel_path}", end='', flush=True)

        print()  # Print a newline after the progress is complete
        print(f"{Colors.GREEN}Scan complete. Total videos found: {total_files}, Videos in queue: {queued_files}{Colors.RESET} Starting processing...")
        return video_queue

    def count_directories_with_progress(self, path):
        total_dirs = 0
        for root, dirs, files in os.walk(path):
            total_dirs += 1
            clear_line()
            print(f"\rFound {total_dirs} directories: {root}", end='', flush=True)
        clear_line()
        return total_dirs
    
    def should_process_video(self, input_file, compare_file, screenshot_dir):
        self.debug_print(f"Checking if should process {os.path.basename(input_file)}")
        
        if self.force_all:
            self.debug_print("Force all flag is set, processing video")
            return True, True  # Process both screenshots and video samples

        info_file = os.path.join(screenshot_dir, self.info_filename)
        
        # Check for existing screenshots
        existing_screenshots = self.directory_has_files(screenshot_dir, '.png')
        # Check for existing video samples
        existing_video_samples = self.directory_has_files(screenshot_dir, ('.mp4', '.mkv', '.avi'))

        if os.path.exists(info_file):
            with open(info_file, 'r') as f:
                info = json.load(f)
            
            input_size = os.path.getsize(input_file)
            if info['input_size'] == input_size:
                if compare_file:
                    compare_size = os.path.getsize(compare_file)
                    if info['compare_size'] == compare_size:
                        transcode_ratio = info.get('transcode_bitrate_ratio')
                        
                        if transcode_ratio is None:
                            self.debug_print(f"Transcode ratio is None for {os.path.basename(input_file)}, processing video")
                            return not existing_screenshots, not existing_video_samples
                        
                        should_sample_video = (transcode_ratio < self.lower_threshold * 100 or transcode_ratio > self.upper_threshold * 100) or self.ignore_thresholds or self.force_video_samples
                        
                        self.debug_print(f"Transcode ratio: {transcode_ratio}, Lower threshold: {self.lower_threshold * 100}, Upper threshold: {self.upper_threshold * 100}")
                        self.debug_print(f"Should sample video: {should_sample_video}")
                        
                        if should_sample_video:
                            self.verbose_print(f"{Colors.YELLOW}Reprocessing {os.path.basename(input_file)} (bitrate ratio outside threshold){Colors.RESET}")
                            return not existing_screenshots, not existing_video_samples and should_sample_video
                        else:
                            self.verbose_print(f"{Colors.YELLOW}Skipping {os.path.basename(input_file)} (sizes match stored info and bitrate ratio within threshold){Colors.RESET}")
                            return False, False
                else:
                    self.verbose_print(f"{Colors.YELLOW}Skipping {os.path.basename(input_file)} (size matches stored info and no compare file){Colors.RESET}")
                    return False, False

        # If we reach here, it means we need to process the video
        input_bitrate = get_video_bitrate(input_file)
        input_size = os.path.getsize(input_file)

        if compare_file:
            compare_bitrate = get_video_bitrate(compare_file)
            compare_size = os.path.getsize(compare_file)

            if input_bitrate is None or compare_bitrate is None:
                if self.verbose:
                    print(f"{Colors.YELLOW}Warning: Could not retrieve bitrate for {os.path.basename(input_file)} or its comparison file. Processing anyway.{Colors.RESET}")
                should_sample_video = True
            else:
                transcode_ratio = (input_bitrate / compare_bitrate) * 100
                should_sample_video = (transcode_ratio < self.lower_threshold * 100 or transcode_ratio > self.upper_threshold * 100) or self.ignore_thresholds or self.force_video_samples
                
                if self.verbose:
                    print(f"{Colors.CYAN}Transcode bitrate ratio for {os.path.basename(input_file)}: {transcode_ratio:.2f}%{Colors.RESET}")
                    if should_sample_video:
                        print(f"{Colors.YELLOW}Video sample will be created (outside {self.lower_threshold * 100}-{self.upper_threshold * 100} threshold){Colors.RESET}")
                    else:
                        print(f"{Colors.GREEN}No video sample needed (within {self.lower_threshold * 100}-{self.upper_threshold * 100} threshold){Colors.RESET}")
        else:
            compare_bitrate = None
            compare_size = None
            should_sample_video = True if self.video_samples > 0 else False

        self.write_video_info(os.path.dirname(info_file), input_bitrate, input_size, compare_bitrate, compare_size)
        return not existing_screenshots, not existing_video_samples and should_sample_video
    
    def directory_has_files(self, dir_path, extensions):
        """Check if the directory contains any files with the given extensions."""
        for root, _, files in os.walk(dir_path):
            if any(file.lower().endswith(extensions) for file in files):
                return True
        return False

    def process_video_queue(self, video_queue):
        total_files = len(video_queue)
        processed_files = 0
        failed_files = 0
        
        for index, (input_file, compare_file, screenshot_dir, should_process_screenshots, should_process_video) in enumerate(video_queue, 1):
            try:
                self.debug_print(f"Processing {os.path.basename(input_file)}")
                self.verbose_print(PROGRESS_MESSAGES['processing_file'].format(
                    index=index, 
                    total=total_files, 
                    filename=os.path.basename(input_file)
                ))
                
                os.makedirs(screenshot_dir, exist_ok=True)
                duration = get_video_duration(input_file)
                timestamps = self.get_random_timestamps(duration)
                self.debug_print(f"Video duration: {duration}, Timestamps: {timestamps}")
            
                screenshots_created = 0
                video_samples_created = 0

                if should_process_screenshots:
                    screenshots_created = self.create_screenshots(input_file, compare_file, screenshot_dir, timestamps, index, total_files)
                    self.debug_print(f"Screenshots created: {screenshots_created}")

                if should_process_video:
                    video_samples_created = self.create_video_samples(input_file, compare_file, screenshot_dir, timestamps[:self.video_samples], index, total_files)
                    self.debug_print(f"Video samples created: {video_samples_created}")

                if screenshots_created > 0 or video_samples_created > 0:
                    processed_files += 1
                    self.verbose_print(SUCCESS_MESSAGES['samples_created'].format(
                        index=index, 
                        total=total_files, 
                        filename=os.path.basename(input_file),
                        screenshots=screenshots_created,
                        video_samples=video_samples_created
                    ))
                else:
                    failed_files += 1
                    self.verbose_print(f"{Colors.RED}Failed {index}/{total_files}: {os.path.basename(input_file)} - No samples created{Colors.RESET}")
            except Exception as e:
                failed_files += 1
                self.verbose_print(f"{Colors.RED}Failed {index}/{total_files}: {os.path.basename(input_file)} - Error: {str(e)}{Colors.RESET}")
                self.debug_print(f"Exception occurred: {str(e)}")

        print()  # Print a newline after all processing is complete
        print(SUCCESS_MESSAGES['processing_complete'].format(
            processed=processed_files, 
            skipped=0,
            failed=failed_files,
            total_screenshots=self.total_screenshots,
            total_video_samples=self.total_video_samples
        ))
        
    def write_video_info(self, screenshot_dir, input_bitrate, input_size, compare_bitrate, compare_size):
        def bytes_to_gb(bytes_value):
            return round(bytes_value / (1024 * 1024 * 1024), 2)

        def bps_to_mbps(bps_value):
            return round(bps_value / 1000000, 2) if bps_value else None

        info = {
            'input_bitrate': input_bitrate,
            'input_bitrate_mbps': bps_to_mbps(input_bitrate),
            'input_size': input_size,
            'input_size_gb': bytes_to_gb(input_size),
            'compare_bitrate': compare_bitrate,
            'compare_bitrate_mbps': bps_to_mbps(compare_bitrate),
            'compare_size': compare_size,
            'compare_size_gb': bytes_to_gb(compare_size) if compare_size else None
        }
        
        # Calculate transcode bitrate ratio
        if compare_bitrate and input_bitrate:
            transcode_ratio = (input_bitrate / compare_bitrate) * 100
            info['transcode_bitrate_ratio'] = round(transcode_ratio, 2)
        else:
            info['transcode_bitrate_ratio'] = None
        
        os.makedirs(screenshot_dir, exist_ok=True)
        info_file = os.path.join(screenshot_dir, self.info_filename)
        
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)

        if self.verbose:
            print(f"{Colors.GREEN}Video info written to {info_file}:{Colors.RESET}")
            if self.debug:   
                debug_print(f"{json.dumps(info, indent=2)}", self.debug)
                
    def update_progress(self, index, total, current, samples, filename):
        clear_line()
        print(f"\rProcessing {index}/{total}: {current}/{samples} {filename}", end='', flush=True)

    def directory_has_screenshots(self, dir_path):
        """Check if the directory or its subdirectories contain any PNG files."""
        for root, _, files in os.walk(dir_path):
            if any(file.lower().endswith('.png') for file in files):
                return True
        return False

    def get_random_timestamps(self, duration):
        return [random.uniform(0, duration) for _ in range(self.screenshot_samples)]
    
    def get_rounded_bitrate_ratio(self, screenshot_dir):
        info_file = os.path.join(screenshot_dir, self.info_filename)
        if os.path.exists(info_file):
            with open(info_file, 'r') as f:
                info = json.load(f)
            ratio = info.get('transcode_bitrate_ratio')
            if ratio is not None:
                return str(round(ratio))
        return "unknown"

    def create_screenshots(self, input_file, compare_file, screenshot_dir, timestamps, index, total_files):
        screenshots_created = 0
        rounded_ratio = self.get_rounded_bitrate_ratio(screenshot_dir) if self.comparison_mode else ""

        for i, timestamp in enumerate(timestamps, 1):
            if not (self.verbose or self.debug):
                self.update_progress(index, total_files, i, self.screenshot_samples, os.path.basename(input_file))
            elif self.verbose or self.debug:
                progress = (index / total_files) * 100
                print_progress(PROGRESS_MESSAGES['creating_screenshots'].format(
                    index=index, 
                    total=total_files, 
                    progress=progress,
                    current=i,
                    samples=self.screenshot_samples,
                    filename=os.path.basename(input_file)
                ), verbose=True)
            
            try:
                timecode = self.format_timecode(timestamp)
                
                if self.comparison_mode:
                    original_cmd = FFMPEG_SCREENSHOT_CMD.copy()
                    original_cmd[2] = str(timestamp)
                    original_cmd[4] = compare_file
                    original_cmd[7] = f"{screenshot_dir}/scr-{rounded_ratio}-{timecode}-original.png"
                    
                    if self.debug:
                        formatted_cmd = ' '.join(shlex.quote(arg) for arg in original_cmd)
                        print(f"{Colors.LIGHT_BLUE}Debug: FFmpeg screenshot command (original):{Colors.RESET}")
                        print(f"{Colors.LIGHT_BLUE}{formatted_cmd}{Colors.RESET}")
                    
                    subprocess.run(original_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=FFMPEG_TIMEOUT, check=True)

                input_cmd = FFMPEG_SCREENSHOT_CMD.copy()
                input_cmd[2] = str(timestamp)
                input_cmd[4] = input_file
                input_cmd[7] = f"{screenshot_dir}/scr-{rounded_ratio}-{timecode}-{'transcoded' if self.comparison_mode else 'screen'}.png"
                
                if self.debug:
                    formatted_cmd = ' '.join(shlex.quote(arg) for arg in input_cmd)
                    print(f"{Colors.LIGHT_BLUE}Debug: FFmpeg screenshot command (input):{Colors.RESET}")
                    print(f"{Colors.LIGHT_BLUE}{formatted_cmd}{Colors.RESET}")
                
                subprocess.run(input_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=FFMPEG_TIMEOUT, check=True)
                
                screenshots_created += 1
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                error_cmd = original_cmd if self.comparison_mode and "original" in str(e) else input_cmd
                formatted_cmd = ' '.join(shlex.quote(arg) for arg in error_cmd)
                if self.verbose or self.debug:
                    print_progress(f"{Colors.RED}Error creating screenshot {timecode} for {os.path.basename(input_file)}:{Colors.RESET}", verbose=True)
                    print_progress(f"{Colors.RED}Command: {formatted_cmd}{Colors.RESET}", verbose=True)
                    print_progress(f"{Colors.RED}{ERROR_MESSAGES['ffmpeg_error'].format(error=str(e))}{Colors.RESET}", verbose=True)

        self.total_screenshots += screenshots_created
        return screenshots_created
    
    def create_video_samples(self, input_file, compare_file, screenshot_dir, timestamps, index, total_files):
        self.debug_print(f"Entering create_video_samples method")
        video_samples_created = 0
        rounded_ratio = self.get_rounded_bitrate_ratio(screenshot_dir) if self.comparison_mode else ""
        
        for i, timestamp in enumerate(timestamps, 1):
            self.debug_print(f"Processing video sample {i}/{len(timestamps)}")
            try:
                timecode = self.format_timecode(timestamp)
                self.debug_print(f"Timecode: {timecode}")
                
                if self.comparison_mode:
                    original_cmd = FFMPEG_VIDEO_SAMPLE_CMD.copy()
                    original_cmd[2] = str(timestamp)
                    original_cmd[4] = compare_file
                    original_cmd[6] = str(self.video_length)
                    original_cmd[-1] = f"{screenshot_dir}/vid-{rounded_ratio}-{timecode}-original.mp4"
                    
                    if self.debug:
                        formatted_cmd = ' '.join(shlex.quote(arg) for arg in original_cmd)
                        print(f"{Colors.LIGHT_BLUE}Debug: FFmpeg video sample command (original):{Colors.RESET}")
                        print(f"{Colors.LIGHT_BLUE}{formatted_cmd}{Colors.RESET}")
                    
                    subprocess.run(original_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=FFMPEG_TIMEOUT, check=True)

                input_cmd = FFMPEG_VIDEO_SAMPLE_CMD.copy()
                input_cmd[2] = str(timestamp)
                input_cmd[4] = input_file
                input_cmd[6] = str(self.video_length)
                input_cmd[-1] = f"{screenshot_dir}/vid-{rounded_ratio}-{timecode}-{'transcoded' if self.comparison_mode else 'sample'}.mp4"
                
                if self.debug:
                    formatted_cmd = ' '.join(shlex.quote(arg) for arg in input_cmd)
                    print(f"{Colors.LIGHT_BLUE}Debug: FFmpeg video sample command (input):{Colors.RESET}")
                    print(f"{Colors.LIGHT_BLUE}{formatted_cmd}{Colors.RESET}")
                
                subprocess.run(input_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=FFMPEG_TIMEOUT, check=True)
                
                video_samples_created += 1
                self.debug_print(f"Video sample {i} created successfully")
            except Exception as e:
                self.debug_print(f"Error creating video sample: {str(e)}")
                self.debug_print(f"Error type: {type(e).__name__}")
                self.debug_print(f"Error details: {repr(e)}")
                if self.verbose or self.debug:
                    print_progress(f"{Colors.RED}Error creating video sample {timecode} for {os.path.basename(input_file)}:{Colors.RESET}", verbose=True)
                    print_progress(f"{Colors.RED}Error: {str(e)}{Colors.RESET}", verbose=True)

        self.debug_print(f"Exiting create_video_samples method. Samples created: {video_samples_created}")
        self.total_video_samples += video_samples_created
        return video_samples_created
    
    def format_timecode(self, seconds):
        """Convert seconds to a timecode string format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}_{minutes:02d}_{secs:02d}_{millisecs:03d}"