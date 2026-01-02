import cv2
import numpy as np
import os
# Initialize model (lazy loading or global)
model = None

def get_model():
    global model
    if model is None:
        from ultralytics import YOLO
        import torch
        
        # Check for GPU availability
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        
        if device == 'cuda':
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        
        print("Loading YOLOv11-pose model (medium - higher accuracy)...")
        # Using medium model for better accuracy
        # Options: yolo11n-pose (fastest), yolo11s-pose, yolo11m-pose (balanced), yolo11l-pose, yolo11x-pose (most accurate)
        model = YOLO('yolo11m-pose.pt')
        model.to(device)
        print("Model loaded successfully.")
    return model 

def process_image(image_bytes: bytes) -> np.ndarray:
    """
    Process an image with YOLOv11-pose and return the annotated image.
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Inference
    yolo_model = get_model()
    results = yolo_model(img)
    
    # Plot results with theme colors
    # Primary (Indigo): #6366F1 -> BGR (241, 102, 99)
    # Accent (Cyan): #06B6D4 -> BGR (212, 182, 6)
    # Hide boxes and labels for a professional pose-only look
    annotated_frame = results[0].plot(
        boxes=False, 
        labels=False, 
        conf=False,
        kpt_radius=3,
        line_width=4  # Very thick lines for visibility
    )
    
    return annotated_frame

def process_video(video_path: str, output_path: str, request=None):
    """
    Process a video, save the pose-estimated video to output_path.
    """
    yolo_model = get_model()
    
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Ensure fps is valid
    if fps == 0 or fps is None:
        fps = 30.0
    
    # Use mp4v for initial write (reliable across platforms, built-in to OpenCV)
    # We will convert to H.264 (avc1) later using ffmpeg for browser compatibility
    print(f"Creating video writer for {output_path} with mp4v codec...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print("Warning: mp4v failed, trying XVID...")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        cap.release()
        raise Exception(f"Failed to create video writer for {output_path}. Tried mp4v and XVID.")
    
    print(f"Video writer opened successfully: {out.isOpened()}")
    print(f"Starting frame processing (Total estimated: {int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0 else 'unknown'})...")
    
    import time
    start_time = time.time()
    TIMEOUT_LIMIT = 60 # 1 minute limit as requested
    
    frame_count = 0
    try:
        while cap.isOpened():
            # 1. Check for timeout
            if time.time() - start_time > TIMEOUT_LIMIT:
                print(f"Timeout reached ({TIMEOUT_LIMIT}s). Stopping processing.")
                break
            
            # 2. Check for client disconnection (refresh/tab close)
            # Simplified check - just verify request object exists
            # The actual disconnection will be caught by the HTTP layer
                    
            ret, frame = cap.read()
            if not ret:
                print("End of video stream or error reading frame.")
                break
                
            # Use tracking for consistent IDs across frames (persist=True keeps track IDs between frames)
            # Track can be slow on CPU
            results = yolo_model.track(frame, persist=True, verbose=False)
            
            if len(results) > 0:
                annotated_frame = results[0].plot(
                    boxes=False, 
                    labels=False, 
                    conf=False,
                    kpt_radius=5,
                    line_width=9  # Very thick lines for visibility
                )
                out.write(annotated_frame)
            else:
                out.write(frame) # Write original if no results (shouldn't happen with results[0] usually)

            frame_count += 1
            if frame_count % 10 == 0:
                print(f"Processed {frame_count} frames...")
    except Exception as e:
        print(f"Error during video processing at frame {frame_count}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()
        out.release()
    
    print(f"Finished processing. Total frames: {frame_count}. Saved to {output_path}")
    
    # Convert to browser-compatible format using ffmpeg if available
    import subprocess
    import shutil
    
    if shutil.which('ffmpeg'):
        try:
            temp_path = output_path.replace('.mp4', '_temp.mp4')
            os.rename(output_path, temp_path)
            
            # Convert to H.264 (H.264/AVC) with YUV420P pixel format (crucial for browsers)
            # Use 'aac' audio if it exists, otherwise skip audio
            print(f"Converting {temp_path} to browser-compatible H.264...")
            cmd = [
                'ffmpeg', '-i', temp_path,
                '-c:v', 'libx264', 
                '-preset', 'ultrafast', # Speed up for testing
                '-crf', '28', # Slightly lower quality for much faster processing
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-y', output_path
            ]
            
            # Run without capture_output to see ffmpeg output in terminal if possible, 
            # or capture it to debug
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg Error: {result.stderr}")
                # Fallback: copy original if conversion failed
                shutil.copy2(temp_path, output_path)
            else:
                print(f"Video converted successfully: {output_path}")
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"FFmpeg conversion process failed: {e}")
            if os.path.exists(temp_path) and not os.path.exists(output_path):
                os.rename(temp_path, output_path)
    
    return output_path
