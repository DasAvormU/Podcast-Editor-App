# Wir starten mit einem schlanken Basis-System
FROM python:3.9-slim

# Wir installieren den Audio-Motor FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Wir kopieren Ihren Code aus dem Canvas in den Container
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Der Startbefehl für den Webserver
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
