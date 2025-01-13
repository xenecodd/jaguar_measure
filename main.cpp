#include <pcl/point_types.h>
#include <pcl/io/pcd_io.h>
#include <pcl/common/transforms.h>
#include <pcl/filters/filter.h>
#include <pcl/filters/voxel_grid.h>
#include <Eigen/Dense>
#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>
#include <iostream>
#include <chrono>  // Include chrono for time measurement

#define MY_DEG2RAD(x) ((x) * M_PI / 180.0f)

using PointT = pcl::PointXYZ;
using PointCloudT = pcl::PointCloud<PointT>;

// Function to generate combined transformation matrix for rotation and translation
Eigen::Matrix4f getTransformationMatrix(float angle_degrees, float x, float y, float z, char axis) {
    float theta = MY_DEG2RAD(angle_degrees);
    Eigen::Matrix4f transform = Eigen::Matrix4f::Identity();

    // Apply rotation based on specified axis
    if (axis == 'X' || axis == 'x') {
        transform(1, 1) = cos(theta);
        transform(1, 2) = -sin(theta);
        transform(2, 1) = sin(theta);
        transform(2, 2) = cos(theta);
    } else if (axis == 'Y' || axis == 'y') {
        transform(0, 0) = cos(theta);
        transform(0, 2) = sin(theta);
        transform(2, 0) = -sin(theta);
        transform(2, 2) = cos(theta);
    } else if (axis == 'Z' || axis == 'z') {
        transform(0, 0) = cos(theta);
        transform(0, 1) = -sin(theta);
        transform(1, 0) = sin(theta);
        transform(1, 1) = cos(theta);
    }

    // Translation components
    transform(0, 3) = x;
    transform(1, 3) = y;
    transform(2, 3) = z;

    return transform;
}

