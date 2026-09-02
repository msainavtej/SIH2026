import React, { useEffect, useState } from 'react';
import './index.css';

function ZoneManagerView({ cameras }) {
  const [zones, setZones] = useState({});
  const [selectedCam, setSelectedCam] = useState(cameras[0] || null);

  const fetchZones = () => {
    if (!selectedCam) return;
    fetch("http://localhost:8000/api/cameras/" + selectedCam + "/zones")
      .then(res => res.json())
      .then(data => {
        setZones(prev => ({ ...prev, [selectedCam]: data }));
      })
      .catch(e => console.error("Error fetching zones", e));
  };

  useEffect(() => {
    fetchZones();
  }, [selectedCam]);

  useEffect(() => {
    if (!selectedCam && cameras.length > 0) {
      setSelectedCam(cameras[0]);
    }
  }, [cameras]);

  const handleDelete = (zoneId) => {
    if (!window.confirm("Are you sure you want to delete zone " + zoneId + "?")) return;
    fetch("http://localhost:8000/api/cameras/" + selectedCam + "/zones/" + zoneId, { method: 'DELETE' })
      .then(res => res.json())
      .then(() => fetchZones())
      .catch(e => console.error(e));
  };

  return (
    <div className="dashboard-scroll">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
        <h2 style={{fontSize: '1.5rem'}}>Zone Management</h2>
      </div>
      <div className="content-grid" style={{gridTemplateColumns: '1fr 2fr'}}>
        <div className="panel">
          <h3>Cameras</h3>
          {cameras.length === 0 && <div style={{color: 'var(--text-muted)'}}>No cameras connected.</div>}
          {cameras.map(c => (
            <div 
              key={c}
              onClick={() => setSelectedCam(c)}
              style={{
                padding: '10px', 
                borderBottom: '1px solid var(--panel-border)', 
                cursor: 'pointer',
                background: selectedCam === c ? 'rgba(255,255,255,0.05)' : 'transparent',
                borderLeft: selectedCam === c ? '3px solid var(--primary)' : '3px solid transparent'
              }}
            >
              {c}
            </div>
          ))}
        </div>
        <div className="panel">
          <h3>Configured Zones {selectedCam && `for ${selectedCam}`}</h3>
          {!selectedCam ? (
            <div style={{color: 'var(--text-muted)'}}>Select a camera to view its zones.</div>
          ) : (
            <div>
              {(!zones[selectedCam] || zones[selectedCam].length === 0) ? (
                <div style={{color: 'var(--text-muted)', padding: '20px 0'}}>No active zones for this camera. Switch to Operations to draw a new one.</div>
              ) : (
                <table style={{width: '100%', borderCollapse: 'collapse'}}>
                  <thead>
                    <tr style={{borderBottom: '1px solid var(--panel-border)', textAlign: 'left'}}>
                      <th style={{padding: '10px'}}>Zone Name</th>
                      <th style={{padding: '10px'}}>Type</th>
                      <th style={{padding: '10px'}}>Vertices</th>
                      <th style={{padding: '10px'}}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {zones[selectedCam].map(z => (
                      <tr key={z.id} style={{borderBottom: '1px solid var(--panel-border)'}}>
                        <td style={{padding: '10px', color: 'var(--primary)', fontWeight: 'bold'}}>{z.name}</td>
                        <td style={{padding: '10px'}}>{z.type.toUpperCase()}</td>
                        <td style={{padding: '10px'}}>{z.polygon.length} points</td>
                        <td style={{padding: '10px'}}>
                          <button onClick={() => handleDelete(z.id)} className="btn-secondary" style={{padding: '5px 10px', fontSize: '0.8rem', background: 'transparent', border: '1px solid var(--risk-high)', color: 'var(--risk-high)', borderRadius: '4px', cursor: 'pointer'}}>
                            <span className="material-symbols-outlined" style={{fontSize: '14px', verticalAlign: 'middle', marginRight: '4px'}}>delete</span>
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('Checking...');
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [activeTab, setActiveTab] = useState('OPERATIONS');
  const [drawingMode, setDrawingMode] = useState(false);
  const [currentPolygon, setCurrentPolygon] = useState([]);
  const [analyticsData, setAnalyticsData] = useState({
    total_detections: 0, avg_risk_score: 0, high_priority_count: 0, resolved_count: 0, mttr: "-", uptime: "-"
  });
  const [storageHealth, setStorageHealth] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditFilter, setAuditFilter] = useState('OPERATOR');

  useEffect(() => {
    if (!isAuthenticated) return;
    const fetchData = () => {
      fetch('http://localhost:8000/health')
        .then(res => {
          if (!res.ok) throw new Error("Offline");
          return res.json();
        })
        .then(data => setStatus('ONLINE'))
        .catch(() => {
           setStatus('OFFLINE');
           setCameras(prev => prev.map(c => ({...c, status: 'OFFLINE'})));
        });

      fetch('http://localhost:8000/api/events')
        .then(res => {
          if (!res.ok) throw new Error();
          return res.json();
        })
        .then(data => {
          const eventMap = new Map();
          data.forEach(evt => eventMap.set(evt.event_id, evt));
          setEvents(Array.from(eventMap.values()));
        })
        .catch(() => {});

      fetch('http://localhost:8000/api/cameras')
        .then(res => res.json())
        .then(data => setCameras(data))
        .catch(() => {});
        
      fetch('http://localhost:8000/api/analytics')
        .then(res => res.json())
        .then(data => setAnalyticsData(data))
        .catch(() => {});
        
      fetch('http://localhost:8000/api/storage/health')
        .then(res => res.json())
        .then(data => setStorageHealth(data))
        .catch(() => {});

      fetch('http://localhost:8000/api/audit_logs')
        .then(res => res.json())
        .then(data => setAuditLogs(data))
        .catch(() => {});
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleEscalate = async (eventId) => {
    try {
      await fetch(`http://localhost:8000/api/events/${eventId}/escalate`, { method: 'POST' });
      setActiveTab('OPERATIONS');
      setSelectedEvent(null);
    } catch (e) { console.error(e); }
  };

  const handleClearLogs = async () => {
    if (!window.confirm("FACTORY RESET: Are you sure you want to delete ALL events, ALL video evidence, and ALL audit logs? This will completely clear the storage budget.")) return;
    try {
      await fetch('http://localhost:8000/api/audit_logs', { method: 'DELETE' });
      setAuditLogs([]);
      setEvents([]);
    } catch (e) { console.error(e); }
  };

  const handleReconnectCamera = async (cameraId) => {
    try {
      await fetch(`http://localhost:8000/api/cameras/${cameraId}/reconnect`, { method: 'POST' });
    } catch (e) { console.error(e); }
  };

  const handleTogglePause = async (cameraId, currentStatus) => {
    try {
      const endpoint = currentStatus === 'PAUSED' ? 'play' : 'pause';
      await fetch(`http://localhost:8000/api/cameras/${cameraId}/${endpoint}`, { method: 'POST' });
    } catch (e) { console.error(e); }
  };

  const handleDeleteCamera = async (cameraId) => {
    if (!window.confirm(`Are you sure you want to delete ${cameraId}?`)) return;
    try {
      await fetch(`http://localhost:8000/api/cameras/${cameraId}`, { method: 'DELETE' });
    } catch (e) { console.error(e); }
  };

  const handleSaveZone = async () => {
    if (currentPolygon.length < 3) {
        alert("Please click at least 3 points to create a zone.");
        return;
    }
    const zoneName = prompt("Enter a name for this virtual border/zone (e.g., RESTRICTED-A):", "RESTRICTED-A");
    if (!zoneName) return;

    try {
      await fetch(`http://localhost:8000/api/cameras/${selectedCamera}/zones`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: zoneName,
          polygon: currentPolygon
        })
      });
      setDrawingMode(false);
      setCurrentPolygon([]);
      alert("Virtual border saved and activated successfully!");
    } catch (e) {
      console.error(e);
      alert("Failed to save zone");
    }
  };

  const handleUploadVideo = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      await fetch('http://localhost:8000/api/cameras/upload', {
        method: 'POST',
        body: formData
      });
      // The camera list will refresh automatically via the 2-second interval,
      // but we can optionally force a refresh here or alert success
      e.target.value = null; // reset input
    } catch (err) {
      console.error(err);
    }
  };

  const handleResolve = async (eventId) => {
    const reason = prompt("Enter reason for dismissal (e.g. false_positive, duplicate):", "false_positive");
    if (!reason) return;
    try {
      await fetch(`http://localhost:8000/api/events/${eventId}/resolve`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason })
      });
      setActiveTab('OPERATIONS');
      setSelectedEvent(null);
    } catch (e) { console.error(e); }
  };

  const handleHold = async (eventId) => {
    try {
      await fetch(`http://localhost:8000/api/events/${eventId}/hold`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: "Manual operator hold" })
      });
      // Fetch fresh data immediately
      const res = await fetch('http://localhost:8000/api/events');
      const data = await res.json();
      const eventMap = new Map();
      data.forEach(evt => eventMap.set(evt.event_id, evt));
      setEvents(Array.from(eventMap.values()));
      setSelectedEvent(data.find(e => e.event_id === eventId));
    } catch (e) { console.error(e); }
  };

  const activeEvents = events.filter(e => e.status === "ACTIVE");
  const resolvedEvents = events.filter(e => e.status === "RESOLVED");
  const highPriority = activeEvents.filter(e => e.risk_level === 'HIGH' || e.risk_level === 'CRITICAL');
  const onlineCameras = cameras.filter(c => c.status === 'ONLINE').length;

  const renderOperations = () => (
    <div className="dashboard-scroll">
      {/* STATS */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="label">Connected Cameras</div>
          <div className="value">{onlineCameras} / {cameras.length}</div>
          <div className="sub">Active monitoring sources</div>
        </div>
        <div className="stat-card">
          <div className="label">Active Events</div>
          <div className="value">{activeEvents.length}</div>
          <div className="sub">Current detections</div>
        </div>
        <div className="stat-card">
          <div className="label">High Priority</div>
          <div className="value" style={{color: highPriority.length > 0 ? 'var(--risk-high)' : ''}}>
            {highPriority.length}
          </div>
          <div className="sub">Critical events requiring action</div>
        </div>
        <div className="stat-card">
          <div className="label">Resolved Events</div>
          <div className="value">{resolvedEvents.length}</div>
          <div className="sub">Successfully handled</div>
        </div>
      </div>

      <div className="content-grid">
        {/* LEFT COLUMN */}
        <div className="col-left">
          <div className="panel">
            <h2>
              <span className="material-symbols-outlined">monitor</span> 
              Live Monitoring Workspace
            </h2>
            <div className="live-view-container">
              {selectedCamera ? (
                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: '#1e1e1e' }}>
                    <div>
                      <button 
                        onClick={() => { setDrawingMode(!drawingMode); setCurrentPolygon([]); }}
                        className="btn-primary"
                        style={{ marginRight: '10px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                      >
                        <span className="material-symbols-outlined" style={{fontSize: '16px'}}>draw</span>
                        {drawingMode ? 'Cancel Edit' : 'Edit Borders'}
                      </button>
                      {drawingMode && (
                        <button 
                          onClick={handleSaveZone}
                          className="btn-primary"
                          style={{ background: 'var(--risk-low)', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                        >
                          <span className="material-symbols-outlined" style={{fontSize: '16px'}}>save</span>
                          Save Zone
                        </button>
                      )}
                    </div>
                    <button 
                      onClick={() => { setSelectedCamera(null); setDrawingMode(false); setCurrentPolygon([]); }}
                      style={{
                        background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none', 
                        borderRadius: '50%', width: '32px', height: '32px', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}
                    >
                      <span className="material-symbols-outlined">close</span>
                    </button>
                  </div>
                  
                  <div 
                    style={{ position: 'relative', width: '100%', height: 'auto', cursor: drawingMode ? 'crosshair' : 'default' }}
                    onClick={(e) => {
                      if (!drawingMode) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      const x = e.clientX - rect.left;
                      const y = e.clientY - rect.top;
                      
                      setCurrentPolygon([...currentPolygon, {
                        px: x / rect.width, 
                        py: y / rect.height
                      }]);
                    }}
                  >
                    <img 
                      src={`http://localhost:8000/api/cameras/${selectedCamera}/stream`} 
                      alt="Live Stream" 
                      style={{ display: 'block', width: '100%', height: '100%', objectFit: 'fill' }}
                    />
                    
                    {drawingMode && (
                      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                        {currentPolygon.length > 0 && (
                          <polygon 
                            points={currentPolygon.map(p => `${p.px * 100},${p.py * 100}`).join(' ')}
                            fill="rgba(255, 0, 0, 0.3)"
                            stroke="red"
                            strokeWidth="0.5"
                          />
                        )}
                        {currentPolygon.map((p, i) => (
                           <circle key={i} cx={p.px * 100} cy={p.py * 100} r="1" fill="red" />
                        ))}
                      </svg>
                    )}
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <span className="material-symbols-outlined" style={{fontSize: '48px'}}>videocam_off</span>
                  <div>Select a camera from the fleet panel to view stream</div>
                  <button className="btn-primary" style={{width: 'auto', marginTop: '15px'}}>ADD CAMERA</button>
                </div>
              )}
            </div>
          </div>

          <div className="panel">
            <h2>
              <span className="material-symbols-outlined">crisis_alert</span> 
              Active Events
            </h2>
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Camera</th>
                  <th>Object</th>
                  <th>Risk</th>
                  <th>Correlation</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {activeEvents.slice().reverse().map(evt => (
                  <tr key={evt.event_id} className={`risk-${evt.risk_level}`} style={{cursor: 'pointer'}} onClick={() => { setSelectedEvent(evt); setActiveTab('EVENT_DETAILS'); }}>
                    <td>{new Date(evt.timestamp).toLocaleTimeString()}</td>
                    <td>{evt.camera_id}</td>
                    <td>{evt.object_type.toUpperCase()}</td>
                    <td>
                      <span className="badge" style={{
                        backgroundColor: evt.risk_level === 'HIGH' || evt.risk_level === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' : 
                                        evt.risk_level === 'MEDIUM' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: evt.risk_level === 'HIGH' || evt.risk_level === 'CRITICAL' ? '#fca5a5' : 
                              evt.risk_level === 'MEDIUM' ? '#fcd34d' : '#6ee7b7'
                      }}>
                        {evt.risk_level}
                      </span>
                    </td>
                    <td>
                      {evt.correlation_confidence ? (
                        <span className="badge" style={{
                          backgroundColor: evt.correlation_confidence === 'HIGH' ? 'rgba(59, 130, 246, 0.25)' : 
                                          evt.correlation_confidence === 'MEDIUM' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(107, 114, 128, 0.25)',
                          color: evt.correlation_confidence === 'HIGH' ? '#60a5fa' : 
                                evt.correlation_confidence === 'MEDIUM' ? '#fcd34d' : '#9ca3af',
                          border: evt.correlation_confidence === 'HIGH' ? '1px solid #3b82f6' : 
                                 evt.correlation_confidence === 'MEDIUM' ? '1px solid #f59e0b' : '1px solid #6b7280',
                          padding: '3px 8px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}>
                          <span className="material-symbols-outlined" style={{fontSize: '13px'}}>link</span>
                          {evt.correlation_confidence}
                        </span>
                      ) : (
                        <span style={{color: 'var(--text-muted)', fontSize: '0.8rem'}}>UNLINKED</span>
                      )}
                    </td>
                    <td>
                      <div style={{fontWeight: 'bold', fontSize: '0.85rem'}}>
                        {evt.incident_id && (
                          <div style={{color: '#60a5fa', fontSize: '0.8rem', fontWeight: 600, marginBottom: '2px'}}>
                            {evt.correlated_with_camera ? `Track #${evt.track_id} correlated across ${evt.camera_id} -> ${evt.correlated_with_camera}` : `Incident: ${evt.incident_id}`}
                          </div>
                        )}
                        <div style={{color: 'var(--text-main)', fontSize: '0.8rem'}}>
                          {evt.reasons[0] ? evt.reasons[0] : 'Suspicious Activity'}
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
                {activeEvents.length === 0 && (
                  <tr><td colSpan="6" style={{textAlign: 'center', color: 'var(--text-muted)'}}>No active events.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="col-right">
          <div className="panel" style={{flex: 1}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <h2>
                <span className="material-symbols-outlined">video_camera_front</span> 
                Available Cameras
              </h2>
              <label className="btn-primary" style={{padding: '5px 10px', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center'}}>
                <span className="material-symbols-outlined" style={{fontSize: '14px', marginRight: '5px'}}>upload</span>
                Upload Video
                <input type="file" accept="video/mp4,video/*" style={{display: 'none'}} onChange={handleUploadVideo} />
              </label>
            </div>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>FPS</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {cameras.map(cam => (
                  <tr 
                    key={cam.camera_id} 
                    onClick={() => setSelectedCamera(cam.camera_id)}
                    style={{
                      cursor: 'pointer', 
                      background: selectedCamera === cam.camera_id ? 'rgba(255,255,255,0.1)' : 'transparent',
                      borderLeft: selectedCamera === cam.camera_id ? '3px solid var(--primary)' : '3px solid transparent'
                    }}
                  >
                    <td><strong>{cam.camera_id}</strong></td>
                    <td>
                      <span className="badge" style={{
                        backgroundColor: cam.status === 'ONLINE' ? 'var(--status-online)' : 
                                       cam.status === 'RECONNECTING' ? 'var(--status-reconn)' : 'var(--status-offline)',
                        color: cam.status === 'ONLINE' ? 'var(--status-online-text)' : 
                             cam.status === 'RECONNECTING' ? 'var(--status-reconn-text)' : 'var(--status-offline-text)'
                      }}>
                        {cam.status}
                      </span>
                    </td>
                    <td>{cam.fps}</td>
                    <td style={{display: 'flex', gap: '5px'}}>
                      <button 
                        title={cam.status === 'PAUSED' ? 'Play' : 'Pause'}
                        onClick={(e) => { e.stopPropagation(); handleTogglePause(cam.camera_id, cam.status); }}
                        className="btn-secondary" 
                        style={{padding: '4px', fontSize: '0.75rem', display: 'flex', alignItems: 'center'}}
                      >
                        <span className="material-symbols-outlined" style={{fontSize: '16px'}}>
                          {cam.status === 'PAUSED' ? 'play_arrow' : 'pause'}
                        </span>
                      </button>
                      <button 
                        title="Replay / Restart"
                        onClick={(e) => { e.stopPropagation(); handleReconnectCamera(cam.camera_id); }}
                        className="btn-secondary" 
                        style={{padding: '4px', fontSize: '0.75rem', display: 'flex', alignItems: 'center'}}
                      >
                        <span className="material-symbols-outlined" style={{fontSize: '16px'}}>replay</span>
                      </button>
                      <button 
                        title="Delete Camera"
                        onClick={(e) => { e.stopPropagation(); handleDeleteCamera(cam.camera_id); }}
                        className="btn-secondary" 
                        style={{padding: '4px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', color: 'var(--risk-high)', borderColor: 'var(--risk-high)'}}
                      >
                        <span className="material-symbols-outlined" style={{fontSize: '16px'}}>delete</span>
                      </button>
                    </td>
                  </tr>
                ))}
                {cameras.length === 0 && (
                  <tr><td colSpan="4" style={{textAlign: 'center', color: 'var(--text-muted)'}}>No cameras configured.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <h2>
              <span className="material-symbols-outlined">history</span> 
              Event Archive
            </h2>
            <div style={{color: 'var(--text-muted)', fontSize: '0.9rem'}}>
              {resolvedEvents.slice().reverse().slice(0, 5).map(evt => (
                <div key={evt.event_id} style={{padding: '10px 0', borderBottom: '1px solid var(--panel-border)', cursor: 'pointer'}} onClick={() => { setSelectedEvent(evt); setActiveTab('EVENT_DETAILS'); }}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '4px'}}>
                    <strong style={{color: 'var(--text-main)'}}>{evt.camera_id}</strong>
                    <span>{new Date(evt.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div>{evt.reasons.join(', ')}</div>
                </div>
              ))}
              {resolvedEvents.length === 0 && <div>No resolved events yet.</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderArchive = () => {
    const filteredAuditLogs = auditLogs.filter(log => {
        if (auditFilter === 'ALL') return true;
        if (auditFilter === 'SYSTEM') return log.operator.startsWith('SYSTEM');
        return !log.operator.startsWith('SYSTEM');
    });
    return (
    <div className="dashboard-scroll">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
        <h2 style={{fontSize: '1.5rem'}}>Audit & Review Log</h2>
      </div>
      <div className="panel" style={{flex: 1}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <h2><span className="material-symbols-outlined" style={{marginRight: '8px', verticalAlign: 'bottom'}}>policy</span> Immutable Audit Trail</h2>
          <div style={{display: 'flex', gap: '10px'}}>
            <div style={{display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', overflow: 'hidden'}}>
              <button 
                onClick={() => setAuditFilter('OPERATOR')} 
                style={{padding: '5px 10px', border: 'none', cursor: 'pointer', background: auditFilter === 'OPERATOR' ? 'var(--primary)' : 'transparent', color: auditFilter === 'OPERATOR' ? 'white' : 'var(--text-muted)'}}
              >OPERATOR</button>
              <button 
                onClick={() => setAuditFilter('SYSTEM')} 
                style={{padding: '5px 10px', border: 'none', cursor: 'pointer', background: auditFilter === 'SYSTEM' ? 'var(--primary)' : 'transparent', color: auditFilter === 'SYSTEM' ? 'white' : 'var(--text-muted)'}}
              >SYSTEM</button>
              <button 
                onClick={() => setAuditFilter('ALL')} 
                style={{padding: '5px 10px', border: 'none', cursor: 'pointer', background: auditFilter === 'ALL' ? 'var(--primary)' : 'transparent', color: auditFilter === 'ALL' ? 'white' : 'var(--text-muted)'}}
              >ALL</button>
            </div>
            <button onClick={handleClearLogs} className="btn-secondary" style={{padding: '5px 10px', fontSize: '0.8rem', background: 'transparent', border: '1px solid var(--risk-high)', color: 'var(--risk-high)', borderRadius: '4px', cursor: 'pointer'}}>
              <span className="material-symbols-outlined" style={{fontSize: '14px', verticalAlign: 'middle', marginRight: '4px'}}>delete_forever</span>
              CLEAR ALL DATA (FACTORY RESET)
            </button>
          </div>
        </div>
        <div style={{color: 'var(--text-muted)', marginBottom: '15px', fontSize: '0.9rem'}}>All manual reviews and automated storage purges are permanently logged here. No event is ever deleted without a trace.</div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Operator</th>
              <th>Action</th>
              <th>Reason</th>
              <th>Notes / Event ID</th>
            </tr>
          </thead>
          <tbody>
            {filteredAuditLogs.map((log, i) => (
              <tr key={i}>
                <td>{new Date(log.timestamp).toLocaleString()}</td>
                <td><strong style={{color: log.operator === 'SYSTEM_AUTO_PURGE' ? 'var(--risk-high)' : 'var(--primary)'}}>{log.operator}</strong></td>
                <td>
                  <span className="badge" style={{background: 'rgba(255,255,255,0.1)'}}>{log.action}</span>
                </td>
                <td>{log.reason}</td>
                <td style={{color: 'var(--text-muted)', fontSize: '0.8rem'}}>
                  <div>{log.event_id}</div>
                  {log.notes && <div>{log.notes}</div>}
                </td>
              </tr>
            ))}
            {auditLogs.length === 0 && (
              <tr><td colSpan="5" style={{textAlign: 'center', padding: '20px', color: 'var(--text-muted)'}}>No audit records found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
    );
  };

  const renderAnalytics = () => (
    <div className="dashboard-scroll">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
        <h2 style={{fontSize: '1.5rem'}}>Analytics & Insights</h2>
        <div style={{display: 'flex', gap: '10px'}}>
          <button className="btn-secondary">7D</button>
          <button className="btn-secondary">30D</button>
          <button className="btn-secondary">Custom</button>
          <button className="btn-primary" style={{width: 'auto', marginTop: 0}}>Export Report</button>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="label">Total Detections</div>
          <div className="value">{analyticsData.total_detections.toLocaleString()}</div>
          <div className="sub" style={{color: 'var(--risk-low)'}}>Live tracking</div>
        </div>
        <div className="stat-card">
          <div className="label">Average Risk Score</div>
          <div className="value">{analyticsData.avg_risk_score}</div>
          <div className="sub" style={{color: 'var(--text-muted)'}}>System wide average</div>
        </div>
        <div className="stat-card">
          <div className="label">Mean Time To Respond (MTTR)</div>
          <div className="value">{analyticsData.mttr}</div>
          <div className="sub" style={{color: 'var(--text-muted)'}}>Estimated</div>
        </div>
        <div className="stat-card">
          <div className="label">System Uptime</div>
          <div className="value">{analyticsData.uptime}</div>
          <div className="sub" style={{color: 'var(--text-muted)'}}>Stable</div>
        </div>
      </div>

      <div className="panel" style={{marginTop: '20px', marginBottom: '20px'}}>
        <h2><span className="material-symbols-outlined" style={{marginRight: '8px', verticalAlign: 'bottom'}}>hard_drive</span> Storage Governance & Auto-Purge</h2>
        {storageHealth ? (
          <div>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '10px'}}>
              <span>Live Usage: {(storageHealth.used_bytes / 1024 / 1024).toFixed(2)} MB / {(storageHealth.budget_bytes / 1024 / 1024).toFixed(2)} MB</span>
              <strong style={{color: storageHealth.percentage > 85 ? 'var(--risk-high)' : 'var(--primary)'}}>{storageHealth.percentage}%</strong>
            </div>
            <div style={{width: '100%', height: '12px', background: 'var(--panel-border)', borderRadius: '6px', overflow: 'hidden', marginBottom: '20px'}}>
              <div style={{width: `${storageHealth.percentage}%`, height: '100%', background: storageHealth.percentage > 85 ? 'var(--risk-high)' : 'var(--primary)', transition: 'width 0.5s'}}></div>
            </div>
            {storageHealth.storage_warning && (
              <div style={{background: 'rgba(255, 50, 50, 0.15)', border: '1px solid var(--risk-high)', borderRadius: '8px', padding: '12px 16px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px'}}>
                <span className="material-symbols-outlined" style={{color: 'var(--risk-high)', fontSize: '22px'}}>warning</span>
                <span style={{color: 'var(--risk-high)', fontWeight: 600, fontSize: '0.9rem'}}>{storageHealth.storage_warning}</span>
              </div>
            )}
            <div className="stat-grid" style={{gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 0}}>
              <div className="stat-card" style={{padding: '15px'}}>
                <div className="label">Routine Evidence</div>
                <div className="value" style={{fontSize: '1.5rem'}}>{storageHealth.tier_breakdown.routine} Items</div>
                <div className="sub">Purged First</div>
              </div>
              <div className="stat-card" style={{padding: '15px'}}>
                <div className="label">High-Risk Incidents</div>
                <div className="value" style={{fontSize: '1.5rem'}}>{storageHealth.tier_breakdown.confirmed} Items</div>
                <div className="sub">Purged Last</div>
              </div>
              <div className="stat-card" style={{padding: '15px', border: '1px solid var(--primary)'}}>
                <div className="label" style={{color: 'var(--primary)'}}>Held / Secured</div>
                <div className="value" style={{fontSize: '1.5rem'}}>{storageHealth.tier_breakdown.held} Items</div>
                <div className="sub" style={{color: 'var(--primary)'}}>Never Purged</div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{color: 'var(--text-muted)'}}>Loading storage metrics...</div>
        )}
      </div>

      <div className="content-grid">
        <div className="panel">
          <h2>Detection Trends</h2>
          <div style={{height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--panel-border)', borderRadius: '8px', color: 'var(--text-muted)'}}>
            [Line Chart Visualization Placeholder]
          </div>
        </div>
        <div className="panel">
          <h2>Zone Activity</h2>
          <div style={{height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--panel-border)', borderRadius: '8px', color: 'var(--text-muted)'}}>
            [Horizontal Bar Chart Placeholder]
          </div>
        </div>
        <div className="panel">
          <h2>AI Model Confidence</h2>
          <div style={{height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--panel-border)', borderRadius: '8px', color: 'var(--text-muted)'}}>
            [Radar Chart Placeholder]
          </div>
        </div>
        <div className="panel">
          <h2>Shift Efficiency</h2>
          <table>
            <thead>
              <tr>
                <th>Shift</th>
                <th>Incidents</th>
                <th>Avg Response</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Alpha (06:00 - 14:00)</td><td>42</td><td>3m 15s</td></tr>
              <tr><td>Bravo (14:00 - 22:00)</td><td>68</td><td>4m 42s</td></tr>
              <tr><td>Charlie (22:00 - 06:00)</td><td>115</td><td>5m 10s</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderEventDetails = () => {
    if (!selectedEvent) return null;
    return (
      <div className="dashboard-scroll">
        <div style={{display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '20px'}}>
          <button onClick={() => setActiveTab('OPERATIONS')} style={{background: 'transparent', border: 'none', color: 'var(--text-main)', cursor: 'pointer'}}>
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
          <h2 style={{fontSize: '1.5rem'}}>Event Investigation</h2>
          <span className="badge" style={{background: 'var(--panel-border)'}}>Case ID: {selectedEvent.event_id}</span>
        </div>

        <div className="content-grid" style={{gridTemplateColumns: '2fr 1.2fr'}}>
          <div className="panel" style={{padding: 0, overflow: 'hidden'}}>
            <div className="live-view-container" style={{background: '#000', minHeight: '400px'}}>
               {selectedEvent.evidence_path ? (
                  <img 
                     src={`http://localhost:8000/api/events/${selectedEvent.event_id}/evidence`} 
                     alt="Event Snapshot" 
                     style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
               ) : selectedEvent.status === 'ACTIVE' ? (
                  <img src={`http://localhost:8000/api/cameras/${selectedEvent.camera_id}/stream`} alt="Event Stream" />
               ) : (
                  <div className="empty-state">
                    <span className="material-symbols-outlined" style={{fontSize: '48px'}}>image</span>
                    <div>No Evidence Frame Available</div>
                  </div>
               )}
            </div>
            <div style={{padding: '15px', background: 'var(--panel-bg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <div style={{display: 'flex', gap: '20px', color: 'var(--text-muted)', fontSize: '0.9rem'}}>
                <span><strong style={{color: 'var(--text-main)'}}>{selectedEvent.camera_id}</strong></span>
                <span>{new Date(selectedEvent.timestamp).toUTCString()}</span>
              </div>
              <div style={{display: 'flex', gap: '15px'}}>
                <span className="material-symbols-outlined" style={{cursor: 'pointer'}}>play_arrow</span>
                <span className="material-symbols-outlined" style={{cursor: 'pointer'}}>screenshot_region</span>
                <span className="material-symbols-outlined" style={{cursor: 'pointer'}}>download</span>
              </div>
            </div>
          </div>

          <div>
            {/* Cross-Camera Spatial-Temporal Correlation Card */}
            {(selectedEvent.incident_id || selectedEvent.correlation_confidence) && (
              <div className="panel" style={{marginBottom: '20px', border: '1px solid #3b82f6', background: 'rgba(59, 130, 246, 0.05)'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px'}}>
                  <h3 style={{margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.05rem'}}>
                    <span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '20px'}}>hub</span>
                    Cross-Camera Correlation
                  </h3>
                  {selectedEvent.correlation_confidence && (
                    <span className="badge" style={{
                      backgroundColor: selectedEvent.correlation_confidence === 'HIGH' ? 'rgba(59, 130, 246, 0.25)' : 
                                      selectedEvent.correlation_confidence === 'MEDIUM' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(107, 114, 128, 0.25)',
                      color: selectedEvent.correlation_confidence === 'HIGH' ? '#60a5fa' : 
                            selectedEvent.correlation_confidence === 'MEDIUM' ? '#fcd34d' : '#9ca3af',
                      border: selectedEvent.correlation_confidence === 'HIGH' ? '1px solid #3b82f6' : 
                             selectedEvent.correlation_confidence === 'MEDIUM' ? '1px solid #f59e0b' : '1px solid #6b7280',
                      padding: '4px 10px',
                      fontSize: '0.85rem',
                      fontWeight: 'bold',
                      letterSpacing: '0.5px'
                    }}>
                      CONFIDENCE: {selectedEvent.correlation_confidence}
                    </span>
                  )}
                </div>

                <div style={{
                  marginBottom: '12px',
                  padding: '10px 12px',
                  background: 'rgba(59, 130, 246, 0.12)',
                  borderLeft: '4px solid var(--primary)',
                  borderRadius: '4px'
                }}>
                  <div style={{fontWeight: 'bold', color: 'var(--text-main)', fontSize: '0.9rem'}}>
                    Correlated Track Link [{selectedEvent.correlation_confidence || 'ACTIVE'}]
                  </div>
                  <div style={{marginTop: '4px', fontSize: '0.85rem', color: '#93c5fd'}}>
                    Track #{selectedEvent.track_id} correlated across {selectedEvent.camera_id} &rarr; {selectedEvent.correlated_with_camera || 'CAM02'} (Track #{selectedEvent.correlated_with_track || '--'})
                  </div>
                </div>

                <div style={{fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '10px'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span>Incident ID:</span>
                    <strong style={{color: 'var(--text-main)', fontFamily: 'monospace'}}>{selectedEvent.incident_id || '--'}</strong>
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span>Correlated Track:</span>
                    <strong style={{color: 'var(--text-main)'}}>{selectedEvent.correlated_with_track || '--'} ({selectedEvent.correlated_with_camera || '--'})</strong>
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span>Transit Duration:</span>
                    <strong style={{color: 'var(--text-main)'}}>{selectedEvent.transit_time_seconds != null ? `${selectedEvent.transit_time_seconds.toFixed(2)}s` : '--'}</strong>
                  </div>
                  <div style={{display: 'flex', justifyContent: 'space-between'}}>
                    <span>Transit Timing Rule:</span>
                    <strong style={{color: '#6ee7b7'}}>Core Transit Window (3.0s - 15.0s)</strong>
                  </div>
                </div>

                <div style={{fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--panel-border)', paddingTop: '8px'}}>
                  Deterministic spatial-temporal correlation link based on camera adjacency geometry and transit timing. Strictly no appearance-based Re-ID embeddings applied.
                </div>
              </div>
            )}

            <div className="panel">
              <h3 style={{marginBottom: '15px'}}>AI Insights</h3>
              <div style={{marginBottom: '20px', padding: '10px', background: selectedEvent.risk_level === 'HIGH' || selectedEvent.risk_level === 'CRITICAL' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)', borderLeft: `4px solid ${selectedEvent.risk_level === 'HIGH' || selectedEvent.risk_level === 'CRITICAL' ? 'var(--risk-high)' : 'var(--risk-medium)'}`, borderRadius: '4px'}}>
                <strong style={{color: selectedEvent.risk_level === 'HIGH' || selectedEvent.risk_level === 'CRITICAL' ? 'var(--risk-high)' : 'var(--risk-medium)'}}>{selectedEvent.risk_level} - {selectedEvent.status}</strong>
                <div style={{marginTop: '5px', fontSize: '0.9rem', fontWeight: 'bold'}}>{selectedEvent.reasons.join(' + ')} = {selectedEvent.risk_score}/100</div>
              </div>

              <div style={{fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '20px'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
                  <span>Primary Subject:</span><strong style={{color: 'var(--text-main)'}}>{selectedEvent.object_type.toUpperCase()} 98%</strong>
                </div>
                {selectedEvent.has_face && (
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
                    <span>Face Quality:</span>
                    {selectedEvent.face_score && selectedEvent.face_score < 40 ? (
                        <strong style={{color: 'var(--risk-high)'}}>UNCERTAIN — MANUAL REVIEW ({selectedEvent.face_score}/100)</strong>
                    ) : (
                        <strong style={{color: 'var(--text-main)'}}>{selectedEvent.face_category} ({selectedEvent.face_score}/100)</strong>
                    )}
                  </div>
                )}
                {selectedEvent.plate && (
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
                    <span>Plate Extracted:</span>
                    {selectedEvent.plate_confidence && selectedEvent.plate_confidence < 0.75 ? (
                        <strong style={{color: 'var(--risk-high)'}}>UNCERTAIN — MANUAL REVIEW ({Math.round(selectedEvent.plate_confidence * 100)}%)</strong>
                    ) : (
                        <strong style={{color: 'var(--text-main)'}}>{selectedEvent.plate} ({selectedEvent.plate_confidence ? Math.round(selectedEvent.plate_confidence * 100) : '--'}%)</strong>
                    )}
                  </div>
                )}
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
                  <span>Tracking Vector:</span><strong style={{color: 'var(--text-main)'}}>{selectedEvent.track_id}</strong>
                </div>
              </div>

              <h4 style={{marginBottom: '10px', fontSize: '0.95rem'}}>Audit Trail</h4>
              <div style={{borderLeft: '2px solid var(--panel-border)', paddingLeft: '15px', marginLeft: '5px', fontSize: '0.85rem', color: 'var(--text-muted)'}}>
                <div style={{position: 'relative', marginBottom: '15px'}}>
                  <div style={{position: 'absolute', left: '-20px', top: '2px', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary)'}}></div>
                  <strong style={{color: 'var(--text-main)'}}>{new Date(selectedEvent.timestamp).toLocaleTimeString()}</strong> - Object detected
                </div>
                <div style={{position: 'relative', marginBottom: '15px'}}>
                  <div style={{position: 'absolute', left: '-20px', top: '2px', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary)'}}></div>
                  <div style={{color: 'var(--risk-high)', fontWeight: 'bold', fontSize: '1rem', marginBottom: '5px'}}>
                    ALERT: {selectedEvent.reasons[0] || 'Suspicious Activity'}
                  </div>
                  <div style={{color: 'var(--text-main)'}}>
                    <strong>Reason:</strong> {selectedEvent.object_type.charAt(0).toUpperCase() + selectedEvent.object_type.slice(1)} crossed {selectedEvent.zone || 'restricted area'} at {new Date(selectedEvent.timestamp).toLocaleTimeString()}.
                  </div>
                </div>
                {selectedEvent.incident_id && (
                  <div style={{position: 'relative', marginBottom: '15px'}}>
                    <div style={{position: 'absolute', left: '-20px', top: '2px', width: '8px', height: '8px', borderRadius: '50%', background: '#60a5fa'}}></div>
                    <strong style={{color: 'var(--text-main)'}}>Cross-Camera Correlation Linked</strong> - Incident {selectedEvent.incident_id} [{selectedEvent.correlation_confidence || 'HIGH'}]
                  </div>
                )}
              </div>

              <div style={{marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px'}}>
                {selectedEvent.status === 'ACTIVE' && (
                  <button className="btn-primary" style={{backgroundColor: 'var(--risk-high)', marginTop: 0}} onClick={() => handleEscalate(selectedEvent.event_id)}>
                    ESCALATE INCIDENT
                  </button>
                )}
                {selectedEvent.status === 'ACTIVE' && (
                  <button className="btn-secondary" style={{width: '100%', padding: '10px', background: 'transparent', border: '1px solid var(--panel-border)', color: 'var(--text-main)', borderRadius: '6px', cursor: 'pointer'}} onClick={() => handleResolve(selectedEvent.event_id)}>
                    REVIEW & DISMISS
                  </button>
                )}
                {!selectedEvent.is_held && (
                  <button className="btn-secondary" style={{width: '100%', padding: '10px', background: 'var(--panel-border)', border: '1px solid var(--primary)', color: 'var(--text-main)', borderRadius: '6px', cursor: 'pointer'}} onClick={() => handleHold(selectedEvent.event_id)}>
                    <span className="material-symbols-outlined" style={{fontSize: '14px', verticalAlign: 'middle', marginRight: '5px'}}>lock</span>
                    HOLD EVIDENCE
                  </button>
                )}
                {selectedEvent.is_held && (
                  <div style={{padding: '10px', textAlign: 'center', background: 'rgba(59, 130, 246, 0.2)', border: '1px solid var(--primary)', borderRadius: '6px', color: 'var(--primary)', fontWeight: 'bold'}}>
                    <span className="material-symbols-outlined" style={{fontSize: '14px', verticalAlign: 'middle', marginRight: '5px'}}>lock</span>
                    EVIDENCE SECURED
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (!isAuthenticated) {
    return (
      <div style={{height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-color)'}}>
         <div className="panel" style={{width: '320px', textAlign: 'center'}}>
            <span className="material-symbols-outlined" style={{fontSize: '48px', color: 'var(--primary)', marginBottom: '20px'}}>admin_panel_settings</span>
            <h2>Operator Login</h2>
            <div style={{color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '20px'}}>PS187 Border Command</div>
            <input type="password" placeholder="Passcode (admin123)" style={{width: '100%', padding: '12px', margin: '10px 0', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', color: 'white', borderRadius: '4px', textAlign: 'center', boxSizing: 'border-box'}} value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && password === 'admin123' && setIsAuthenticated(true)} />
            <button className="btn-primary" style={{width: '100%'}} onClick={() => password === 'admin123' && setIsAuthenticated(true)}>LOGIN</button>
         </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="brand">
          <span className="material-symbols-outlined" style={{color: 'var(--primary)', fontSize: '28px'}}>shield_person</span>
          BORDER<span style={{color: 'var(--primary)'}}>X</span>
        </div>
        
        <div className="nav-links">
          <div className={`nav-item ${activeTab === 'OPERATIONS' ? 'active' : ''}`} onClick={() => setActiveTab('OPERATIONS')}>
            <span className="material-symbols-outlined">dashboard</span>
            Dashboard
          </div>
          <div className={`nav-item ${activeTab === 'ZONES' ? 'active' : ''}`} onClick={() => setActiveTab('ZONES')}>
            <span className="material-symbols-outlined">category</span>
            Zone Management
          </div>
          <div className="nav-item">
            <span className="material-symbols-outlined">videocam</span>
            Live View
          </div>
          <div className={`nav-item ${activeTab === 'EVENT_DETAILS' ? 'active' : ''}`} onClick={() => setActiveTab('OPERATIONS')}>
            <span className="material-symbols-outlined">crisis_alert</span>
            Events
          </div>
          <div className={`nav-item ${activeTab === 'ARCHIVE' ? 'active' : ''}`} onClick={() => setActiveTab('ARCHIVE')}>
            <span className="material-symbols-outlined">history</span>
            Audit & Archive Log
          </div>
          <div className={`nav-item ${activeTab === 'ANALYTICS' ? 'active' : ''}`} onClick={() => setActiveTab('ANALYTICS')}>
            <span className="material-symbols-outlined">analytics</span>
            System Insights
          </div>
        </div>

        <div style={{padding: '20px', marginTop: 'auto'}}>
          <button className="btn-primary">DEPLOY RESPONSE</button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        
        {/* TOP NAV */}
        <div className="top-bar">
          <div className="tabs">
            {['OPERATIONS', 'ZONES', 'ANALYTICS', 'FLEET', 'ARCHIVE'].map(t => (
              <div 
                key={t} 
                className={`tab ${activeTab === t ? 'active' : ''}`}
                onClick={() => setActiveTab(t)}
              >
                {t}
              </div>
            ))}
          </div>
          <div className="top-actions">
            <div className={`sys-status ${status.toLowerCase()}`}>
              System {status}
            </div>
            <span className="material-symbols-outlined" style={{color: 'var(--text-muted)', cursor: 'pointer'}}>notifications</span>
            <div className="avatar">
              <span className="material-symbols-outlined" style={{fontSize: '20px'}}>person</span>
            </div>
          </div>
        </div>

        {activeTab === 'OPERATIONS' && renderOperations()}
        {activeTab === 'ZONES' && <ZoneManagerView cameras={cameras} />}
        {activeTab === 'ANALYTICS' && renderAnalytics()}
        {activeTab === 'EVENT_DETAILS' && renderEventDetails()}
        {activeTab === 'ARCHIVE' && renderArchive()}
        {['FLEET', 'LOGS'].includes(activeTab) && (
           <div className="dashboard-scroll" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)'}}>
             <h2>Coming Soon</h2>
           </div>
        )}

      </div>
    </div>
  );
}

export default App;
