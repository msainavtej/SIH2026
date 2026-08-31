import os
import sys
from pathlib import Path

# Force the project root (fin_proj) into the Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr
import cv2
import tempfile
import json
import sqlite3
from main import BorderXPipeline
from modules.gateway import StreamGateway
from config.settings import ZONES

pipeline = BorderXPipeline()

def run_border_pipeline(video_path, is_night, is_cross_cam, is_online):
    if not video_path:
        return None, "Please upload a video stream first.", []

    gateway = StreamGateway(video_path)
    if not gateway.start():
        return None, "Failed to read stream.", []

    cap = gateway.cap
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    
    out_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    latest_incident = None
    fence_y = int(ZONES["VIRTUAL_FENCE_LINE"][0][1] * h)
    correlated_cams = ["CAM_02"] if is_cross_cam else []

    for frame in gateway.get_frames():
        detections, incidents = pipeline.process_frame(
            frame, 
            is_night=is_night, 
            correlated_cameras=correlated_cams, 
            is_online=is_online
        )

        # Draw Perimeter Overlay
        cv2.line(frame, (0, fence_y), (w, fence_y), (0, 0, 255), 2)
        cv2.putText(frame, "INTERNATIONAL BORDER PERIMETER", (20, fence_y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw Bounding Boxes and Identity Telemetry
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            tid = det["track_id"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, det["foot_point"], 4, (0, 0, 255), -1)
            cv2.putText(frame, f"{det['class_name']} #{tid}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        if incidents:
            latest_incident = incidents[-1]

        writer.write(frame)

    writer.release()
    gateway.release()

    logs = pipeline.queue.get_latest_incidents(limit=5)
    telemetry_json = json.dumps(latest_incident or {"status": "NO_ACTIVE_BREACH"}, indent=2)
    return out_path, telemetry_json, logs

def trigger_sync():
    count = pipeline.queue.sync_pending_queue()
    logs = pipeline.queue.get_latest_incidents(limit=5)
    return f"Synced {count} queued incidents to central C2.", logs

def acknowledge_alert(incident_id, operator_id):
    if not incident_id or not operator_id:
        return "Incident ID and Operator ID required.", pipeline.queue.get_latest_incidents(limit=5)
    pipeline.queue.acknowledge_incident(incident_id.strip(), operator_id.strip())
    logs = pipeline.queue.get_latest_incidents(limit=5)
    return f"Incident {incident_id} acknowledged by {operator_id}.", logs

# Gradio Interface
with gr.Blocks(title="BORDER-X Operator Console") as demo:
    gr.Markdown("# 🛡️ BORDER-X | AI Border Incident Intelligence Layer")
    gr.Markdown("**Unified Edge Outpost Terminal** | PS 26187 Complete Pipeline")

    with gr.Row():
        with gr.Column(scale=1):
            video_input = gr.Video(label="Simulated CCTV Stream")
            night_mode = gr.Checkbox(label="Night Window (+20 Risk)", value=True)
            cross_cam = gr.Checkbox(label="Cross-Camera Confirmation (+15 Risk)", value=True)
            online_status = gr.Checkbox(label="Network Online (Store-and-Forward Active)", value=False)
            run_btn = gr.Button("▶ Ingest Stream & Run Pipeline", variant="primary")

        with gr.Column(scale=2):
            video_output = gr.Video(label="Processed Stream / Live Tracking")
            telemetry_code = gr.Code(label="Latest Incident Telemetry (JSON Contract)", language="json")

    gr.Markdown("---")
    gr.Markdown("### 🗄️ Edge Resilience, Store-and-Forward & Audit Logs")
    with gr.Row():
        with gr.Column(scale=2):
            incident_table = gr.Dataframe(
                headers=["Incident ID", "Timestamp", "Score", "Severity", "Rationale", "Sync Status", "Acknowledged By"],
                label="Local SQLite Outpost Incident Registry"
            )
        with gr.Column(scale=1):
            sync_btn = gr.Button("🔄 Reconnect & Sync Queue", variant="secondary")
            sync_status = gr.Textbox(label="Sync Output", interactive=False)
            
            gr.Markdown("#### Human-in-the-Loop Acknowledgment")
            ack_inc_id = gr.Textbox(label="Incident ID")
            ack_op_id = gr.Textbox(label="Operator ID")
            ack_btn = gr.Button("Acknowledge Incident", variant="stop")
            ack_status = gr.Textbox(label="Audit Status", interactive=False)

    run_btn.click(
        fn=run_border_pipeline,
        inputs=[video_input, night_mode, cross_cam, online_status],
        outputs=[video_output, telemetry_code, incident_table]
    )

    sync_btn.click(fn=trigger_sync, outputs=[sync_status, incident_table])
    ack_btn.click(fn=acknowledge_alert, inputs=[ack_inc_id, ack_op_id], outputs=[ack_status, incident_table])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)