# Virtual geofence zones (normalized 0.0 to 1.0 coordinates [x, y])
ZONES = {
    "RESTRICTED_SECTOR": [
        [0.0, 0.6],
        [1.0, 0.6],
        [1.0, 1.0],
        [0.0, 1.0]
    ],
    "VIRTUAL_FENCE_LINE": [
        [0.0, 0.6],
        [1.0, 0.6]
    ]
}

# Rule Risk Weights
RISK_WEIGHTS = {
    "NORMAL_ZONE": 10,
    "RESTRICTED_ZONE": 30,
    "NIGHT_MOVEMENT": 20,
    "FENCE_BREACH": 30,
    "CROSS_CAMERA_MATCH": 15
}

# Operational thresholds
DWELL_TIME_THRESHOLD_SEC = 5.0