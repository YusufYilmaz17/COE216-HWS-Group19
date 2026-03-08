from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os
import uuid
import shutil
from processor import analyze_speech

app = FastAPI(title="Speech Analysis Dashboard")

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("temp", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only WAV files are supported.")
        
    file_id = str(uuid.uuid4())
    input_path = os.path.join("temp", f"{file_id}_input.wav")
    output_path = os.path.join("temp", f"{file_id}_processed.wav")
    
    # Save uploaded file
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        file.file.close()
        
    # Process file
    try:
        results = analyze_speech(input_path, output_path)
        results["processed_file_id"] = file_id
        
        # Clean up input file after processing
        if os.path.exists(input_path):
             os.remove(input_path)
             
        return results
    except Exception as e:
        # Clean up files on error
        if os.path.exists(input_path):
             os.remove(input_path)
        if os.path.exists(output_path):
             os.remove(output_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{file_id}")
async def download_processed_audio(file_id: str):
    output_path = os.path.join("temp", f"{file_id}_processed.wav")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="File not found. It may have expired.")
        
    return FileResponse(
        output_path, 
        media_type="audio/wav", 
        filename="processed_speech.wav",
        # Important: Don't remove the file here, it might be downloaded multiple times.
        # A real app would have a cron job or background task to clean up old files in temp/.
    )
