FROM python:3.10

ENV DEBIAN_FRONTEND=noninteractive
ENV SHELL=/bin/bash

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
    pkg-config

RUN apt-get clean

# Upgrade pip before installing Python dependencies
RUN python3 -m pip install --upgrade pip

# Install required Python packages
RUN python3 -m pip install --no-cache-dir wheel Cython opencv-python opencv-contrib-python MechEyeAPI websocket-client

# Copy and install Mech-Eye API
COPY ./MecheyePackage/mecheyeinstall/Mech-Eye_API_2.5.0_amd64.deb /tmp/
RUN dpkg -i /tmp/Mech-Eye_API_2.5.0_amd64.deb || apt-get install -f -y

# Copy application code and requirements.txt
WORKDIR /backend
COPY . .

EXPOSE 5000

# Install Python dependencies from requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# RUN mkdir -p /usr/local/lib/python3.10/site-packages/fair_api
# RUN wget -P /usr/local/lib/python3.10/site-packages/fair_api/ https://raw.githubusercontent.com/FAIR-INNOVATION/fairino-python-sdk/a1451207e918c228b8933bf5d89bc58a05618103/Linux/fairino/Robot.cpython-310-x86_64-linux-gnu.so

# Copy the fair_api shared object file
RUN mkdir -p /usr/local/lib/python3.10/site-packages/fair_api
COPY ./MecheyePackage/fair_api/Robot.cpython-310-x86_64-linux-gnu.so /usr/local/lib/python3.10/site-packages/fair_api/

ENV LD_PRELOAD=/lib/x86_64-linux-gnu/liblz4.so.1
ENV PYTHONPATH=/usr/local/lib/python3.10/site-packages

RUN rm -rf /usr/local/lib/python3.10/site-packages/mecheye/profiler_utils.py
COPY ./MecheyePackage/profiler_utils.py /usr/local/lib/python3.10/site-packages/mecheye/

RUN python3 -m pip install --no-cache-dir apscheduler

# Start the application
CMD ["python3", "run.py"]