from fastapi import APIRouter
from backend.api.events import events_db

router = APIRouter()

@router.get("/analytics")
def get_analytics():
    all_events = events_db.get_all()
    total = len(all_events)
    
    if total == 0:
        return {
            "total_detections": 0,
            "avg_risk_score": 0,
            "high_priority_count": 0,
            "resolved_count": 0
        }
        
    avg_risk = sum(e.risk_score for e in all_events) / total
    
    high_priority = sum(1 for e in all_events if e.risk_level in ["HIGH", "CRITICAL"])
    resolved = sum(1 for e in all_events if e.status == "RESOLVED")
    
    # Just mock MTTR and shift efficiency for the demo, since we don't have historical data
    return {
        "total_detections": total,
        "avg_risk_score": round(avg_risk, 1),
        "high_priority_count": high_priority,
        "resolved_count": resolved,
        "mttr": "1m 45s",
        "uptime": "99.99%"
    }
