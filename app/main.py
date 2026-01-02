from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import cv2
import uuid

# Handle both relative and absolute imports
try:
    from .model import process_image, process_video
except ImportError:
    from model import process_image, process_video

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "https://your-heroku-app.herokuapp.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for now, tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories for temporary storage
UPLOAD_DIR = "uploads"
RESULTS_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

@app.post("/api/predict/image")
async def predict_image_endpoint(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        annotated_img = process_image(contents)
        
        # Encode to JPEG to return directly
        _, img_encoded = cv2.imencode('.jpg', annotated_img)
        return Response(content=img_encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predict/video")
async def predict_video_endpoint(request: Request, file: UploadFile = File(...)):
    file_path = None
    try:
        # Save uploaded video
        file_ext = file.filename.split('.')[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process video
        output_filename = f"processed_{filename.replace(file_ext, 'mp4')}"
        output_path = os.path.join(RESULTS_DIR, output_filename)
        
        # We use a custom loop here to allow checking for disconnection
        # because process_video is blocking
        import anyio
        async def run_processing():
            return process_video(file_path, output_path, request=request)
            
        # Run in a threadpool to not block the main event loop
        # anyio/starlette background tasks or similar would also work
        await anyio.to_thread.run_sync(process_video, file_path, output_path, request)
        
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return FileResponse(output_path, media_type="video/mp4", filename=output_filename)
    except Exception as e:
        # Clean up on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# API to list sample images
@app.get("/api/samples/images")
def list_sample_images():
    images_dir = "images"
    if os.path.exists(images_dir):
        files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return {"files": sorted(files)}
    return {"files": []}

# API to list sample videos
@app.get("/api/samples/videos")
def list_sample_videos():
    videos_dir = "videos"
    if os.path.exists(videos_dir):
        files = [f for f in os.listdir(videos_dir) if f.lower().endswith(('.mp4', '.avi', '.mov'))]
        return {"files": sorted(files)}
    return {"files": []}

# API to process sample image by name
@app.get("/api/predict/sample/image/{filename}")
async def predict_sample_image(filename: str):
    try:
        file_path = os.path.join("images", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(file_path, "rb") as f:
            contents = f.read()
        
        annotated_img = process_image(contents)
        _, img_encoded = cv2.imencode('.jpg', annotated_img)
        return Response(content=img_encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API to process sample video by name
@app.post("/api/predict/sample/video/{filename}")
async def predict_sample_video(request: Request, filename: str):
    try:
        file_path = os.path.join("videos", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        output_filename = f"processed_{filename}"
        output_path = os.path.join(RESULTS_DIR, output_filename)
        
        import anyio
        await anyio.to_thread.run_sync(process_video, file_path, output_path, request)
        
        return FileResponse(output_path, media_type="video/mp4", filename=output_filename)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Serve sample files
app.mount("/samples/images", StaticFiles(directory="images"), name="sample_images")
app.mount("/samples/videos", StaticFiles(directory="videos"), name="sample_videos")

@app.get("/health")
def health_check():
    return {"status": "ok", "model": "YOLOv11-pose"}

# Serve static files (React build) - MUST BE LAST
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

