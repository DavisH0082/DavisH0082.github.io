"""
Python Script: server_hard_drive_check.py
Version: 2.0
Author: Davis Hood
Last Updated: 09/09/2025
Assisted by: Claude Sonnet 4 and VSCode Suggestions

Description:
The intended use case for this script is to compare the files present in a hard drive directory against a server directory to report what files are missing from the server.
The script will scan both directories recursively, comparing files by name and size, and report any discrepancies present in the server compared to the hard drive.
This version handles recursive subdirectory structures in both directories. 

Run this script from the command line by invoking the command: 

python server_hard_drive_check.py /path/to/hard_drive /path/to/server_directory [--verbose]

Edge cases not accounted for may include:
- Files with permission issues that prevent access
- Symbolic links (the script currently does not follow symlinks)
- Hidden files (files starting with '.' on Unix-like systems)
- Irregular file types (e.g., sockets, device files)
- Paths containing special characters or spaces (account for spaces in the file paths by quoting the entire path in the command line)
"""

import os, sys, argparse
from pathlib import Path


def get_all_files_recursive(directory_path):
    """
    Get all files recursively from a directory with their relative paths and sizes.
    This function explicitly handles subdirectories at any depth level.
    """
    files_info = {}
    directories_processed = set()
    directory = Path(directory_path)
    
    print(f"Scanning directory: {directory_path}")
    
    # First pass: count total files for progress bar with live updates
    print("Counting files for progress tracking...")
    total_files = 0
    for item in directory.rglob('*'):
        if item.is_file():
            total_files += 1
            if total_files % 100 == 0 or total_files < 100:  # Update every 100 files or for small counts
                print(f'\rDiscovering files... {total_files:,} files found so far', end='', flush=True)
    
    print(f'\rFound {total_files:,} total files to process' + ' ' * 20)  # Clear any extra characters
    
    # Progress bar setup
    processed_files = 0
    bar_width = 50
    
    def update_progress_bar(current, total):
        """Update and display progress bar"""
        if total == 0:
            return
        
        percentage = (current / total) * 100
        filled_length = int(bar_width * current // total)
        bar = '█' * filled_length + '░' * (bar_width - filled_length)
        
        # Clear the line and print progress bar
        print(f'\r|{bar}| {percentage:.1f}% scanned {current:,}/{total:,} files', end='', flush=True)
    
    # Use rglob('*') to recursively traverse ALL subdirectories
    for item_path in directory.rglob('*'):
        if item_path.is_file():
            # Process files - get relative path and size
            relative_path = item_path.relative_to(directory)
            try:
                file_size = item_path.stat().st_size
                files_info[str(relative_path)] = file_size
                
                # Track the directory containing this file
                parent_dir = relative_path.parent
                if str(parent_dir) != '.':
                    directories_processed.add(str(parent_dir))
                
                if args.verbose:
                    print(f"\n  Found file: {relative_path} ({file_size:,} bytes)")
                    
            except (OSError, PermissionError) as e:
                if args.verbose:
                    print(f"\n  WARNING: Could not access file {relative_path}: {e}")
            
            # Update progress bar
            processed_files += 1
            if not args.verbose:  # Only show progress bar when not in verbose mode
                update_progress_bar(processed_files, total_files)
                
        elif item_path.is_dir():
            # Process directories - track them for reporting
            relative_path = item_path.relative_to(directory)
            directories_processed.add(str(relative_path))
            
            if args.verbose:
                print(f"\n  Processing directory: {relative_path}/")
    
    # Complete the progress bar
    if not args.verbose:
        print()  # New line after progress bar
    
    # Report summary of what was processed
    print(f"  → Found {len(files_info):,} files in {len(directories_processed):,} subdirectories")
    
    if args.verbose and directories_processed:
        print("  Subdirectories processed:")
        for subdir in sorted(directories_processed):
            file_count = sum(1 for f in files_info.keys() if f.startswith(subdir + os.sep) or f.startswith(subdir + '/'))
            print(f"    {subdir}/ ({file_count} files)")
    
    return files_info


def compare_directories(hard_drive_path, server_path):
    """
    Compare files between hard drive and server directories.
    Handles recursive directory structures including nested subdirectories.
    """
    print(f"\nComparing files between:")
    print(f"Hard Drive: {hard_drive_path}")
    print(f"Server Directory: {server_path}")
    print("=" * 80)
    
    # Get all files from both directories recursively
    print("\n1. SCANNING HARD DRIVE:")
    hard_drive_files = get_all_files_recursive(hard_drive_path)
    
    print("-" * 80)
    
    print("\n2. SCANNING SERVER DIRECTORY:")
    server_files = get_all_files_recursive(server_path)
    
    print("=" * 80)
    
    print("\n3. COMPARING FILES:")
    
    # Create filename-based lookup for server files (filename -> [(path, size), ...])
    server_files_by_name = {}
    for file_path, file_size in server_files.items():
        filename = os.path.basename(file_path)
        if filename not in server_files_by_name:
            server_files_by_name[filename] = []
        server_files_by_name[filename].append((file_path, file_size))
    
    # Track statistics
    missing_files = 0
    size_mismatch_files = 0
    identical_files = 0
    missing_file_details = []
    mismatch_file_details = []
    
    # Process each file from hard drive (including files in all subdirectories)
    for file_path, hard_drive_size in sorted(hard_drive_files.items()):
        filename = os.path.basename(file_path)
        print(f"CHECKING: {file_path}")
        
        if filename not in server_files_by_name:
            # File not present in server directory (by filename)
            print(f"  → MISSING: {filename} not found anywhere in server directory (Size: {hard_drive_size:,} bytes)")
            missing_files += 1
            missing_file_details.append((file_path, hard_drive_size))
            
        else:
            # File exists by filename, check for size matches
            matching_files = [entry for entry in server_files_by_name[filename] if entry[1] == hard_drive_size]
            
            if matching_files:
                # File present with matching size
                if len(matching_files) == 1:
                    server_path_match = matching_files[0][0]
                    print(f"  → IDENTICAL: {filename} found at server: {server_path_match} (Size: {hard_drive_size:,} bytes)")
                else:
                    server_paths_match = [entry[0] for entry in matching_files]
                    print(f"  → IDENTICAL: {filename} found at multiple server locations with matching size: {', '.join(server_paths_match)} (Size: {hard_drive_size:,} bytes)")
                identical_files += 1
            else:
                # File present but no size match
                all_server_instances = server_files_by_name[filename]
                server_info = ', '.join([f"{entry[0]}({entry[1]:,} bytes)" for entry in all_server_instances])
                print(f"  → SIZE_DIFF: {filename} found but no size match - Hard Drive: {hard_drive_size:,} bytes, Server instances: {server_info}")
                size_mismatch_files += 1
                mismatch_file_details.append((file_path, hard_drive_size, all_server_instances))
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"  Total files in hard drive: {len(hard_drive_files):,}")
    print(f"  Files missing from server directory: {missing_files:,}")
    print(f"  Files with size differences: {size_mismatch_files:,}")
    print(f"  Identical files: {identical_files:,}")
    print(f"  Total files in server directory: {len(server_files):,}")
    
    # print missing and size mismatch details if any
    if missing_files > 0:
        print("\nMissing files details:")
        for missing_file, size in missing_file_details:
            print(f" → MISSING: {missing_file} (Size: {size:,} bytes)")
            
    if size_mismatch_files > 0:
        print("\nSize mismatch files details:")
        for mismatch_file, hd_size, server_instances in mismatch_file_details:
            server_info = ', '.join([f"{entry[0]}({entry[1]:,} bytes)" for entry in server_instances])
            print(f" → SIZE_DIFF: {mismatch_file} - Hard Drive: {hd_size:,} bytes, Server instances: {server_info}")
    
    

