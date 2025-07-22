# Camera configuration constants
PREVIEW_CAMERA_ID = 0  # Camera index to use for preview (0 or 1)
CAPTURE_MODES = ["raw", "video"]  # Per-camera: "raw", "jpg", or "video" (len=number of cameras)
VIDEO_OUTPUT_DIR = "/data/captures/videos"  # Where to store video files

from time import time
from picamera2 import Picamera2
import numpy as np

# Camera model configuration dictionaries
CAMERA_CONFIGS = {
    'PiVariety_2.2MP_Global_Shutter_Mono': {
        'raw_format': 'SRGGB12',
        'default_gain': 1.0,
        'gain_min': 1.0,
        'gain_max': 16.0,
        'default_exposure': 10000,  # microseconds
        'supports_auto_exposure': False,
        'sensor_resolution': (1600, 1400),
        'description': 'PiVariety 2.2MP Global Shutter Mono',
        'white_level_preview': 255,  # For preview frames (8-bit)
        'white_level_still': 4095,  # For still frames (12-bit
    },
    'IMX519': {
        'raw_format': 'SRGGB12',
        'default_gain': 1.0,
        'gain_min': 1.0,
        'gain_max': 16.0,
        'default_exposure': 10000,  # microseconds
        'supports_auto_exposure': True,
        'sensor_resolution': (4656, 3496),
        'description': 'IMX519 16MP Color',
        'white_level_preview': 255,  # For preview frames (8-bit)
        'white_level_still': 4095,  # For still frames (12-bit)
    },
}

# Map cam_id to camera config (customize as needed for your setup)
camera_configurations = [
    CAMERA_CONFIGS['PiVariety_2.2MP_Global_Shutter_Mono'],
    # CAMERA_CONFIGS['IMX519'],
]

