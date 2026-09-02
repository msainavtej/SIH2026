import sqlite3
import json
import threading
from datetime import datetime
from pydantic import ValidationError
from backend.schemas.events import EventSchema
import os

os.makedirs('storage', exist_ok=True)

class SQLiteEventStore:
    def __init__(self, db_path='storage/events.db'):
        self._lock = threading.RLock()
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()
        self._cache = self._load_all() # Load to memory for quick reads

    def _init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                camera_id TEXT,
                timestamp TEXT,
                object_type TEXT,
                track_id TEXT,
                risk_level TEXT,
                risk_score REAL,
                status TEXT,
                incident_id TEXT,
                data TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                timestamp TEXT,
                operator TEXT,
                action TEXT,
                reason TEXT,
                notes TEXT
            )
        ''')
        # Migrate schema if incident_id is missing from preexisting table
        self.cursor.execute("PRAGMA table_info(events)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if "incident_id" not in columns:
            self.cursor.execute("ALTER TABLE events ADD COLUMN incident_id TEXT")

        # Create indices for fast lookup
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_event_id ON events (event_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_incident_id ON events (incident_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_track_id ON events (track_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_event_id ON audit_logs (event_id)')
        self.conn.commit()

    def log_audit(self, event_id: str, operator: str, action: str, reason: str = "", notes: str = ""):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO audit_logs (event_id, timestamp, operator, action, reason, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_id, datetime.utcnow().isoformat(), operator, action, reason, notes))
            self.conn.commit()
        
    def get_audit_logs(self):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id, event_id, timestamp, operator, action, reason, notes FROM audit_logs ORDER BY timestamp DESC')
            rows = cursor.fetchall()
            return [{"id": r[0], "event_id": r[1], "timestamp": r[2], "operator": r[3], "action": r[4], "reason": r[5], "notes": r[6]} for r in rows]

    def clear_audit_logs(self):
        with self._lock:
            self.conn.execute('DELETE FROM audit_logs')
            self.conn.commit()
            self.log_audit("SYSTEM", "ADMIN", "LOGS_CLEARED", "User cleared audit logs to free up memory", "All previous logs deleted")

    def delete_evidence_files(self, event_id: str):
        with self._lock:
            event = next((e for e in self._cache if e.event_id == event_id), None)
            if not event: return False
            
            # Physically delete the mock evidence file if it exists
            if event.evidence_path and os.path.exists(event.evidence_path):
                try:
                    os.remove(event.evidence_path)
                except Exception as e:
                    print(f"Failed to delete evidence file {event.evidence_path}: {e}")
                    
            event.evidence_path = None
            self.append(event) # Resave event
            return True

    def _load_all(self):
        self.cursor.execute('SELECT data FROM events')
        rows = self.cursor.fetchall()
        loaded = []
        for row in rows:
            try:
                if hasattr(EventSchema, 'model_validate_json'):
                    loaded.append(EventSchema.model_validate_json(row[0]))
                else:
                    loaded.append(EventSchema.parse_raw(row[0]))
            except ValidationError:
                pass
        return loaded

    def __iter__(self):
        with self._lock:
            return iter(list(self._cache))

    def __len__(self):
        with self._lock:
            return len(self._cache)

    def remove(self, event):
        with self._lock:
            self._cache = [e for e in self._cache if e.event_id != event.event_id]
            self.conn.execute('DELETE FROM events WHERE event_id = ?', (event.event_id,))
            self.conn.commit()

    def append(self, event: EventSchema):
        with self._lock:
            # Update cache
            existing = [i for i, e in enumerate(self._cache) if e.event_id == event.event_id]
            if existing:
                self._cache[existing[0]] = event
            else:
                self._cache.append(event)
                
            # Update DB
            incident_id = getattr(event, 'incident_id', None)
            event_json = event.model_dump_json() if hasattr(event, 'model_dump_json') else event.json()
            self.conn.execute('''
                INSERT OR REPLACE INTO events 
                (event_id, camera_id, timestamp, object_type, track_id, risk_level, risk_score, status, incident_id, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.camera_id, str(event.timestamp), event.object_type,
                event.track_id, event.risk_level, event.risk_score, event.status, incident_id, event_json
            ))
            self.conn.commit()
        
    def get_all(self):
        with self._lock:
            return list(self._cache)

    def get_by_incident_id(self, incident_id: str):
        with self._lock:
            return [e for e in self._cache if getattr(e, 'incident_id', None) == incident_id]

    def get_by_event_id(self, event_id: str):
        with self._lock:
            return next((e for e in self._cache if e.event_id == event_id), None)

    def update_event_status(self, event_id: str, updates: dict):
        with self._lock:
            # Apply updates to the event object
            for event in self._cache:
                if event.event_id == event_id:
                    for k, v in updates.items():
                        setattr(event, k, v)
                    self.append(event) # re-save
                    return True
            return False

    def factory_reset(self):
        with self._lock:
            # Delete ALL physical files in storage
            storage_dir = "storage/evidence"
            if os.path.exists(storage_dir):
                import shutil
                shutil.rmtree(storage_dir)
                os.makedirs(storage_dir)
                
            # Clear DB
            self.conn.execute('DELETE FROM events')
            self.conn.execute('DELETE FROM audit_logs')
            self.conn.commit()
            # Clear in-memory cache
            self._cache = []

# Global instance
events_db = SQLiteEventStore()
