import numpy as np
import sys
import os

from pidng.core import RPICAM2DNG, DNGTags, Tag
from pidng.camdefs import *

def main():
    if len(sys.argv) < 3:
        print("Usage: python npy_to_dng.py <input.npy> <output.dng>")
        sys.exit(1)

    npy_path = sys.argv[1]
    dng_path = sys.argv[2]

    if not os.path.exists(npy_path):
        print(f"Input file {npy_path} does not exist.")
        sys.exit(1)

    raw = np.load(npy_path)

    # Use the official camera model for IMX519, mode 1, RGGB
    camera = RaspberryPiHqCamera(1, CFAPattern.RGGB)
    camera.fmt = {"size": (4656, 3496)}
    camera.tags.set(Tag.ApertureValue, [[4,1]])             # F 4.0
    camera.tags.set(Tag.ExposureTime, [[1,400]])             # SHUTTER 1/400
    camera.tags.set(Tag.PhotographicSensitivity, [400])     # ISO 400

    dng = RPICAM2DNG(camera)
    dng.options(path="", compress=False)
    dng.convert(
        raw,
        filename=dng_path
    )
    print(f"Converted {npy_path} to {dng_path}")

if __name__ == "__main__":
    main()
