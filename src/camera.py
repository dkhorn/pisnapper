from picamera2 import Picamera2
import numpy as np

class CameraManager:
    def __init__(self, camera_indices=[0], exposure_mode="auto", iso=None, exposure_time=None):
        self.cameras = []
        self.exposure_mode = exposure_mode
        self.iso = iso  # ISO value (float, e.g., 100, 200, 400, ...)
        self.exposure_time = exposure_time  # microseconds
        for idx in camera_indices:
            try:
                print(f"[INFO] Initializing Picamera2 for camera index {idx}...")
                cam = Picamera2(idx)
                cam.start()  # Start camera before setting controls
                self._configure_camera(cam)
                print(f"[INFO] Camera {idx} started and configured.")
                self.cameras.append(cam)
            except Exception as e:
                print(f"[ERROR] Could not initialize camera {idx}: {e}")

    def _configure_camera(self, cam):
        # Set camera controls based on mode
        import time
        if self.exposure_mode == "manual":
            print(f"[INFO] Setting MANUAL mode: ISO={self.iso}, Exposure={self.exposure_time}us")
            gain = self.iso / 100 if self.iso else 1.0
            exposure = self.exposure_time or 10000
            cam.set_controls({
                "AeEnable": False,
                "AnalogueGain": gain,
                "ExposureTime": exposure
            })
            time.sleep(0.1)  # Allow settings to take effect
        elif self.exposure_mode == "iso-priority":
            print(f"[INFO] Setting ISO-PRIORITY mode: ISO={self.iso}")
            gain = self.iso / 100 if self.iso else 1.0
            cam.set_controls({"AeEnable": True, "AnalogueGain": gain})
        elif self.exposure_mode == "etime-priority":
            print(f"[INFO] Setting ETIME-PRIORITY mode: Exposure={self.exposure_time}us")
            exposure = self.exposure_time or 10000
            cam.set_controls({"AeEnable": True, "ExposureTime": exposure})
        elif self.exposure_mode == "auto":
            print(f"[INFO] Setting FULL AUTO mode.")
            cam.set_controls({"AeEnable": True})
        # Smart-auto modes will be handled in main loop

    def set_exposure(self, cam_id=0, iso=None, exposure_time=None):
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            controls = {}
            if iso is not None:
                controls["AnalogueGain"] = iso/100
            if exposure_time is not None:
                controls["ExposureTime"] = exposure_time
            if controls:
                cam.set_controls(controls)

    def capture_frame(self, cam_id=0, raw=False):
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            try:
                if raw:
                    print(f"[DEBUG] Capturing raw frame from camera {cam_id}...")
                    raw_array = cam.capture_array("raw")
                    return raw_array
                else:
                    print(f"[DEBUG] Capturing RGB frame from camera {cam_id}...")
                    frame = cam.capture_array()
                    return frame
            except Exception as e:
                print(f"[WARN] Failed to capture frame from camera {cam_id}: {e}")
                return None
        print(f"[ERROR] Camera id {cam_id} out of range.")
        return None

    def release(self):
        for i, cam in enumerate(self.cameras):
            try:
                cam.stop()
                print(f"[INFO] Stopped camera {i}.")
            except Exception as e:
                print(f"[WARN] Could not stop camera {i}: {e}")