class CameraManager:


    def __init__(self, camera_indices=[0, 1], exposure_mode="auto", gain=None, exposure_time=None):
        import time
        self.cameras = []
        self.exposure_mode = exposure_mode
        self.gain = gain  # User-provided gain value (float, e.g., 1.0, 2.0, ...)
        self.exposure_time = exposure_time  # User-provided exposure time in microseconds
        self.configs = []
        self.preview_configs = []
        self.still_configs = []
        self.last_gain = [gain or 1.0 for _ in camera_indices]  # Track last gain per camera
        self.last_exposure = [exposure_time or 10000 for _ in camera_indices]  # Track last exposure time per camera

        for idx in camera_indices:
            try:
                print(f"[INFO] Initializing Picamera2 for camera index {idx}...")
                cam = Picamera2(idx)
                self._print_camera_specs(cam)
                config = camera_configurations[idx] if idx < len(camera_configurations) else {}
                # Create both video (for preview) and still (for capture) configurations
                sensor_res = cam.sensor_resolution
                cam.video_configuration = cam.create_video_configuration(main={'size': (240, 240), 'format': 'RGB888'}, raw=None)
                cam.still_configuration = cam.create_still_configuration(raw={'size': sensor_res, 'format': config.get('raw_format', 'SRGGB12')})
                # Only specify 'main' stream for preview, no 'raw' stream
                # preview_config = cam.create_video_configuration(main={'size': (240, 240), 'format': 'RGB888'}, controls={"FrameDurationLimits": (10000, 33333), "AnalogueGain": 14.0, "ExposureTime": 23123}, raw=None)
                # still_config = cam.create_still_configuration(raw={'size': sensor_res, 'format': config.get('raw_format', 'SRGGB12')}, controls={"AnalogueGain": 14.0, "ExposureTime": 23123})
                cam.configure("video")
                cam.start()
                time.sleep(0.5)
                # self._configure_camera(cam, config, idx)
                print(f"[INFO] Camera {idx} started and configured (video/preview mode).")
                self.cameras.append(cam)
                # self.preview_configs.append(preview_config)
                # self.still_configs.append(still_config)
                # print("[INFO] Camera info:", getattr(cam, 'camera_info', 'N/A'))
                self._print_camera_specs(cam)
            except Exception as e:
                print(f"[ERROR] Could not initialize camera {idx}: {e}")

    def _print_camera_specs(self, cam):
        """Print detailed camera specifications."""
        try:
            print("[INFO] Camera properties:", cam.camera_properties)
            # print("[INFO] Sensor modes:", cam.sensor_modes)
            print("[INFO] Sensor resolution:", cam.sensor_resolution)
            print("[INFO] Supported controls:", cam.controls)
            print("[INFO] Supported camera controls:", cam.camera_controls)
            # print("[INFO] Camera controls dictionary:", cam.camera_properties.get('Controls', 'N/A'))
            # print("[INFO] More controls", cam.controls.get_libcamera_controls(), "if available")
            # print("[INFO] Camera info:", getattr(cam, 'camera_info', 'N/A'))
            # print("[INFO] AnalogueGain range:", cam.controls["AnalogueGain"].get_range())
            # print("")
        except Exception as e:
            print(f"[ERROR] Could not print camera specs: {e}")

    def _should_use_custom_exposure(self, camera_index):
        """Determine if custom exposure correction should be used."""
        config = camera_configurations[camera_index] if camera_index < len(camera_configurations) else {}
        support_auto_exposure =  config.get('supports_auto_exposure', False)
        smart_modes = {"smart-auto", "smart-auto-action", "smart-auto-low-noise"}
        if not support_auto_exposure:
            return self.exposure_mode != "manual"
        else:
            return self.exposure_mode in smart_modes

    def _configure_camera(self, cam, config, cam_id):
        # Set camera controls based on mode, using camera_configurations for AE support
        import time
        supports_ae = config.get('supports_auto_exposure', False)
        gain = self.gain if self.gain else config.get('default_gain', 1.0)
        exposure = self.exposure_time or config.get('default_exposure', 10000)
        self.last_gain[cam_id] = gain  # Track last gain per camera
        self.last_exposure[cam_id] = exposure  # Track last exposure time
        ae_modes = ["gain-priority", "etime-priority", "auto"]
        if self.exposure_mode in ae_modes and supports_ae:
            if self.exposure_mode == "gain-priority":
                print(f"[INFO] Setting GAIN-PRIORITY mode: Gain={gain}")
                cam.set_controls({"AeEnable": True, "AnalogueGain": gain, "AnalogueGainMode": 1})
            elif self.exposure_mode == "etime-priority":
                print(f"[INFO] Setting ETIME-PRIORITY mode: Exposure={self.exposure_time}us")
                cam.set_controls({"AeEnable": True, "ExposureTime": exposure, "AnalogueGainMode": 0})
            else:  # "auto"
                print(f"[INFO] Setting FULL AUTO mode.")
                cam.set_controls({"AeEnable": True, "AnalogueGainMode": 0})
        else:
            print(f"[INFO] Setting MANUAL mode (AE unsupported or forced): Gain={gain}, Exposure={self.exposure_time} us")
            # cam.set_controls({
            #     "AeEnable": False,
            #     "AnalogueGainMode": 1,  # Use manual gain mode
            # })
            time.sleep(0.2)
            cam.set_controls({
                # "AeExposureMode": 0,
                "AnalogueGain": gain,
                "ExposureTime": exposure
            })
        time.sleep(5.1)  # Allow settings to take effect
        self._print_camera_specs(cam)

    def set_exposure(self, cam_id=0, gain=None, exposure_time=None):
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            controls = {}
            if gain is not None:
                controls["AnalogueGain"] = gain
                self.last_gain[cam_id] = gain
            if exposure_time is not None:
                controls["ExposureTime"] = exposure_time
                self.last_exposure[cam_id] = exposure_time
            if controls:
                cam.set_controls(controls)
            self._print_camera_specs(cam)

    def set_preview_mode(self, cam_id=0):
        """Switch camera to fast preview (video) mode."""
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            # config = self.preview_configs[cam_id]
            cam.stop()
            cam.configure("video")
            cam.start()
            print(f"[INFO] Camera {cam_id} switched to preview (video) mode.")

    def set_still_mode(self, cam_id=0):
        """Switch camera to still (raw/full-res) mode."""
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            # config = self.still_configs[cam_id]
            cam.stop()
            cam.configure("still")
            cam.start()
            print(f"[INFO] Camera {cam_id} switched to still (capture) mode.")

    def get_white_level(self, cam_id=0, is_preview=False):
        """Get the white level for the specified camera and mode.
        Returns 255 for preview (8-bit) or 4095 for still (12-bit).
        """
        if cam_id < len(self.cameras):
            config = camera_configurations[cam_id] if cam_id < len(camera_configurations) else {}
            if is_preview:
                return config.get('white_level_preview', 255)
            else:
                return config.get('white_level_still', 4095)
        return 255  # Default fallback


    def _suggest_exposure_correction(self, cam_id, is_preview, raw_arr):
        """
        Given a uint16 raw image, estimate the number of stops needed to correct exposure.
        Uses average luminance (linear) as a simple proxy.
        Returns positive for increase, negative for decrease, 0 for no change.
        """
        # 12-bit max value
        max_val = self.get_white_level(cam_id, is_preview)
        avg = raw_arr.mean()
        # Target: middle gray at 18% of max (common photographic convention)
        target = max_val * 0.18
        # Stops = log2(target/avg)
        import numpy as np
        if avg <= 0:
            return 0  # avoid log(0)
        stops = np.log2(target / avg)
        print(f"[SMART AE] Avg: {avg:.1f}, Target: {target:.1f}, Suggested correction: {stops:+.2f} stops")
        return stops

    def _apply_exposure_correction(self, cam_id, correction_stops):
        """
        Apply exposure correction based on the suggested number of stops.
        Adjusts gain or exposure time accordingly.
        """
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            # Use tracked last_gain value
            last_gain = self.last_gain[cam_id] if cam_id < len(self.last_gain) else (self.gain or 1.0)
            last_exposure = self.last_exposure[cam_id] if cam_id < len(self.last_exposure) else (self.exposure_time or 10000)

            if correction_stops > 0:
                new_gain = last_gain * (2 ** correction_stops)
            else:
                new_gain = last_gain / (2 ** abs(correction_stops))
            # Clamp gain to config limits
            config = camera_configurations[cam_id] if cam_id < len(camera_configurations) else {}
            gain_min = config.get('gain_min', 1.0)
            gain_max = config.get('gain_max', 16.0)
            new_gain = max(gain_min, min(new_gain, gain_max))
            new_exposure = last_exposure
            if (last_gain != new_gain or last_exposure != new_exposure):
                print(f"[SMART AE] Applying exposure correction: Gain={new_gain:.2f}, Exposure={new_exposure}us")
                self.set_exposure(cam_id, gain=new_gain, exposure_time=new_exposure)
            else:
                print(f"[SMART AE] No exposure correction needed: Gain={last_gain:.2f}, Exposure={last_exposure}us")

    def _maybe_correct_exposure(self, cam_id, is_preview, raw_arr):
        """
        If smart AE is enabled, suggest exposure correction based on the raw array.
        Returns the number of stops to adjust, or 0 if no correction needed.
        """
        # if self._should_use_custom_exposure(cam_id):
        #     correction_stops = self._suggest_exposure_correction(cam_id, is_preview, raw_arr)
        #     if (abs(correction_stops) > 0.2):
        #         self._apply_exposure_correction(cam_id, correction_stops)
        return 0

    def capture_frame(self, cam_id=0, raw=False, jpg=False):
        """
        Capture a frame from the specified camera.
        In preview mode, always returns 240x240 RGB (main).
        In still mode, returns raw if raw=True, jpg if jpg=True, else full-res RGB.
        For raw, always returns a (height, width) uint16 array (12-bit data, LSB first in each uint16).
        If smart AE is needed, prints suggested correction.
        """
        import time
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            try:
                t0 = time.time()
                if raw:
                    print(f"[DEBUG] Capturing raw frame from camera {cam_id}...")
                    # arr = cam.capture_array("raw")
                    req = cam.capture_request()
                    print(req.get_metadata())
                    arr = req.make_array("raw")
                    req.release()
                    t1 = time.time()
                    print(f"[DEBUG] Raw array shape: {arr.shape}, dtype: {arr.dtype}")
                    print(f"[PROFILE] cam.capture_array('raw') took {(t1-t0)*1000:.2f} ms")
                    # Convert packed uint8 (height, width*2) to uint16 (height, width)
                    if arr.dtype == np.uint8 and arr.shape[1] % 2 == 0:
                        height, width2 = arr.shape
                        width = width2 // 2
                        arr16 = arr.view(np.uint16).reshape(height, width)
                        arr = arr16
                    # If already uint16, just use as-is
                    if arr.dtype == np.uint16:
                        arr16 = arr
                    else:
                        arr16 = arr  # fallback for debugging
                    # Smart AE: only for raw
                    self._maybe_correct_exposure(cam_id, False, arr16)
                    t2 = time.time()
                    print(f"[PROFILE] Exposure correction took {(t2-t1)*1000:.2f} ms")
                    return arr16
                elif jpg:
                    print(f"[DEBUG] Capturing JPEG from camera {cam_id}...")
                    jpg_bytes = cam.capture_buffer("main", format="jpeg")
                    t1 = time.time()
                    print(f"[PROFILE] cam.capture_buffer('main', jpeg) took {(t1-t0)*1000:.2f} ms")
                    return jpg_bytes
                else:
                    print(f"[DEBUG] Capturing main frame from camera {cam_id}...")
                    req = cam.capture_request()
                    print(req.get_metadata())
                    arr = req.make_array("main")
                    req.release()

                    #arr = cam.capture_array("main")
                    t1 = time.time()
                    print(f"[PROFILE] cam.capture_array('main') took {(t1-t0)*1000:.2f} ms")
                    self._maybe_correct_exposure(cam_id, True, arr)
                    t2 = time.time()
                    print(f"[PROFILE] Exposure correction took {(t2-t1)*1000:.2f} ms")
                    return arr
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

    # --- Video recording methods ---
    def start_video_recording(self, cam_id=0, filename=None):
        """Start video recording for the specified camera. Returns the output filename."""
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            import os, time
            if filename is None:
                ts = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(VIDEO_OUTPUT_DIR, f"video_cam{cam_id}_{ts}.mp4")
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            cam.start_recording(filename)
            print(f"[VIDEO] Camera {cam_id} started recording to {filename}")
            return filename
        else:
            print(f"[ERROR] Camera id {cam_id} out of range for video recording.")
            return None

    def stop_video_recording(self, cam_id=0):
        """Stop video recording for the specified camera."""
        if cam_id < len(self.cameras):
            cam = self.cameras[cam_id]
            cam.stop_recording()
            print(f"[VIDEO] Camera {cam_id} stopped recording.")
        else:
            print(f"[ERROR] Camera id {cam_id} out of range for video recording.")

    def is_recording(self, cam_id=0):
        if cam_id < len(self.cameras):
            return getattr(self.cameras[cam_id], "_recording", False)
        return False


