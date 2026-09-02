from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.events import EventSchema
from backend.api.events_store import events_db

router = APIRouter()

@router.get("/events", response_model=List[EventSchema])
def get_all_events():
    return events_db.get_all()

@router.post("/events")
def create_event(event: EventSchema):
    events_db.append(event)
    return {"status": "created", "id": event.event_id}

from fastapi.responses import FileResponse
import os

@router.get("/events/{event_id}/evidence")
def get_event_evidence(event_id: str):
    for e in events_db:
        if e.event_id == event_id:
            if e.evidence_path and os.path.exists(e.evidence_path):
                return FileResponse(e.evidence_path)
            break
    raise HTTPException(status_code=404, detail="Evidence not found")

@router.post("/events/{event_id}/escalate")
def escalate_event(event_id: str):
    for e in events_db:
        if e.event_id == event_id:
            e.risk_level = "CRITICAL"
            e.risk_score = 100
            e.reasons.append("Manually escalated by operator")
            events_db.append(e) # Save back to DB
            return {"status": "escalated"}
    raise HTTPException(status_code=404, detail="Event not found")

from pydantic import BaseModel
class ResolveRequest(BaseModel):
    operator: str = "admin123"
    reason: str = "false_positive"
    notes: str = ""

@router.post("/events/{event_id}/resolve")
def resolve_event(event_id: str, req: ResolveRequest):
    for e in events_db:
        if e.event_id == event_id:
            e.status = "DISMISSED"
            e.reasons.append(f"Dismissed: {req.reason}")
            events_db.append(e) # Save back to DB
            
            # 1. Delete the raw footage (storage drop tier logic)
            events_db.delete_evidence_files(event_id)
            
            # 2. Permanent Audit Trail
            events_db.log_audit(event_id, req.operator, 'REVIEWED', req.reason, req.notes)
            
            return {"status": "resolved"}
    raise HTTPException(status_code=404, detail="Event not found")

class BulkReviewRequest(BaseModel):
    operator: str = "admin123"
    event_type_filter: str
    reason: str = "duplicate"
    
@router.post("/events/bulk-review")
def bulk_review(req: BulkReviewRequest):
    count = 0
    for e in events_db:
        if e.status == "ACTIVE" and (req.event_type_filter in e.reasons or req.event_type_filter == e.object_type or e.risk_level == req.event_type_filter):
            e.status = "DISMISSED"
            events_db.append(e)
            events_db.delete_evidence_files(e.event_id)
            events_db.log_audit(e.event_id, req.operator, 'REVIEWED_BULK', req.reason, f"Bulk match: {req.event_type_filter}")
            count += 1
    return {"status": "success", "count": count}


