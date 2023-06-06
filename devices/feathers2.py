"""
Author: Chris Knowles
File: feathers2.py
Version: 1.0.0
Notes: Base module for all FeatherS2 CircuitPython application code
"""
# Imports
import sys
import microcontroller
import rtc
import board
import busio
import array
import math
import wifi
import ipaddress
import socketpool as sp
import adafruit_minimqtt.adafruit_minimqtt as mm
from time import struct_time, monotonic_ns
from digitalio import DigitalInOut
from micropython import const
from adafruit_binascii import hexlify

class RunStates:
    NOT_STARTED = 1
    STARTING = 2
    INITIALISING = 3
    LOOPING = 4
    DEINITIALISING = 5
    SHUTTING_DOWN = 6

class FeatherS2:
    # Names for days of the week
    DAY_NAMES = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    )

    # Default value for sleep period (in seconds) set at 100ms
    _DEFAULT_LOOP_SLEEP_TIME = 0.1

    def __init__(self):
        self.debug_on = None
        self.i2c_frequency = None
        self.spi_frequency = None
        self.use_wifi = None
        self.use_mqtt = None
        self.wifi_timeout = None
        self.wifi_retries = None
        self.wifi_ssid = None
        self.wifi_password = None
        self.mqtt_broker = None
        self.mqtt_port = None
        self.mqtt_username = None
        self.mqtt_password = None
        self.apply_dst = None
        self.spi = None
        self.i2c = None
        self.rtc = None
        self.mqtt_id = None
        self.mqtt_client = None
        self.finished = None
        self.exit_code = None
        self.run_state = None
        self.timers = None

    @property
    def ident(self):
        return FeatherS2.decode_address(microcontroller.cpu.uid)

    @property
    def wifi_mac_address(self):
        return FeatherS2.decode_address(wifi.radio.mac_address)
        
    @property
    def wifi_is_enabled(self):
        return wifi.radio.enabled

    @property
    def wifi_access_point(self):
        return wifi.radio.ap_info

    @property
    def wifi_ip_address(self):
        return wifi.radio.ipv4_address
        
    @property
    def wifi_is_connected(self):
        return True

    def startup(self):
        # Import properties from the secrets module or set them to default values
        # if no secrets module available
        try:
            from secrets import secrets

        except ImportError:
            # Create a defaults secrets dictionary
            secrets = {
                "debug_on" : True,
                "i2c_frequency" : 0,
                "spi_frequency" : 0,
                "use_wifi" : False,
                "use_mqtt" : False,
                "wifi_timeout" : 0,
                "wifi_retries" : 0,
                "ssid" : "",
                "password" : "",
                "mqtt_broker" : "",
                "mqtt_port" : 1883,
                "mqtt_username" : None,
                "mqtt_password" : None,
                "apply_dst" : False
            }

        # Are debug messages sent to serial terminal?
        self.debug_on = secrets["debug_on"]
        # Frequency to set the hardware I2C
        self.i2c_frequency = secrets["i2c_frequency"]
        # Frequency to set the hardware SPI
        self.spi_frequency = secrets["spi_frequency"]
        # Is WIFI support required?
        self.use_wifi = secrets["use_wifi"]
        # Is MQTT support required?
        self.use_mqtt = secrets["use_mqtt"]
        # Timeout to use when connecting to WiFi access point
        self.wifi_timeout = secrets["wifi_timeout"]
        # Number of retries when trying to connect to WiFi access point
        self.wifi_retries = secrets["wifi_retries"]
        # WIFI access point SSID and password
        self.wifi_ssid = secrets["ssid"]
        self.wifi_password = secrets["password"]
        # MQTT broker address, username and password
        self.mqtt_broker = secrets["mqtt_broker"]
        self.mqtt_port = secrets["mqtt_port"]
        self.mqtt_username = secrets["mqtt_username"]
        self.mqtt_password = secrets["mqtt_password"]
        # Should the RTC apply DST (True) or always use UTC (False)
        self.apply_dst = secrets["apply_dst"]

        if self.debug_on:
            print("Debug messages are ON")
            print("\nDevice Identifier:  {0}".format(self.ident))
            print("Device Platform:    {0}".format(sys.platform))
            print("Device Interpreter: {0} ver{1}.{2}.{3}".format(sys.implementation[0], sys.implementation[1][0],
                                                                  sys.implementation[1][1], sys.implementation[1][2]))

        # Hardware I2C bus object instance, use default frequency if self.i2c_frequency is 0 or negative
        if self.i2c_frequency > 0:
            self.i2c = busio.I2C(board.SCL, board.SDA, frequency=self.i2c_frequency)
        else:
            self.i2c = busio.I2C(board.SCL, board.SDA)

        # Hardware SPI bus object instance, use default frequency if self.spi_frequency is 0 or negative
        self.spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        if self.spi_frequency > 0:
            while not self.spi.try_lock():
                pass
            
            self.spi.configure(baudrate=self.spi_frequency)
            
            self.spi.unlock()

        if self.debug_on:
            print("\nSPI Frequency: {0:.2f}MHz".format(float(self.spi.frequency) / 1000000.0))
        
        if self.use_wifi:
            wifi_secrets = {
                "wifi_timeout" : self.wifi_timeout,
                "wifi_retries" : self.wifi_retries,
                "ssid" : self.wifi_ssid,
                "password" : self.wifi_password
            }

        if self.use_mqtt:
            # Allocate the MQTT client identifier based on the identifier of the MCU device
            self.mqtt_id = "MQTT-ID-{0}".format(self.ident)

        # Instantiate the real-time clock (RTC), this will initialise the date time to the base value
        # of 00:00:00 01-01-2000 (seconds:minutes:hours day-month-year)
        self.rtc = rtc.RTC()

        # Control variable that is checked to determine if the main app loop should continue, note
        # that any derived class from the App should use this property to control the way the
        # application manages its run time life cycle
        self.finished = False

        # Exit code to show at the completion of the app, code of 0 means all OK whilst any otherwise
        # code indicates an error before completing, assume all OK initially
        self.exit_code = 0

        # Current state of the run time life cycle of the app, this can be one of the values from the
        # RunStates enumeration class and changes as the app progresses
        self.run_state = RunStates.NOT_STARTED
        
        # Dictionary of timers which are keyed by the name of the timer instance (which means this name
        # is unique in the timers dictionary)
        self.timers = {}

    def shutdown(self):
        if self.debug_on:
            # Print details of app completion to the connected console
            print("\nTerminated with code: {0} <OK>".format(self.exit_code))

    # Public methods
    def run(self):
        try:
            # App run time life cycle
            self.run_state = RunStates.STARTING
            self.startup()

            self.run_state = RunStates.INITIALISING
            self.init()

            self.run_state = RunStates.LOOPING
            while not self.finished:
                self.update_timers()
                self.loop()

            self.run_state = RunStates.DEINITIALISING
            self.deinit()

            self.run_state = RunStates.SHUTTING_DOWN
            self.shutdown()
        except Exception as ex:
            if self.debug_on:
                # Print the details of the exception to the connected console
                sys.print_exception(ex)

            # Use the current run state ordinal value to provide the exit_code, which will remain
            # at 0 if no exception is raised
            self.exit_code = self.run_state

            # Check if the exception occurred before the shutdown() method of the app completed
            if self.run_state < RunStates.SHUTTING_DOWN:
                # Deinitialise the device
                self.deinit()

                if self.debug_on:
                    # Print details of app completion to the connected console
                    print("\nTerminated with code: {0} <ERROR>".format(self.exit_code))

    def finish(self):
        """
        Use this method to set the finished flag to True
        """
        self.finished = True

    def init(self):
        """
        To be overriden by the derived app class
        """
        pass

    def loop(self):
        """
        To be overriden by the derived app class
        """
        pass

    def deinit(self):
        """
        To be overriden by the derived app class
        """
        pass
    
    def update_timers(self):
        for timer in self.timers.values():
            timer.update()
                
    def add_timer(self, period, callback, name=None, rtc=None):
        if not name or not name in self.timers:
            timer = Timer(period, callback, name, rtc)
            self.timers[timer.name] = timer
            return timer
            
        return None
    
    def remove_timer(self, name):
        if name in self.timers:
            del self.timers[name]
    
    def remove_timers(self, names):
        for name in names:
            self.remove_timer(name)    
    
    def remove_all_timers(self):
        self.timers.clear()
    
    def has_timer(self, name):
        return name in self.timers
    
    def get_timer(self, name):
        if self.has_timer(name):
            return self.timers[name]
        
        return None
    
    def start_timer(self, name):
        if self.has_timer(name):
            self.get_timer(name).start()
    
    def stop_timer(self, name):
        if self.has_timer(name):
            self.get_timer(name).stop()
    
    def pause_timer(self, name):
        if self.has_timer(name):
            self.get_timer(name).pause()
    
    def resume_timer(self, name):
        if self.has_timer(name):
            self.get_timer(name).resume()
    
    def start_timers(self, names):
        for name in names:
            self.start_timer(name)
    
    def stop_timers(self, names):
        for name in names:
            self.stop_timer(name)
    
    def pause_timers(self, names):
        for name in names:
            self.pause_timer(name)
    
    def resume_timers(self, names):
        for name in names:
            self.resume_timer(name)
    
    def start_all_timers(self):
        for timer in self.timers.values():
            timer.start()
    
    def stop_all_timers(self):
        for timer in self.timers.values():
            timer.stop()
    
    def pause_all_timers(self):
        for timer in self.timers.values():
            timer.pause()
    
    def resume_all_timers(self):
        for timer in self.timers.values():
            timer.resume()

    def connect_to_wifi(self):
        if self.debug_on:
            print("MAC Address: {0}".format(self.wifi_mac_address))
            print("WiFi is {0}".format("being used" if self.use_wifi else "not being used")) 
            print("WiFi is {0}".format("enabled" if self.wifi_is_enabled else "not enabled")) 

        if not self.use_wifi or not self.wifi_is_enabled:
            return False

        if self.debug_on:
            sn = wifi.radio.start_scanning_networks()

            for n in sn:
                print(n.ssid)
                
            sn = wifi.radio.stop_scanning_networks()

        count = 0
        while not self.wifi_access_point and count < self.wifi_retries:
            if self.debug_on:
                print("WiFi connection attempt {0}".format(count + 1))
            
            try:
                wifi.radio.connect(ssid=self.wifi_ssid, password=self.wifi_password.encode("utf-8"), timeout=self.wifi_timeout)
            except Exception as ex:
                print(ex)
                count += 1

        if not self.wifi_ip_address:
            return False
        
        if self.debug_on:
            print("IP Address : {0}".format(self.wifi_ip_address))
            print("AP Info: {0} {1} {2} {3}".format(self.wifi_access_point.ssid,
                                                    FeatherS2.decode_address(self.wifi_access_point.bssid),
                                                    self.wifi_access_point.rssi,
                                                    self.wifi_access_point.channel))

        return True

    def register_to_mqtt(self, broker, port, username=None, password=None,
                         is_ssl=True, keep_alive=60, ssl_context=None):
        if not self.use_wifi or not self.wifi_is_enabled or not self.use_mqtt:
            return False
        
        try:        
            # Initialize MQTT interface with the WiFi interface through the SocketPool allocation of sockets
            self.mqtt_client = mm.MQTT(socket_pool=sp.SocketPool(wifi.radio), broker=broker, port=port,
                                       username=username, password=password, client_id=self.mqtt_id,
                                       is_ssl=is_ssl, keep_alive=keep_alive, ssl_context=ssl_context)
            
            # Setup the callback methods to act as stubs and be overriden in the main application
            self.mqtt_client.on_connect = self.on_mqtt_connected
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnected
            self.mqtt_client.on_subscribe = self.on_mqtt_subscribe
            self.mqtt_client.on_unsubscribe = self.on_mqtt_unsubscribe
            self.mqtt_client.on_publish = self.on_mqtt_publish
            self.mqtt_client.on_message = self.on_mqtt_message
            
            # Connect the client to the MQTT broker
            self.mqtt_client.connect()
        except Exception as ex:
            print(ex)
            return False

        return True

    def on_mqtt_connected(self, client, userdata, flags, rc):
        pass

    def on_mqtt_disconnected(self, client, userdata, rc):
        pass

    def on_mqtt_subscribe(self, client, userdata, topic, granted_qos):
        pass

    def on_mqtt_unsubscribe(self, client, userdata, topic, pid):
        pass

    def on_mqtt_publish(self, client, userdata, topic, pid):
        pass

    def on_mqtt_message(self, client, topic, message):
        pass

    def set_rtc_by_datetime(self, datetime=(2000, 1, 1, 0, 0, 0, 0, -1, -1)):
        """
        RTC will be set with the provided (year, month, day, hour, minute, seconds, day_number (0 - 6),
        year_day_number (1 - 366), daylight_saving) tuple, -1 for year_day_number or daylight_saving
        means 'not known' and daylight_saving is not implemented, if no tuple is provided then set the
        RTC to the base datetime of 00:00:00 01-01-2000, note - there is currently no timezone support
        in CircuitPython, so time.localtime() will return UTC time as if it was time.gmtime()
        """
        self.rtc.datetime = struct_time(datetime)

    def reset_rtc(self):
        """
        RTC reset helper method
        """
        return self.set_rtc_by_datetime()
        
    @staticmethod
    def decode_address(addr, sep=":"):
        s = ""
        for b in addr:
            s += "{0:02x}{1}".format(b, sep)

        return s[:-1]


