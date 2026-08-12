# Use NVIDIA's official PyTorch / L4T base image for JetPack 6.x
FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.1-py3

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy project files into the container
COPY . .

# Expose Flask port
EXPOSE 5000

# Open a Bash terminal by default instead of running app.py
CMD ["/bin/bash"]
