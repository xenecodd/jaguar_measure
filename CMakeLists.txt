cmake_minimum_required(VERSION 3.10)  # Minimum CMake versiyonu
project(PointCloudTransformation)      # Proje adı

# C++ standardını belirleyin (C++11 veya daha yüksek bir sürüm kullanabilirsiniz)
set(CMAKE_CXX_STANDARD 11)

# PCL kütüphanesini bulun
find_package(PCL REQUIRED)

# Include dizinlerini ayarlayın
include_directories(${PCL_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})
add_definitions(${PCL_DEFINITIONS})

# İkili dosya olarak derlenecek kaynak dosyayı belirtin
add_executable(point_cloud_transform main.cpp)  # main.cpp, kaynak kod dosyanız

# PCL kütüphanelerini projeye bağlayın
target_link_libraries(point_cloud_transform ${PCL_LIBRARIES})
