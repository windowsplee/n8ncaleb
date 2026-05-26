FROM python:3.10-slim

# Install FFmpeg, fontconfig, and Korean fonts (Nanum)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    fontconfig \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# Install python libraries
RUN pip install --no-cache-dir \
    edge-tts \
    moviepy \
    requests

WORKDIR /app

# Copy renderer script
COPY render_shorts.py .

CMD ["python", "render_shorts.py"]
