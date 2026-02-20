# ==========================================
# REENACTMENT PODCAST BACKEND (Low Memory Mode)
# ==========================================
# Nutzt direkt FFmpeg auf der Festplatte, um RAM-Abstürze
# auf kostenlosen Servern (512MB Limit) zu verhindern.

import subprocess
import tempfile
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Podcast Generator API (Low Memory)")

# Erlaubt dem Frontend, mit diesem Backend zu kommunizieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def normalize_audio_ffmpeg(input_path, output_path):
    """
    Normalisiert die Lautstärke ressourcenschonend direkt auf der Festplatte.
    Verhindert, dass der Arbeitsspeicher (RAM) belastet wird.
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter:a", "loudnorm",
        "-c:a", "libmp3lame", "-b:a", "128k",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

@app.post("/generate-podcast/")
async def create_podcast(
    intro: UploadFile = File(...),
    outro: UploadFile = File(...),
    segments: list[UploadFile] = File(...)
):
    # Erstellt einen sicheren, temporären Ordner auf der Festplatte
    temp_dir = tempfile.mkdtemp()
    final_output = os.path.join(temp_dir, "final_podcast.mp3")
    concat_list_path = os.path.join(temp_dir, "concat.txt")

    try:
        processed_files = []

        # Hilfs-Routine: Datei speichern und ohne RAM-Belastung normalisieren
        def process_file(upload_file, prefix):
            raw_path = os.path.join(temp_dir, f"raw_{prefix}_{upload_file.filename}")
            norm_path = os.path.join(temp_dir, f"norm_{prefix}.mp3")
            
            with open(raw_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
                
            normalize_audio_ffmpeg(raw_path, norm_path)
            return norm_path

        # --- SCHRITT 1 & 2: Jingles & Segmente laden und anpassen ---
        processed_files.append(process_file(intro, "intro"))
        
        # Chronologische Sortierung der WhatsApp-Dateien
        sorted_segments = sorted(segments, key=lambda x: x.filename)
        for idx, seg in enumerate(sorted_segments):
            processed_files.append(process_file(seg, f"seg_{idx}"))
            
        processed_files.append(process_file(outro, "outro"))

        # --- SCHRITT 3: Effizientes Zusammenfügen (Concat ohne Re-Encoding) ---
        # Erstellt eine Textdatei mit allen Schnipseln als Bauplan für FFmpeg
        with open(concat_list_path, "w") as f:
            for pf in processed_files:
                safe_path = pf.replace('\\', '/')
                f.write(f"file '{safe_path}'\n")

        # FFmpeg klebt die Dateien in Sekunden auf der Festplatte zusammen (nahezu 0 RAM!)
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy", 
            final_output
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Liefert die fertige Datei an die App zurück
        return FileResponse(
            path=final_output, 
            filename="Reenactment_Podcast_Episode.mp3", 
            media_type="audio/mpeg"
        )

    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Audio-Motor (FFmpeg) Fehler. Datei eventuell beschädigt.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Systemfehler: {str(e)}")
