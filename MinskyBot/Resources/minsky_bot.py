# Imports
import time
from machine import Pin
from huzzah32_app import App
from seesaw import Seesaw

# Classes
class MainApp(App):
    def init(self):
        # Initialise SeeSaw chip on Crickit board
        self.seesaw = Seesaw(self.huzzah32.i2c)
        
        # Pin that integrated LED is connected to, taken from the Huzzah32 instance
        # available in your custom class (inherited from App)
        self.led_pin = self.huzzah32.PIN_13
    
        # Set pin to be a digital output pin with value 0
        self.led_pin.init(mode=Pin.OUT, value=0)
        
        # Capacitive touch threshold
        self.ctt = 850
        
        # LED blink counter
        self.count = 0
        
    def loop(self):
        # Get current capacitive touch values and if value is above capacitive touch
        # threshold self.ctt then record as "pressed" 
        ctv = [0] * 4
        ctp = [False] * 4
        for i in range(1, 5):
            ctv[i - 1] = self.seesaw.read_touch(i)
            ctp[i - 1] = ctv[i - 1] > self.ctt
            print("{0} {1}".format(ctv[i - 1], ctp[i - 1]))

        if self.count >= 15 or ctp[0]:
            # Set finished property as True to terminate the main app loop
            self.finish()
        else:
            # Switch on the LED pin
            self.led_pin.value(1)
            print("\t{0: <2} Blink on".format(self.count))
        
            # Sleep for 0.5 second
            time.sleep(0.5)
        
            # Switch off the LED pin
            self.led_pin.value(0)
            print("\t{0: <2} Blink off".format(self.count))

            # Sleep for 0.5 second
            time.sleep(0.5)
        
            # Increment count
            self.count += 1
    
    def deinit(self):
        # In this specific implementation the deint() method does nothing, only included
        # for completeness sake
        pass

# Program entrance function
def main():
    # Instantiate an instance of the custom App class (MainApp class) with the following
    # property values:-
    #
    #   name: "LED Blinky", this should be a maximum of 14 characters else it is truncated
    #
    app = MainApp(name="LED Blinky")
    
    # Run the app
    app.run()

# Invoke main() program entrance
if __name__ == "__main__":
    # execute only if run as a script
    main()







"""
#-----------------------------------------------------------------------------------------------------------------------------------
# File: led_blinky_v2.py
# Description: LED Blinky second version using inherited IoTApp class
# Author: Chris Knowles, University of Sunderland
# Date: Jan 2019


# main.py - code to test the Adafruit CRICKIT board with
# the BBC micro:bit and MicroPython (NOT CircuitPython)
# MIT License by Limor Fried and Mike Barela, 2019
# This code requires the seesaw.py module as a driver
import time
import seesaw

seesaw.init()
while True:
    # Touch test - check with the Mu plotter!
    print("Touch: \n(", end="")
    for i in range(1, 5):
        print(seesaw.read_touch(i), end=", \t")
    print(")")

    # analog read signal test - assumes analog input pin 8
    print("Analog signal:\n(", end="")
    print(seesaw.analog_read(8), end=", \t")
    print(")")

    seesaw.write_digital(2, 0)  # Assumes LED on Signal pin 2
    time.sleep(0.1)
    seesaw.write_digital(2, 1)
    time.sleep(0.1)

    if seesaw.read_digital(7):  # Assumes button on Signal pin 7
        print("pin high")
    else:
        print("pin low")

    # Servo test - assumes servo on Servo position 1 on CRICKIT
    seesaw.servo(1, 0, min=0.5, max=2.5)
    time.sleep(0.5)
    seesaw.servo(1, 90, min=0.5, max=2.5)
    time.sleep(0.5)
    seesaw.servo(1, 180, min=0.5, max=2.5)
    time.sleep(0.5)

    # Drive test
    # seesaw.drive(1, 0.2)
    # seesaw.drive(2, 0.4)
    # seesaw.drive(3, 0.6)
    # seesaw.drive(4, 0.8)

    # motor test - assumes a DC motor on CRICKIT Motor 1 terminals
    seesaw.motor(1, 1)
    time.sleep(0.5)
    seesaw.motor(1, 0)
    time.sleep(0.5)
    seesaw.motor(1, -1)
    time.sleep(0.5)
    seesaw.motor(1, 0)

    time.sleep(0.1)
"""