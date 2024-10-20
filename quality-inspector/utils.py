import os
import shutil
import logging
from colorama import Fore, Style # type: ignore

from constants import Colors, Styles, SUCCESS_MESSAGES, PROGRESS_MESSAGES

def setup_logging(verbose, debug):
    if debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    elif verbose:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def clear_line():
    """Clear the current line in the console."""
    columns, _ = shutil.get_terminal_size()
    print('\r' + ' ' * columns, end='', flush=True)

def print_progress(message, end='\n', verbose=False):
    if verbose:
        print(message)
    else:
        clear_line()
        print(f"\r{message}", end=end, flush=True)

def debug_print(message, debug=False):
    if debug:
        print(f"{Colors.CYAN}[DEBUG] {message}{Colors.RESET}")

def count_directories(path):
    total_dirs = 0
    for root, dirs, files in os.walk(path):
        total_dirs += 1
        clear_line()
        print(f"\rDirectories found {total_dirs}: {root}", end='', flush=True)
    clear_line()
    print(f"Total directories found: {total_dirs}")
    return total_dirs

def generate_summary(args):
    summary = [
        f"{Colors.CYAN}{Styles.BOLD}Video Quality Comparison Tool - Execution Summary{Colors.RESET}",
        f"{Colors.CYAN}{'=' * 50}{Colors.RESET}",
        f"{Colors.GREEN}Transcoded videos path:{Colors.RESET} {args.transcode_path}",
        f"{Colors.GREEN}Original videos path:{Colors.RESET} {args.original_path}",
        f"{Colors.GREEN}Screenshots will be saved to:{Colors.RESET} {args.screenshot_path}",
        f"{Colors.GREEN}Number of screenshot samples per video:{Colors.RESET} {args.screenshot_samples}",
        f"{Colors.GREEN}Video file extensions to process:{Colors.RESET} {', '.join(args.extensions)}",
        f"{Colors.GREEN}Force regeneration of existing screenshots:{Colors.RESET} {'Yes' if args.force else 'No'}",
        f"{Colors.GREEN}Verbose output:{Colors.RESET} {'Enabled' if args.verbose else 'Disabled'}",
        f"{Colors.GREEN}Debug output:{Colors.RESET} {'Enabled' if args.debug else 'Disabled'}",
        f"\n{Colors.YELLOW}{Styles.BOLD}Operation mode:{Colors.RESET}",
        "- The script will scan all directories in the transcoded videos path.",
        "- It will compare each transcoded video with its original counterpart.",
        f"- {'All videos will be processed, regardless of existing screenshots.' if args.force else 'Videos with existing screenshots will be skipped unless forced.'}"
        "- Videos with identical bitrates will be skipped.",
        f"\n{Colors.YELLOW}{Styles.BOLD}Process:{Colors.RESET}",
        "1. Scan directories and build a queue of videos to process.",
        "2. For each video in the queue:",
        "   a. Compare bitrates of transcoded and original videos.",
        "   b. If bitrates differ, generate screenshot samples.",
        "   c. Save screenshots for visual comparison.",
    ]
    return "\n".join(summary)
