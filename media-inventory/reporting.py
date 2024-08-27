import csv 
from colorama import Fore, Style # type: ignore
import os

def generate_report(output_dir, output_file, stats, total_time, avg_time_per_file):
    # Calculate percentages safely
    def safe_percentage(part, whole):
        return f"{(part / whole * 100):.2f}%" if whole > 0 else "0.00%"

    error_percentage = safe_percentage(stats['error'], stats['processed'])
    failed_percentage = safe_percentage(stats['failed'], stats['processed'])
    low_percentage = safe_percentage(stats['low'], stats['processed'])
    medium_percentage = safe_percentage(stats['medium'], stats['processed'])
    high_percentage = safe_percentage(stats['high'], stats['processed'])
    no_issues_percentage = safe_percentage(stats['no_issues'], stats['processed'])
    with_issues_percentage = safe_percentage(stats['with_issues'], stats['processed'])

    report = f"""
{Fore.YELLOW}{Style.BRIGHT}Process Report
{Fore.YELLOW}{'=' * 50}

{Fore.CYAN}Files Processed: {Fore.WHITE}{stats['processed']} / {stats['total']}
{Fore.CYAN}Time Taken: {Fore.WHITE}{total_time:.2f} seconds
{Fore.CYAN}Avg Time per File: {Fore.WHITE}{avg_time_per_file:.2f} seconds

{Fore.YELLOW}Transcode Performance:
{Fore.CYAN}Error: {Fore.WHITE}{stats['error']} ({error_percentage})
{Fore.CYAN}Failed: {Fore.WHITE}{stats['failed']} ({failed_percentage})
{Fore.CYAN}Low: {Fore.WHITE}{stats['low']} ({low_percentage})
{Fore.CYAN}Medium: {Fore.WHITE}{stats['medium']} ({medium_percentage})
{Fore.CYAN}High: {Fore.WHITE}{stats['high']} ({high_percentage})

{Fore.YELLOW}Issues:
{Fore.CYAN}Files with No Issues: {Fore.WHITE}{stats['no_issues']} ({no_issues_percentage})
{Fore.CYAN}Files with Issues: {Fore.WHITE}{stats['with_issues']} ({with_issues_percentage})
"""

    if stats['error'] > 0:
        report += f"\n{Fore.YELLOW}Errors encountered:{Style.RESET_ALL}\n"
        try:
            with open(output_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter='\t')
                next(reader, None)  # Skip header, use None as default to avoid StopIteration
                for row in reader:
                    if row and row[-2] == "Error":  # Check if row is not empty
                        report += f"{Fore.RED}{row[0]}: {row[-1]}{Style.RESET_ALL}\n"
        except Exception as e:
            report += f"{Fore.RED}Error reading CSV file: {str(e)}{Style.RESET_ALL}\n"

    print(report)

    # Write report to file (without color codes)
    report_file = os.path.join(output_dir, 'process_report.txt')
    with open(report_file, 'w') as f:
        f.write(report.replace(Fore.YELLOW, '').replace(Fore.CYAN, '').replace(Fore.WHITE, '').replace(Fore.RED, '').replace(Style.BRIGHT, '').replace(Style.RESET_ALL, ''))
