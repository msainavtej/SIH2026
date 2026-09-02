import os
import threading
import time
from backend.api.events_store import events_db
from datetime import datetime

class StorageManager:
    def __init__(self, storage_dir="storage/evidence", max_budget_mb=50):
        self.storage_dir = storage_dir
        self.max_budget_bytes = max_budget_mb * 1024 * 1024
        self.is_running = False
        os.makedirs(self.storage_dir, exist_ok=True)
        self.audit_orphans()
        
    def audit_orphans(self, auto_delete=False):
        """Identify files in storage without a corresponding event in the database."""
        if not os.path.exists(self.storage_dir): return
        
        valid_paths = set(os.path.normpath(e.evidence_path) for e in events_db.get_all() if e.evidence_path)
        orphans = []
        
        for f in os.listdir(self.storage_dir):
            if f.endswith(".mp4"):
                fp = os.path.normpath(os.path.join(self.storage_dir, f))
                if fp not in valid_paths:
                    orphans.append(fp)
                    
        if orphans:
            print(f"[StorageManager] WARNING: Found {len(orphans)} orphaned evidence files consuming disk space.")
            for orphan in orphans:
                print(f"  - Orphan: {orphan}")
                events_db.log_audit(os.path.basename(orphan), "SYSTEM_STARTUP", "ORPHAN_DETECTED", f"File {orphan} has no matching event in database")
                if auto_delete:
                    os.remove(orphan)
                    print(f"    Deleted {orphan}")
        
    def save_snapshot(self, event_id: str, frame):
        """Saves a real image snapshot for the event."""
        used = self.get_dir_size()
        if used > self.max_budget_bytes:
            warning = f"STORAGE FULL: Writing evidence for {event_id} while {used / 1024 / 1024:.1f}MB / {self.max_budget_bytes / 1024 / 1024:.1f}MB used. Budget exceeded."
            print(f"[StorageManager] WARNING: {warning}")
            events_db.log_audit(event_id, "SYSTEM_STORAGE", "BUDGET_EXCEEDED", warning, f"Used {used} bytes, budget {self.max_budget_bytes} bytes")
        filepath = os.path.join(self.storage_dir, f"{event_id}.jpg")
        import cv2
        cv2.imwrite(filepath, frame)
        return filepath

    def get_dir_size(self):
        total_size = 0
        for dirpath, _, filenames in os.walk(self.storage_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size
        
    def start_governor(self):
        self.is_running = True
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()
        
    def stop(self):
        self.is_running = False
        
    def _run_loop(self):
        while self.is_running:
            try:
                self.enforce_retention()
            except Exception as e:
                print(f"Storage governor error: {e}")
            time.sleep(10) # check every 10 seconds
            
    def enforce_retention(self):
        used_bytes = self.get_dir_size()
        if used_bytes > self.max_budget_bytes * 0.9: # 90% full
            print(f"[StorageManager] Usage {used_bytes}/{self.max_budget_bytes} bytes. Running auto-purge.")
            
            # Fetch events with evidence
            events_with_evidence = [e for e in events_db.get_all() if e.evidence_path and os.path.exists(e.evidence_path)]
            
            # Filter out HELD events
            purge_eligible = [e for e in events_with_evidence if not getattr(e, 'is_held', False)]
            
            # Sort: Routine (LOW/NORMAL/DISMISSED) first, then older first
            def get_tier_priority(event):
                if event.status == "DISMISSED": return 0 # Purge immediately
                if event.risk_level in ["LOW", "NORMAL"]: return 1
                if event.risk_level == "MEDIUM": return 2
                return 3 # HIGH/CRITICAL
                
            purge_eligible.sort(key=lambda x: (get_tier_priority(x), x.timestamp))
            
            for event in purge_eligible:
                if used_bytes < self.max_budget_bytes * 0.7: # target 70%
                    break
                    
                file_size = os.path.getsize(event.evidence_path)
                events_db.delete_evidence_files(event.event_id)
                events_db.log_audit(event.event_id, "SYSTEM_AUTO_PURGE", "AUTO_PURGED", f"Disk cleanup: Tier {get_tier_priority(event)}", f"Freed {file_size} bytes")
                used_bytes -= file_size
                print(f"[StorageManager] Purged {event.event_id}")

storage_manager = StorageManager(max_budget_mb=100) # 100MB demo cap
