# ==============================================================================
# Production Dockerfile for Robotics Control & Data Processing API
# ==============================================================================

FROM python:3.10-slim

# ==============================================================================
# Environment Configuration
# ==============================================================================
ENV DEBIAN_FRONTEND=noninteractive \
    SHELL=/bin/bash \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LD_PRELOAD=/lib/x86_64-linux-gnu/liblz4.so.1 \
    PYTHONPATH=/usr/local/lib/python3.10/site-packages

# ==============================================================================
# System Dependencies Installation
# ==============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python development
    python3-dev \
    # OpenCV dependencies
    libopencv-dev \
    libglfw3-dev \
    libgtk-3-dev \
    # Build tools
    gcc \
    g++ \
    cmake \
    make \
    pkg-config \
    # System libraries
    libflann-dev \
    libssl-dev \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    # Utilities
    wget \
    net-tools \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ==============================================================================
# Python Dependencies Installation
# ==============================================================================

RUN python3 -m pip install --upgrade pip wheel setuptools


# Install system-level Python packages that require compilation
RUN python3 -m pip install --no-cache-dir \
    Cython \
    numpy \
    opencv-python \
    opencv-contrib-python

# ==============================================================================
# Mech-Eye API Installation
# ==============================================================================
# Copy and install Mech-Eye API package
COPY ./MecheyePackage/mecheyeinstall/Mech-Eye_API_2.5.0_amd64.deb /tmp/
RUN dpkg -i /tmp/Mech-Eye_API_2.5.0_amd64.deb || \
    (apt-get update && apt-get install -f -y) && \
    rm -f /tmp/Mech-Eye_API_2.5.0_amd64.deb

# ==============================================================================
# Application Setup
# ==============================================================================
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python application dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Install additional required packages
RUN python3 -m pip install --no-cache-dir \
    MechEyeAPI \
    websocket-client \
    apscheduler \
    eventlet

# ==============================================================================
# Custom Package Installation
# ==============================================================================
# Create fair_api directory and copy shared object
RUN mkdir -p /usr/local/lib/python3.10/site-packages/fair_api
COPY ./MecheyePackage/fair_api/Robot.cpython-310-x86_64-linux-gnu.so \
     /usr/local/lib/python3.10/site-packages/fair_api/

# Replace profiler_utils.py with custom version
RUN rm -f /usr/local/lib/python3.10/site-packages/mecheye/profiler_utils.py
COPY ./MecheyePackage/profiler_utils.py \
     /usr/local/lib/python3.10/site-packages/mecheye/

# ==============================================================================
# Application Code
# ==============================================================================
RUN pip install appwrite
COPY . .

EXPOSE 5000

# ==============================================================================
# Application Startup
# ==============================================================================
# Set default command
CMD ["python3", "run.py"]