import pytest
from camera.simulated_camera import SimulatedCamera

def test_simulated_camera_read():
    cam = SimulatedCamera("TEST_CAM_01", fps=30)
    
    # Should not read if not started
    ret, frame = cam.read()
    assert not ret
    assert frame is None
    
    cam.start()
    ret, frame = cam.read()
    
    assert ret
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    
    cam.stop()
    ret, frame = cam.read()
    assert not ret