class Timer:
    name_counter = 0
    
    def __init__(self, period, callback, name=None, rtc=None):
        if name:
            self.name = name
        else:
            self.name = "Timer-{0}".format(Timer.name_counter)
            Timer.name_counter += 1
            
        self.period = period
        self.callback = callback
        self.rtc = rtc
        self.trigger_count = 0
        self.running = False
        self.paused = False
        self.duration = 0.0
        self.before = 0.0
    
    def reset(self):
        self.trigger_count = 0
        self.duration = 0.0
        self.before = monotonic_ns()
    
    def start(self):
        self.reset()
        self.running = True
        self.paused = False
        
    def stop(self):
        self.running = False
        self.paused = False
        self.reset()
        
    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        self.before = monotonic_ns()
        
    def update(self):
        if self.running and not self.paused:
            now = monotonic_ns()
            self.duration += now - self.before
            
            if self.duration >= self.period * 1000000:
                now_as_datetime = None
                if self.rtc:
                    now_as_datetime = self.rtc.datetime
                self.callback(source=self, triggered_at=now_as_datetime)
                after = monotonic_ns()
                self.duration = after - now
                self.trigger_count += 1
                self.before = after
            else:
                self.before = now

    def __str__(self):
        if self.running:
            if self.paused:
                return "{0} {1} p:{2} d:{3}".format(self.name, "Running and paused", self.period, self.duration)
            else:
                return "{0} {1} p:{2} d:{3}".format(self.name, "Running not paused", self.period, self.duration)

        return "{0} {1} p:{2}".format(self.name, "Not running", self.period)
