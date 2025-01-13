import subprocess

def run_cloudcompare_ransac(input_file):
    # CloudCompare command to run RANSAC for shape detection (Plane, Sphere, Cylinder, Cone, Torus)
    command = [
        "/usr/bin/CloudCompare",  # Adjust the path as necessary
        "-SILENT",                # Silent mode (no GUI)
        "-O", input_file,         # Input point cloud file
        "-RANSAC", "PLANE",       # Use RANSAC for plane detection (adjust for other shapes)
        "-SPHERE", "1",           # Enable sphere detection
        "-CYLINDER", "1",         # Enable cylinder detection
        "-CONE", "1",             # Enable cone detection
        "-TORUS", "1",            # Enable torus detection
        "-MIN_SUPPORT_POINTS", "500",   # Minimum support points per primitive
        "-MAX_DISTANCE_TO_PRIMITIVE", "1.501",  # Max distance to primitive
        "-SAMPLING_RESOLUTION", "3.003",  # Sampling resolution
        "-MAX_NORMAL_DEVIATION", "25.00",  # Max normal deviation
        "-OVERLOOKING_PROBABILITY", "0.010000",  # Overlooking probability
        "-OUTPUT_INDIVIDUAL_SUBCLOUDS", "1",  # Save individual subclouds for each detected shape
        "-SAVE_CLOUDS",  # Save the clouds
        "-NO_TIMESTAMP"  # Disable timestamp in filenames
    ]
    
    # Run the CloudCompare command
    subprocess.run(command)

# Example usage
input_file = "/home/rog/Documents/scanner/transform/ransac/181.ply"
run_cloudcompare_ransac(input_file)
