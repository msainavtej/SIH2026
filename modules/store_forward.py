import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "border_x_edge.db"

class StoreForwardQueue:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    primary_camera TEXT,
                    threat_score INTEGER,
                    severity TEXT,
                    rationale TEXT,
                    payload_json TEXT,
                    sync_status TEXT,
                    acknowledged_by TEXT
                )
            """)
            conn.commit()

    def enqueue_incident(self, incident_dict, is_online=False):
        """Saves incident locally at the edge with appropriate sync status."""
        sync_status = "SYNCED_CENTRAL" if is_online else "QUEUED_LOCAL"
        incident_dict["sync_status"] = sync_status

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO incidents 
                (incident_id, timestamp, primary_camera, threat_score, severity, rationale, payload_json, sync_status, acknowledged_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_dict["incident_id"],
                incident_dict["timestamp"],
                incident_dict["primary_camera"],
                incident_dict["threat_score"],
                incident_dict["severity"],
                incident_dict["rationale"],
                json.dumps(incident_dict),
                sync_status,
                incident_dict.get("acknowledged_by")
            ))
            conn.commit()
        return incident_dict

    def sync_pending_queue(self):
        """Simulates central command synchronization for queued local events."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT incident_id, payload_json FROM incidents WHERE sync_status = 'QUEUED_LOCAL'")
            rows = cursor.fetchall()
            
            synced_ids = []
            for inc_id, payload in rows:
                # Upstream HTTP/MQTT webhook sync logic to CIBMS goes here
                synced_ids.append(inc_id)

            cursor.execute("UPDATE incidents SET sync_status = 'SYNCED_CENTRAL' WHERE sync_status = 'QUEUED_LOCAL'")
            conn.commit()
            return len(synced_ids)

    def acknowledge_incident(self, incident_id, operator_id):
        """Updates mandatory human-in-the-loop audit log."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE incidents 
                SET acknowledged_by = ? 
                WHERE incident_id = ?
            """, (operator_id, incident_id))
            conn.commit()

    def get_latest_incidents(self, limit=5):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT incident_id, timestamp, threat_score, severity, rationale, sync_status, acknowledged_by 
                FROM incidents 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()