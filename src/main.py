from camera import CameraManager
from display import PiTFTDisplay
from utils import draw_histogram, overlay_histogram_on_image
import tifffile

import time
import cv2
import os
import argparse
import board
import digitalio
from datetime import datetime
import numpy as np
import threading
import queue


def main():
    parser = argparse.ArgumentParser(description="PiSnapper Camera App")
    parser.add_argument('--mode', type=str, default='auto', choices=[
        'auto', 'manual', 'gain-priority', 'etime-priority',
        'smart-auto', 'smart-auto-action', 'smart-auto-low-noise'],
        help='Exposure mode')
    parser.add_argument('--gain', type=float, default=None, help='Gain value (e.g. 1.0, 4.0, 16.0)')
    parser.add_argument('--etime', type=int, default=None, help='Exposure time in microseconds')
    parser.add_argument('--unpack-tiff', action='store_true', help='Unpack RAW12 and save as TIFF instead of .npy')
    args = parser.parse_args()

    cam_manager = CameraManager(camera_indices=[0], exposure_mode=args.mode, gain=args.gain, exposure_time=args.etime)
    display = PiTFTDisplay()

    # Setup buttons (redundant if using display.buttonA/B, but explicit here)
    buttonA = display.buttonA
    buttonB = display.buttonB

    # State machine
    STATE_OFF = "off"
    STATE_IDLE = "idle"
    STATE_CAPTURING = "capturing"
    state = STATE_OFF

    def turn_off():
        shared["state"] = STATE_OFF
        display.backlight.value = False
        display.clear()
        print("[STATE] OFF: Display and cameras off.")

    def turn_idle():
        shared["state"] = STATE_IDLE
        display.backlight.value = True
        cam_manager.set_preview_mode()
        print("[STATE] IDLE: Displaying live camera feed.")

    def turn_capturing():
        shared["state"] = STATE_CAPTURING
        display.backlight.value = True
        cam_manager.set_still_mode()
        print("[STATE] CAPTURING: Saving RAW images as fast as possible.")

    def setup_capture_dir():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_dir = f"/data/captures/{ts}"
        os.makedirs(capture_dir, exist_ok=True)
        shared["img_count"] = 0
        shared["capture_dir"] = capture_dir


    from PIL import Image, ImageDraw, ImageFont
    event_queue = queue.Queue()
    shared = {
        "state": STATE_OFF,
        "img_count": 0,
        "capture_dir": None,
        "running": True,  # global running flag for all threads
        "camera_running": True,  # camera thread running flag
        "last_camera_activity": time.time(),
    }

    def button_thread():
        last_a = buttonA.value
        last_b = buttonB.value
        while shared["running"]:
            a_pressed = (not buttonA.value) and last_a
            b_pressed = (not buttonB.value) and last_b
            last_a = buttonA.value
            last_b = buttonB.value
            if a_pressed:
                event_queue.put("A")
            if b_pressed:
                event_queue.put("B")
            time.sleep(0.01)

    def camera_thread():
        try:
            while shared["camera_running"]:
                shared["last_camera_activity"] = time.time()  # Update activity timestamp

                # Handle events
                try:
                    event = event_queue.get_nowait()
                except queue.Empty:
                    event = None

                if shared["state"] == STATE_OFF:
                    if event == "A":
                        turn_capturing()
                        setup_capture_dir()
                    elif event == "B":
                        turn_idle()
                    else:
                        time.sleep(0.05)
                        continue

                elif shared["state"] == STATE_IDLE:
                    camera_thread._off_displayed = False
                    if event == "A":
                        turn_capturing()
                        setup_capture_dir()
                    elif event == "B":
                        turn_off()
                        continue
                    # Use preview mode for fast preview
                    frame = cam_manager.capture_frame()
                    if frame is not None:
                        hist_img = draw_histogram(frame)
                        frame_with_hist = overlay_histogram_on_image(frame, hist_img, position=(5, 5))
                        display.show_image(frame_with_hist)
                    time.sleep(0.05)

                elif shared["state"] == STATE_CAPTURING:
                    camera_thread._off_displayed = False
                    if event == "B":
                        turn_idle()
                        continue
                    # Button A does nothing (keep capturing)
                    raw = cam_manager.capture_frame(raw=True)
                    if raw is not None:
                        now = datetime.now()
                        ms = int(now.microsecond / 1000)
                        if args.unpack_tiff:
                            img_name = f"IMG_{now.strftime('%Y%m%d_%H%M%S')}_{ms:03d}.tiff"
                            img_path = os.path.join(shared["capture_dir"], img_name)
                            tifffile.imwrite(
                                img_path,
                                raw,
                                photometric='minisblack',
                                planarconfig='contig',
                                dtype='uint16'
                            )
                            print(f"[CAPTURE] Saved packed 12-bit TIFF to {img_path}")
                        else:
                            img_name = f"IMG_{now.strftime('%Y%m%d_%H%M%S')}_{ms:03d}.npy"
                            img_path = os.path.join(shared["capture_dir"], img_name)
                            np.save(img_path, raw)
                            print(f"[CAPTURE] Saved RAW to {img_path}")
                        shared["img_count"] += 1
                    img = Image.new("RGB", (240, 240), (0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    text = f"capturing - {shared['img_count']}"
                    draw.text((40, 110), text, fill=(255, 255, 255))
                    display.display.image(img)
                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            print("Releasing...")
            cam_manager.release()
            display.clear()

    # def watchdog_thread():
    #     WATCHDOG_TIMEOUT = 2.0  # seconds
    #     while shared["running"]:
    #         time.sleep(0.5)
    #         now = time.time()
    #         last = shared.get("last_camera_activity", now)
    #         if now - last > WATCHDOG_TIMEOUT:
    #             print("[WATCHDOG] Camera thread appears hung. Restarting...")
    #             shared["camera_running"] = False  # signal camera thread to exit
    #             try:
    #                 t2[0].join(timeout=1.0)
    #             except Exception as e:
    #                 print(f"[WATCHDOG] Error joining old camera thread: {e}")
    #             # Start a new camera thread
    #             shared["camera_running"] = True
    #             shared["last_camera_activity"] = time.time()
    #             t2[0] = threading.Thread(target=camera_thread, daemon=False)
    #             t2[0].start()

    # Ensure we start in OFF state visually and logically
    turn_off()
    t1 = threading.Thread(target=button_thread, daemon=True)
    t2 = threading.Thread(target=camera_thread, daemon=False)
    # t3 = threading.Thread(target=watchdog_thread, daemon=True)
    t1.start()
    t2.start()
    # t3.start()
    try:
        t2.join()
    except KeyboardInterrupt:
        print("Exiting due to KeyboardInterrupt (main thread)")
        shared["camera_running"] = False  # Signal camera thread to exit
        shared["running"] = False  # Signal all threads to exit
        t2.join()  # Wait for camera thread to clean up
        print("Main cleanup complete.")
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        shared["camera_running"] = False
        shared["running"] = False
        t2.join()
        print("Main cleanup complete.")
    finally:
        print("Main finally.")

if __name__ == "__main__":
    main()