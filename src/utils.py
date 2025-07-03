import cv2
import numpy as np
from PIL import Image

def draw_histogram(frame):
    """Draw a histogram for the image and return as a PIL image."""
    chans = cv2.split(frame)
    colors = ('b', 'g', 'r')
    hist_img = np.zeros((100, 256, 3), dtype=np.uint8)

    for chan, color in zip(chans, colors):
        hist = cv2.calcHist([chan], [0], None, [256], [0, 256])
        cv2.normalize(hist, hist, 0, 100, cv2.NORM_MINMAX)
        for x, y in enumerate(hist):
            cv2.line(hist_img, (x, 100), (x, 100 - int(y)), (255 if color == 'b' else 0,
                                                             255 if color == 'g' else 0,
                                                             255 if color == 'r' else 0), 1)
    return Image.fromarray(hist_img)

def overlay_histogram_on_image(frame, hist_img, position=(0, 0)):
    """Overlay the histogram image onto the frame at the given position."""
    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    hist_img = hist_img.convert("RGBA").resize((128, 50))
    frame_pil.paste(hist_img, position, hist_img)
    return cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)