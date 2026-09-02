from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime

class TrackedObject(BaseModel):
    track_id: str
    object_type: str
    confidence: float
    bbox: List[int] = Field(description="Bounding box [x1, y1, x2, y2]")

class EventSchema(BaseModel):
    event_id: str
    camera_id: str
    timestamp: datetime
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "ACTIVE" # CANDIDATE, ACTIVE, RESOLVED, DISMISSED
    track_id: str
    object_type: str
    confidence: float
    plate: Optional[str] = None
    plate_confidence: Optional[float] = None
    plate_observations: Optional[int] = 0
    zone: Optional[str] = None
    direction: Optional[str] = None
    dwell_seconds: Optional[int] = 0
    has_face: Optional[bool] = False
    face_score: Optional[int] = None
    face_category: Optional[str] = None
    risk_score: int = Field(default=0, ge=0, le=100)
    max_risk_score: int = Field(default=0, ge=0, le=100)
    risk_level: str
    reasons: List[str]
    score_breakdown: Optional[dict] = None
    snapshot_path: Optional[str] = None
    evidence_path: Optional[str] = None
    is_held: bool = False

    # Cross-camera spatial-temporal correlation extensions
    incident_id: Optional[str] = None
    correlation_confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None
    correlated_with_track: Optional[str] = None
    correlated_with_camera: Optional[str] = None
    transit_time_seconds: Optional[float] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "EVT-20260824-0001",
                "camera_id": "CAM01",
                "timestamp": "2026-08-24T02:17:43Z",
                "track_id": "P27",
                "object_type": "person",
                "confidence": 0.91,
                "zone": "RED-03",
                "direction": "toward_border",
                "dwell_seconds": 42,
                "risk_score": 94,
                "risk_level": "HIGH",
                "reasons": [
                    "restricted_zone",
                    "night_movement",
                    "toward_border",
                    "loitering"
                ],
                "snapshot_path": "/storage/snapshots/CAM01/EVT-20260824-0001.jpg",
                "evidence_path": "/storage/events/CAM01/EVT-20260824-0001.mp4",
                "incident_id": "INC-20260824-0001",
                "correlation_confidence": "HIGH",
                "correlated_with_track": "CAM02-P28",
                "correlated_with_camera": "CAM02",
                "transit_time_seconds": 5.4
            }
        }
    )
