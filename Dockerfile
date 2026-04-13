# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies required for OpenCV (libGL)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Set workspace directory
WORKDIR /home/user/app

# Copy the requirements file into the container
COPY --chown=user:user requirements.txt .

# Install dependencies (running as root to install system-wide, or we can just switch to user)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=user:user . .

# Switch to the non-root user (Mandatory for Hugging Face Spaces)
USER user

# Expose the port Hugging Face expects
EXPOSE 7860

# Command to run the application using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "-w", "2", "--timeout", "120", "run:app"]
