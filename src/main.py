from camera import CameraManager
from display import PiTFTDisplay
from utils import draw_histogram, overlay_histogram_on_image
import time
import cv2
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="PiSnapper Camera App")
    parser.add_argument('--mode', type=str, default='auto', choices=[
        'auto', 'manual', 'iso-priority', 'etime-priority',
        'smart-auto', 'smart-auto-action', 'smart-auto-low-noise'],
        help='Exposure mode')
    parser.add_argument('--iso', type=int, default=None, help='ISO value (e.g. 100, 200, 400)')
    parser.add_argument('--etime', type=int, default=None, help='Exposure time in microseconds')
    args = parser.parse_args()

    cam_manager = CameraManager(camera_indices=[0], exposure_mode=args.mode, iso=args.iso, exposure_time=args.etime)
    display = PiTFTDisplay()

    img_count = 0
    output_dir = "captured_images"
    os.makedirs(output_dir, exist_ok=True)
    print("[INFO] Starting camera capture loop...")
    try:
        while True:
            print("[DEBUG] Capturing frame...")
            frame = cam_manager.capture_frame()
            if frame is not None:
                img_path = os.path.join(output_dir, f"frame_{img_count:04d}.jpg")
                # cv2.imwrite(img_path, frame)
                print(f"[INFO] Frame captured and saved to {img_path}")
                hist_img = draw_histogram(frame)
                print("[DEBUG] Histogram generated.")
                frame_with_hist = overlay_histogram_on_image(frame, hist_img, position=(5, 5))
                display.show_image(frame_with_hist)
                img_count += 1
            else:
                print("[WARN] No frame captured from camera.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        cam_manager.release()
        display.clear()

if __name__ == "__main__":
    main()