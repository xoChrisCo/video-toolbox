import sys
import shutil
import csv
from decimal import Decimal
import os
from config import LANGUAGE_MAPPING

def format_time(seconds):
    """
    Format a duration in seconds to a human-readable string.

    Args:
    seconds (float): The duration in seconds.

    Returns:
    str: A formatted string representing the duration.
    """
    years, remainder = divmod(int(seconds), 31536000)  # 365 days
    months, remainder = divmod(remainder, 2592000)  # 30 days
    weeks, remainder = divmod(remainder, 604800)  # 7 days
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if weeks > 0:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    if len(parts) > 1:
        return ', '.join(parts[:-1]) + f" and {parts[-1]}"
    elif parts:
        return parts[0]
    else:
        return "0 seconds"
    
def format_number(number):
    """
    Format a number with thousands separators.

    Args:
    number (int, float, or Decimal): The number to format.

    Returns:
    str: The formatted number as a string.
    """
    if isinstance(number, (int, float)):
        return f"{number:,}"
    elif isinstance(number, Decimal):
        return f"{number:f}".rstrip('0').rstrip('.')
    else:
        return str(number)


def format_large_number(number):
    """
    Format a large number into a more readable string with suffix.

    Args:
    number (int, float, Decimal, or str): The number to format.

    Returns:
    str: The formatted number as a string with appropriate suffix.
    """
    try:
        if isinstance(number, str):
            number = float(number)
        if isinstance(number, Decimal):
            number = float(number)
        if number >= 1e15:
            return f"{number/1e15:.2f} quadrillion"
        elif number >= 1e12:
            return f"{number/1e12:.2f} trillion"
        elif number >= 1e9:
            return f"{number/1e9:.2f} billion"
        elif number >= 1e6:
            return f"{number/1e6:.2f} million"
        else:
            return f"{number:,.0f}"
    except (ValueError, TypeError):
        return "Error: Invalid number"

def safe_float(value, default=0.0):
    """
    Safely convert a value to float, returning a default if conversion fails.

    Args:
    value: The value to convert to float.
    default (float): The default value to return if conversion fails.

    Returns:
    float: The converted value or the default.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_decimal(value, default=Decimal('0')):
    """
    Safely convert a value to Decimal, returning a default if conversion fails.

    Args:
    value: The value to convert to Decimal.
    default (Decimal): The default value to return if conversion fails.

    Returns:
    Decimal: The converted value or the default.
    """
    try:
        return Decimal(value)
    except (ValueError, TypeError):
        return default

def get_terminal_width():
    """
    Get the width of the terminal.

    Returns:
    int: The width of the terminal in characters.
    """
    return shutil.get_terminal_size().columns

def print_progress(message):
    """
    Print a progress message, overwriting the current line.

    Args:
    message (str): The message to print.
    """
    terminal_width = get_terminal_width()
    sys.stdout.write('\r' + ' ' * terminal_width)  # Clear the line
    sys.stdout.write('\r' + message[:terminal_width - 1])
    sys.stdout.flush()

def remove_statistics_tags(tags):
    """
    Remove statistics tags from a dictionary.

    Args:
    tags (dict): A dictionary of tags.

    Returns:
    dict: A new dictionary with statistics tags removed.
    """
    return {k: v for k, v in tags.items() if not k.startswith('_STATISTICS_')}

class CustomDialect(csv.excel):
    """A custom CSV dialect."""
    quoting = csv.QUOTE_NONE
    escapechar = '\\'

def custom_quoting(field):
    """
    Determine the quoting for a CSV field.

    Args:
    field (str): The field to check.

    Returns:
    int: The quoting constant to use for this field.
    """
    if field == 'Raw ffprobe output':
        return csv.QUOTE_NONE
    return csv.QUOTE_MINIMAL

def count_files(root_folder, verbosity):
    count = 0
    for root, _, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                count += 1
                if verbosity >= 1:
                    print_progress(f"{count} files discovered - Searching {root}")
    if verbosity >= 1:
        print()  # Move to the next line after counting
    return count

def safe_get_stat(stats, *keys, default="Error"):
    """
    Safely get a value from a nested dictionary.

    Args:
    stats (dict): The dictionary to search.
    *keys: The keys to use for nested access.
    default: The default value to return if the key is not found.

    Returns:
    The value found at the specified keys, or the default value.
    """
    try:
        value = stats
        for key in keys:
            value = value[key]
        return value
    except KeyError:
        return default

def combine_language_counts(language_counts):
    """
    Combine language counts, mapping 2-letter codes to 3-letter codes.

    Args:
    language_counts (Counter): A Counter object with language counts.

    Returns:
    dict: A dictionary with combined language counts.
    """
    combined = {}
    
    for lang, count in language_counts.items():
        main_lang = LANGUAGE_MAPPING.get(lang, lang)
        combined[main_lang] = combined.get(main_lang, 0) + count
    
    return combined