# ==========================================
# REENACTMENT PODCAST BACKEND (Fast Mode)
# ==========================================
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydub import AudioSegment
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil

app = FastAPI(title="Podcast Generator API (Fast Mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def normalize_audio(audio_segment: AudioSegment, target_dBFS=-20.0):
    """Gleicht die Lautstärke der Tonspur an (Normalisierung)."""
    change_in_dBFS = target_dBFS - audio_segment.dBFS
    return audio_segment.apply_gain(change_in_dBFS)

@app.post("/generate-podcast/")
async def create_podcast(
    intro: UploadFile = File(...),
    outro: UploadFile = File(...),
    segments: list[UploadFile] = File(...)
):
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "final_podcast.mp3")

    try:
        # --- SCHRITT 1: Intro laden ---
        intro_path = os.path.join(temp_dir, intro.filename)
        with open(intro_path, "wb") as buffer:
            shutil.copyfileobj(intro.file, buffer)
        final_audio = AudioSegment.from_file(intro_path)
        
        # --- SCHRITT 2: Segmente sortieren und normalisieren ---
        sorted_segments = sorted(segments, key=lambda x: x.filename)
        for segment in sorted_segments:
            seg_path = os.path.join(temp_dir, segment.filename)
            with open(seg_path, "wb") as buffer:
                shutil.copyfileobj(segment.file, buffer)
                
            raw_audio = AudioSegment.from_file(seg_path)
            
            # KOMPLEXITÄTSREDUKTION: Nur noch Normalisierung, kein Pausenschnitt!
            normalized_audio = normalize_audio(raw_audio)
            final_audio += normalized_audio
            
        # --- SCHRITT 3: Outro anhängen ---
        outro_path = os.path.join(temp_dir, outro.filename)
        with open(outro_path, "wb") as buffer:
            shutil.copyfileobj(outro.file, buffer)
        final_audio += AudioSegment.from_file(outro_path)
        
        # --- SCHRITT 4: Export als MP3 ---
        final_audio.export(output_path, format="mp3", bitrate="192k")
        
        return FileResponse(
            path=output_path, 
            filename="Reenactment_Podcast_Episode.mp3", 
            media_type="audio/mpeg"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Verarbeitung: {str(e)}")