int main() {
    // Start timing
    auto start_time = std::chrono::high_resolution_clock::now();

    // Load the reference point cloud
    PointCloudT::Ptr reference_cloud(new PointCloudT);
    if (pcl::io::loadPCDFile("/home/rog/Documents/scanner/transform/point_cloud_00090.pcd", *reference_cloud) == -1) {
        std::cerr << "Error loading reference cloud file!" << std::endl;
        return -1;
    }
    std::vector<int> indices;
    pcl::removeNaNFromPointCloud(*reference_cloud, *reference_cloud, indices);

    // Load and transform point_cloud_00030.pcd
    PointCloudT::Ptr cloud_30(new PointCloudT);
    if (pcl::io::loadPCDFile("/home/rog/Documents/scanner/transform/point_cloud_00030.pcd", *cloud_30) == -1) {
        std::cerr << "Error loading point_cloud_00030.pcd file!" << std::endl;
        return -1;
    }
    pcl::removeNaNFromPointCloud(*cloud_30, *cloud_30, indices);

    Eigen::Matrix4f transform_30 = getTransformationMatrix(30, 38, -18, 15, 'Y');
    pcl::transformPointCloud(*cloud_30, *cloud_30, transform_30);

    // Load and transform point_cloud_00031.pcd
    PointCloudT::Ptr cloud_31(new PointCloudT);
    if (pcl::io::loadPCDFile("/home/rog/Documents/scanner/transform/point_cloud_00031.pcd", *cloud_31) == -1) {
        std::cerr << "Error loading point_cloud_00031.pcd file!" << std::endl;
        return -1;
    }
    pcl::removeNaNFromPointCloud(*cloud_31, *cloud_31, indices);

    Eigen::Matrix4f transform_31 = getTransformationMatrix(-30, -32, -18, -37, 'Y');
    pcl::transformPointCloud(*cloud_31, *cloud_31, transform_31);

    // Load and transform point_cloud_00180.pcd
    PointCloudT::Ptr cloud_180(new PointCloudT);
    if (pcl::io::loadPCDFile("/home/rog/Documents/scanner/transform/point_cloud_0180.pcd", *cloud_180) == -1) {
        std::cerr << "Error loading point_cloud_00180.pcd file!" << std::endl;
        return -1;
    }
    pcl::removeNaNFromPointCloud(*cloud_180, *cloud_180, indices);

    Eigen::Matrix4f transform_180_x = getTransformationMatrix(90, 0, 0, 0, 'X');
    Eigen::Matrix4f transform_180_z = getTransformationMatrix(180, 109, 360, -127, 'Z');
    Eigen::Matrix4f transform_180_y = getTransformationMatrix(0, 0, 0, 0, 'Y');

    Eigen::Matrix4f combined_transform_180 = transform_180_z * transform_180_y * transform_180_x;
    pcl::transformPointCloud(*cloud_180, *cloud_180, combined_transform_180);

    // Load and transform point_cloud_00181.pcd
    PointCloudT::Ptr cloud_181(new PointCloudT);
    if (pcl::io::loadPCDFile("/home/rog/Documents/scanner/transform/point_cloud_00181.pcd", *cloud_181) == -1) {
        std::cerr << "Error loading point_cloud_00181.pcd file!" << std::endl;
        return -1;
    }
    
    pcl::removeNaNFromPointCloud(*cloud_181, *cloud_181, indices);

    Eigen::Matrix4f transform_181_x = getTransformationMatrix(-90, 0, 0, 0, 'X');
    Eigen::Matrix4f transform_181_z = getTransformationMatrix(180, 94, 92, 40, 'Z');
    Eigen::Matrix4f combined_transform_181 = transform_181_z * transform_181_x;

    pcl::transformPointCloud(*cloud_181, *cloud_181, combined_transform_181);

    // Apply VoxelGrid Filter
    pcl::VoxelGrid<PointT> voxel_grid;
    PointCloudT::Ptr filtered_reference_cloud(new PointCloudT);
    PointCloudT::Ptr filtered_cloud_30(new PointCloudT);
    PointCloudT::Ptr filtered_cloud_31(new PointCloudT);
    PointCloudT::Ptr filtered_cloud_180(new PointCloudT);
    PointCloudT::Ptr filtered_cloud_181(new PointCloudT);

    voxel_grid.setInputCloud(reference_cloud);
    voxel_grid.setLeafSize(0.2f, 0.2f, 0.2f);
    voxel_grid.filter(*filtered_reference_cloud);

    voxel_grid.setInputCloud(cloud_30);
    voxel_grid.filter(*filtered_cloud_30);

    voxel_grid.setInputCloud(cloud_31);
    voxel_grid.filter(*filtered_cloud_31);

    voxel_grid.setInputCloud(cloud_180);
    voxel_grid.filter(*filtered_cloud_180);

    voxel_grid.setInputCloud(cloud_181);
    voxel_grid.filter(*filtered_cloud_181);

    // Merge the transformed clouds into the reference cloud
    *filtered_reference_cloud += *filtered_cloud_30;
    *filtered_reference_cloud += *filtered_cloud_31;
    *filtered_reference_cloud += *filtered_cloud_180;
    *filtered_reference_cloud += *filtered_cloud_181;

    // PLY formatında kaydet
    if (pcl::io::savePLYFile("/home/rog/Documents/scanner/transform/scripts/MERGED.ply", *filtered_reference_cloud) == -1) {
        std::cerr << "Error: Could not save PLY file!" << std::endl;
        return -1;
    }

    if (pcl::io::savePLYFile("/home/rog/Documents/scanner/transform/scripts/90.ply", *reference_cloud) == -1) {
        std::cerr << "Error: Could not save PLY file!" << std::endl;
        return -1;
    }
    if (pcl::io::savePLYFile("/home/rog/Documents/scanner/transform/scripts/180.ply", *filtered_cloud_180) == -1) {
        std::cerr << "Error: Could not save PLY file!" << std::endl;
        return -1;
    }
    if (pcl::io::savePLYFile("/home/rog/Documents/scanner/transform/scripts/30.ply", *filtered_cloud_30) == -1) {
        std::cerr << "Error: Could not save PLY file!" << std::endl;
        return -1;
    }
    if (pcl::io::savePLYFile("/home/rog/Documents/scanner/transform/scripts/31.ply", *filtered_cloud_31) == -1) {
        std::cerr << "Error: Could not save PLY file!" << std::endl;
        return -1;
    }
    if (pcl::io::savePLYFile("/home/rog/Documents/scanner/transform/scripts/181.ply", *filtered_cloud_181) == -1) {
        std::cerr << "Error: Could not save PLY file!" << std::endl;
        return -1;
    }

    // End timing
    auto end_time = std::chrono::high_resolution_clock::now();

    // Calculate and print the elapsed time
    std::chrono::duration<double> duration = end_time - start_time;
    std::cout << "Processing took: " << duration.count() << " seconds." << std::endl;

    std::cout << "Point clouds transformed and merged without ICP, saved successfully." << std::endl;
    return 0;
}
