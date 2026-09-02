from fastapi import APIRouter, HTTPException
from backend.storage_manager import storage_manager
from backend.api.events_store import events_db
from pydantic import BaseModel

router = APIRouter()

@router.get("/storage/health")
def get_storage_health():
    used = storage_manager.get_dir_size()
    budget = storage_manager.max_budget_bytes
    
    events = events_db.get_all()
    
    routine = sum(1 for e in events if e.evidence_path and e.risk_level in ["LOW", "NORMAL"] and not e.is_held)
    confirmed = sum(1 for e in events if e.evidence_path and e.risk_level in ["MEDIUM", "HIGH", "CRITICAL"] and not e.is_held)
    held = sum(1 for e in events if e.evidence_path and e.is_held)
    
    pct = round(used / budget * 100, 1) if budget > 0 else 0
    
    # Detect saturated state: over budget with nothing left to purge
    storage_warning = None
    if pct > 90:
        import os
        purgeable = sum(1 for e in events if e.evidence_path and not e.is_held
                        and e.evidence_path and os.path.exists(e.evidence_path))
        if purgeable == 0:
            storage_warning = f"STORAGE FULL — {pct}% used. All evidence is Held or Critical. New recordings may exceed budget. Release holds or increase budget."
        else:
            storage_warning = f"STORAGE WARNING — {pct}% used. Auto-purge active."
    
    return {
        "used_bytes": used,
        "budget_bytes": budget,
        "percentage": pct,
        "storage_warning": storage_warning,
        "tier_breakdown": {
            "routine": routine,
            "confirmed": confirmed,
            "held": held
        }
    }

class HoldRequest(BaseModel):
    operator: str = "admin123"
    reason: str = "Investigation"

@router.post("/events/{event_id}/hold")
def hold_event(event_id: str, req: HoldRequest):
    target = events_db.get_by_event_id(event_id)
    if not target:
        raise HTTPException(status_code=404, detail="Event not found")
        
    events_to_hold = [target]
    incident_id = getattr(target, 'incident_id', None)
    if incident_id:
        events_to_hold = events_db.get_by_incident_id(incident_id)
        
    for e in events_to_hold:
        e.is_held = True
        events_db.append(e)
        events_db.log_audit(e.event_id, req.operator, "HELD", req.reason, "Evidence marked for indefinite retention")
        
    return {"status": "held"}

@router.get("/audit_logs")
def get_audit_logs():
    return events_db.get_audit_logs()

@router.delete("/audit_logs")
def clear_all_data():
    events_db.factory_reset()
    return {"status": "cleared"}
