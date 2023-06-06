"""
Author: Chris Knowles
File: oled.py
Version: 1.0.0
Notes: This provides the class for the FeatherWing SH1107 device, it relies on the FrameBuffer not the
       Adafruit DisplayIO approach - it encapsulates use of the driver for the SH1107 as provided at:-
       
           https://github.com/mdroberts1243/mdroberts1243_CircuitPython_SH1107_I2C
       
       Also, the use of the three buttons (A, B and C) are encapsulated in the Oled_FeatherWing class
       so the action_buttons() method should be called each time around the main application loop or when
       needed, each button can be designated as being used or not using the "use_buttons" __init__()
       parameter (include the button letter as a string in a list passed to this parameter, defaults
       to all three buttons as being used)
       
       The pin numbers for the buttons can be passed into __init__ or they will default to those pin
       numbers defined as part of the featherwing format (button A pin is board.D9, button B pin is
       board.D6 and button C pin is board.D5)
       
       This library is not part of the CircuitPython libraries release at the time of the creation of
       the Oled_FeatherWing class
       
       Maximum readable text output using font5x8 is 21 characters by 6 lines when starting at (1, 4) and
       then increasing y by 10 pixels per new line, each character is then 6.05 x 10.00 pixels in size
       
       Also requires the "font5x8.bin" font file in the same directory as this library
"""
# Imports
import board
from adafruit_bus_device.i2c_device import I2CDevice
from sh1107_i2c import SH1107_I2C as SH1107
from digitalio import DigitalInOut, Pull

class Oled_FeatherWing:
    LEFT_VERTICAL_ORIENTATION = 0
    TOP_HORIZONTAL_ORIENTATION = 1
    RIGHT_VERTICAL_ORIENTATION = 2
    BOTTOM_HORIZONTAL_ORIENTATION = 3

    def __init__(self, i2c, device_address=0x3c, use_buttons=["a", "A", "b", "B", "c", "C"],
                 button_a_pin=board.D9, button_b_pin=board.D6, button_c_pin=board.D5,
                 button_a_callback=None, button_b_callback=None, button_c_callback=None):
        self.native_width = 64
        self.native_height = 128
        self.i2c = i2c
        self.device_address = device_address
        self.i2c_device = I2CDevice(i2c=self.i2c, device_address=self.device_address)
        self.oled = SH1107(i2c=self.i2c_device, width=self.native_width, height=self.native_height)
        self.background = 0
        self.foreground = 1
        self.on = False
        self.rotation = 0

        self.use_buttons = use_buttons
        self.use_a_button = "a" in self.use_buttons or "A" in self.use_buttons
        self.use_b_button = "b" in self.use_buttons or "B" in self.use_buttons
        self.use_c_button = "c" in self.use_buttons or "C" in self.use_buttons
        
        if self.use_a_button:
            self.button_a_pin = DigitalInOut(button_a_pin)
            self.button_a_pin.pull = Pull.UP
            self.button_a_callback = button_a_callback
        else:
            self.button_a_pin = None
            self.button_a_callback = None

        if self.use_b_button:
            self.button_b_pin = DigitalInOut(button_b_pin)
            self.button_b_pin.pull = Pull.UP
            self.button_b_callback = button_b_callback
        else:
            self.button_b_pin = None
            self.button_b_callback = None

        if self.use_c_button:
            self.button_c_pin = DigitalInOut(button_c_pin)
            self.button_c_pin.pull = Pull.UP
            self.button_c_callback = button_c_callback
        else:
            self.button_c_pin = None
            self.button_c_callback = None
            
        self.rotate_to(self.TOP_HORIZONTAL_ORIENTATION)  # Initially top aligned horizontal display ie. 128x64 
        self.switch_on()

    @property
    def width(self):
        if self.rotation == self.TOP_HORIZONTAL_ORIENTATION or self.rotation == self.BOTTOM_HORIZONTAL_ORIENTATION:
            return self.native_height
        else:
            return self.native_width

    @property
    def height(self):
        if self.rotation == self.TOP_HORIZONTAL_ORIENTATION or self.rotation == self.BOTTOM_HORIZONTAL_ORIENTATION:
            return self.native_width
        else:
            return self.native_height

    @property
    def is_on(self):
        return self.on
        
    def switch_on(self):
        self.on = True
        
    def switch_off(self):
        self.on = False
        
    def toggle(self):
        self.on = not self.is_on

    def rotate_to(self, rotation):
        if rotation < self.LEFT_VERTICAL_ORIENTATION or rotation > self.BOTTOM_HORIZONTAL_ORIENTATION:
            return
        
        self.rotation = rotation
        
        self.oled.rotation = self.rotation

    def is_inverted(self):
        return self.background == 1
        
    def invert(self):
        self.background = 0 if self.background else 1
        self.foreground = 0 if self.foreground else 1
        
    def display(self):
        if self.is_on:
            self.oled.show()
        
    def clear(self, colour=None):
        if self.is_on:
            # To ensure that any supplied colour is either 0 or 1 use int(colour > 0)
            self.oled.fill(self.background if colour == None else int(colour > 0))

    def pixel(self, x, y, colour=None):
        if self.is_on:
            self.oled.pixel(x, y, self.foreground if colour == None else int(colour > 0))
        
    def fill(self, x, y, w, h, colour=None):
        if self.is_on:
            self.oled.fill_rect(x, y, w, h, self.foreground if colour == None else int(colour > 0))
        
    def rect(self, x, y, w, h, colour=None):
        if self.is_on:
            self.oled.rect(x, y, w, h, self.foreground if colour == None else int(colour > 0))
        
    def hline(self, x, y, w, colour=None):
        if self.is_on:
            self.oled.hline(x, y, w, self.foreground if colour == None else int(colour > 0))
        
    def vline(self, x, y, h, colour=None):
        if self.is_on:
            self.oled.vline(x, y, h, self.foreground if colour == None else int(colour > 0))
        
    def line(self, x0, y0, x1, y1, colour=None):
        if self.is_on:
            self.oled.line(x0, y0, x1, y1, self.foreground if colour == None else int(colour > 0))
        
    def text(self, text, x, y, colour=None):
        if self.is_on:
            self.oled.text(text, x, y, self.foreground if colour == None else int(colour > 0), font_name="/devices/font5x8.bin")

    def scroll(self, dx=0, dy=0):
        if self.is_on:
            self.oled.scroll(dx, dy)

    def action_buttons(self, datetime=None):
        if self.use_a_button:
            if not self.button_a_pin.value and self.button_a_callback:
                self.button_a_callback(datetime=datetime)

        if self.use_b_button:
            if not self.button_b_pin.value and self.button_b_callback:
                self.button_b_callback(datetime=datetime)
        
        if self.use_c_button:
            if not self.button_c_pin.value and self.button_c_callback:
                self.button_c_callback(datetime=datetime)
