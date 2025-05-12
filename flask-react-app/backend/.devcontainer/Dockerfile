FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV SHELL=/bin/bash
ENV LD_PRELOAD=/lib/x86_64-linux-gnu/liblz4.so.1

# Update system and install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    libopencv-dev \
    libflann-dev \
    openssl \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    wget \
    net-tools \
    ca-certificates \
    gcc \
    g++ \
    cmake \
    make \
    libglfw3-dev \
    libgtk-3-dev \
    libssl-dev \
    pkg-config \
    apt-get clean

# Upgrade pip before installing Python dependencies
RUN python3 -m pip install --upgrade pip

# Install required Python packages
RUN python3 -m pip install --no-cache-dir wheel Cython opencv-python opencv-contrib-python MechEyeAPI

# Copy and install Mech-Eye API
COPY ./MecheyePackage/mecheyeinstall/Mech-Eye_API_2.5.0_amd64.deb /tmp/
RUN dpkg -i /tmp/Mech-Eye_API_2.5.0_amd64.deb || apt-get install -f -y

# Copy application code and requirements.txt
WORKDIR /app
COPY . .

# Install Python dependencies from requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Start the application
CMD ["python3", "run.py"]