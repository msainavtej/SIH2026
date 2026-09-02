import cv2
from fastapi import APIRouter, HTTPException, UploadFile, File
import os
import shutil
from fastapi.responses import StreamingResponse
from backend.camera_manager import camera_manager

router = APIRouter()

@router.get("/cameras")
def get_cameras():
    return camera_manager.get_all_health()

def frame_generator(camera_id):
    while True:
        frame = camera_manager.get_latest_frame(camera_id)
        if frame is None:
            continue
            
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@router.get("/cameras/{camera_id}/stream")
def get_camera_stream(camera_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    return StreamingResponse(
        frame_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.post("/cameras/{camera_id}/reconnect")
def reconnect_camera(camera_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    cam = camera_manager.cameras[camera_id]
    if hasattr(cam, 'reconnect'):
        cam.reconnect()
        return {"status": "reconnecting"}
    return {"status": "not_supported"}

@router.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_manager.remove_camera(camera_id)
    return {"status": "deleted"}

@router.post("/cameras/{camera_id}/pause")
def pause_camera(camera_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_manager.pipelines[camera_id].is_paused = True
    return {"status": "paused"}

@router.post("/cameras/{camera_id}/play")
def play_camera(camera_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_manager.pipelines[camera_id].is_paused = False
    return {"status": "playing"}

from pydantic import BaseModel
from typing import List, Dict

class ZoneCreate(BaseModel):
    name: str
    polygon: List[Dict[str, float]]

@router.post("/cameras/{camera_id}/zones")
def add_camera_zone(camera_id: str, zone: ZoneCreate):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    pipeline = camera_manager.pipelines[camera_id]
    
    # Get current resolution to map percentages to absolute pixels
    frame = pipeline.current_frame
    if frame is not None:
        h, w = frame.shape[:2]
    else:
        h, w = 480, 640 # Fallback
        
    abs_polygon = []
    for pt in zone.polygon:
        abs_polygon.append([int(pt['px'] * w), int(pt['py'] * h)])
    
    zone_dict = {
        'id': zone.name,
        'type': 'restricted',
        'polygon': abs_polygon
    }
    
    pipeline.zone_manager.add_zone(zone_dict)
    return {"status": "added", "zone": zone.name}

@router.post("/cameras/upload")
async def upload_camera_video(file: UploadFile = File(...)):
    # Save the file
    upload_dir = "storage/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_filename = file.filename.replace(" ", "_")
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Add as a new camera
    cam_id = f"UPLOAD_{safe_filename.split('.')[0].upper()}"
    # Ensure it's unique if uploaded multiple times
    if cam_id in camera_manager.cameras:
        import time
        cam_id = f"{cam_id}_{int(time.time())}"
        
    camera_manager.add_camera(cid=cam_id, stype="file", url=file_path)
    
    return {"status": "uploaded", "camera_id": cam_id, "file_path": file_path}

@router.get("/cameras/{camera_id}/zones")
def get_camera_zones(camera_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    pipeline = camera_manager.pipelines[camera_id]
    
    frame = pipeline.current_frame
    h, w = 480, 640
    if frame is not None:
        h, w = frame.shape[:2]

    zones_list = []
    for z_id, z in pipeline.zone_manager.zones.items():
        pts = []
        for pt in z.polygon:
            x, y = pt[0]
            pts.append({"px": float(x) / w, "py": float(y) / h})
        zones_list.append({
            "id": z_id,
            "name": z_id,
            "type": z.zone_type,
            "polygon": pts
        })
    return zones_list

@router.delete("/cameras/{camera_id}/zones/{zone_id}")
def delete_camera_zone(camera_id: str, zone_id: str):
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    pipeline = camera_manager.pipelines[camera_id]
    if zone_id in pipeline.zone_manager.zones:
        del pipeline.zone_manager.zones[zone_id]
        return {"status": "deleted", "zone_id": zone_id}
    raise HTTPException(status_code=404, detail="Zone not found")
