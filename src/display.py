import board
import digitalio
from adafruit_rgb_display import st7789
from adafruit_rgb_display.rgb import color565
from PIL import Image

class PiTFTDisplay:
    def __init__(self):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = None
        BAUDRATE = 64000000
        self.display = st7789.ST7789(
            board.SPI(),
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=BAUDRATE,
            width=240,
            height=240,
            x_offset=0,
            y_offset=80,
        )
        self.backlight = digitalio.DigitalInOut(board.D22)
        self.backlight.switch_to_output()
        self.backlight.value = True
        self.buttonA = digitalio.DigitalInOut(board.D23)
        self.buttonB = digitalio.DigitalInOut(board.D24)
        self.buttonA.switch_to_input()
        self.buttonB.switch_to_input()

    def show_image(self, frame):
        img = Image.fromarray(frame)
        img = img.resize((240, 240))
        self.display.image(img)

    def show_histogram(self, hist_img):
        hist_img = hist_img.resize((240, 240))
        self.display.image(hist_img)

    def clear(self):
        self.display.fill(color565(0, 0, 0))