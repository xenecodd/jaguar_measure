import os
import subprocess

def extract_all_entities_from_bin(input_bin_file):
    """
    Extracts all entities from a .bin file and saves each as a .ply file.
    
    Args:
        input_bin_file (str): Path to the input .bin file.
    """
    # Command to open and export all entities
    command = [
        "/usr/bin/CloudCompare",  # Adjust the path to your CloudCompare executable
        "-SILENT",                # Suppress UI
        "-O", input_bin_file,     # Open the .bin file
        "-C_EXPORT_FMT", "PLY",   # Set export format to .ply
        "-NO_TIMESTAMP",          # Disable timestamp in filenames
        "-SAVE_CLOUDS",           # Save all clouds
    ]

    # Run the command
    subprocess.run(command)

# Example usage
input_directory = "/home/rog/Documents/scanner/transform/scripts/"
output_dir = "/home/rog/Documents/scanner/"

# List all files in the directory
all_files = os.listdir(input_directory)

# Filter files that start with "MERGED_MERGED"
input_bins = [file for file in all_files if file.startswith("Cleaned_PointCloud - Cloud")]
removables = [file for file in all_files if file.startswith("181_2024")]

# Process each file individually
for input_bin in input_bins:
    input_bin_path = os.path.join(input_directory, input_bin)
    extract_all_entities_from_bin(input_bin_path)

# Optionally remove files after processing
for input_bin, remove in zip(input_bins, removables):  # Using zip to iterate over two lists
    input_bin_path = os.path.join(input_directory, input_bin)
    remove_bin_path = os.path.join(input_directory, remove)
    
    # Remove the files
    os.remove(input_bin_path)
    os.remove(remove_bin_path)