if __name__ == "__main__":
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="Compare files between a hard drive directory and a server directory with full recursive subdirectory support.",
        epilog="""
Examples:
  python script.py /home/user/data /mnt/server/backup
  python script.py C:\\MyFiles \\\\server\\share\\files
  python script.py /path/to/hard_drive /path/to/server_directory --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "hard_drive_path", 
        type=str, 
        help="Path to the hard drive directory to check."
    )
    
    parser.add_argument(
        "server_path", 
        type=str, 
        help="Path to the server directory for comparison."
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output with detailed file processing and subdirectory analysis."
    )
    
    # Parse the arguments
    args = parser.parse_args()
    hard_drive_file_path = args.hard_drive_path
    server_file_path = args.server_path
    
    # Validate paths exist
    if not (os.path.exists(hard_drive_file_path) and os.path.exists(server_file_path)):
        if not os.path.exists(hard_drive_file_path):
            print(f"ERROR: Hard drive path '{hard_drive_file_path}' does not exist.")
            sys.exit(1)
        elif not os.path.exists(server_file_path):
            print(f"ERROR: Server directory path '{server_file_path}' does not exist.")
            sys.exit(1)
        else:
            print("ERROR: Both directory paths do not exist.")
            sys.exit(1)
            
    # Validate paths are directories
    if not (os.path.isdir(hard_drive_file_path) and os.path.isdir(server_file_path)):
        if not os.path.isdir(hard_drive_file_path):
            print(f"ERROR: Hard drive path '{hard_drive_file_path}' is not a directory.")
            sys.exit(1)
        elif not os.path.isdir(server_file_path):
            print(f"ERROR: Server directory path '{server_file_path}' is not a directory.")
            sys.exit(1)
        else:
            print("ERROR: The paths entered are not directories.")
            sys.exit(1)
        
    # Perform the comparison
    try:
        compare_directories(hard_drive_file_path, server_file_path)
    except PermissionError as e:
        print(f"ERROR: Permission denied accessing files: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        sys.exit(1)