"""
Author: Chris Knowles
File: mainapp.py
Version: 1.0.0
Notes: The code.py module executes the method run() from an instance of this MainApp
       class. As such this MainApp class, by inheriting from the relevant device
       base class, overrides the init(), loop() and deinit() methods from the relevant
       device base class and provides the functionality of the application using these
       overriden methods
"""
# Imports
import sys
import os
import board
from time import struct_time, sleep, monotonic_ns

# Make sure the devices package is on the package path
sys.path.append("/devices")
from feathers2 import FeatherS2, Timer  # Relevant device base class

# Make sure that the Crickit singleton has the I2C bus that is instantiated for its
# associated Seesaw object is disconnected leaving the board.SCL and board.SDA pins
# available for the I2C objec tthat is instantiated by the Feather2 class - this is
# a bit how-you-doing but works
from adafruit_crickit import Crickit, crickit
crickit.seesaw.i2c_device.i2c.deinit()
crickit = None

class MainApp(FeatherS2):
    MQTT_REQUEST_SYNC_TOPIC = "minskybot/REQUEST_SYNC_TOPIC"
    MQTT_TIME_SYNC_TOPIC = "minskybot/TIME_SYNC_TOPIC"
    MQTT_SPEED_SYNC_TOPIC = "minskybot/SPEED_SYNC_TOPIC"
    MQTT_COMMAND_TOPIC = "minskybot/COMMAND_TOPIC"
    MQTT_STATUS_TOPIC = "minskybot/STATUS_TOPIC"
    
    SPEED_INITIAL_VALUE = 0.0
    SPEED_DEADZONE = 0.2
    SPEED_MIN_VALUE = -1.0
    SPEED_MAX_VALUE = 1.0
    SPEED_DELTA_VALUE = 0.05

    # Create the MainApp instance as a Singleton to get over the way that CircuitPython
    # eval() function does not recognise local variables, only global variables and
    # class-scoped variables, this isn't really a problem since there will only ever be
    # a single instance of the MainApp object, then in creating any eval() methods these
    # must be static class-scoped functions and use the "MainApp.this" reference in place
    # of "self" in those eval() invoked class-scoped functions (see the static function
    # shutdown_cmd() for an example of how this all ties together
    this = None
    
    def __init__(self):
        # Make sure __init__() from base class is called first
        super().__init__()

        self.use_oled_featherwing = None
        self.use_logger_rtc = None
        self.use_logger_sdcard = None
        self.use_crickit = None
        self.use_crickit_motors = None
        self.use_crickit_motor_1 = None
        self.use_crickit_motor_2 = None
        self.use_crickit_servos = None
        self.use_crickit_servo_1 = None
        self.use_crickit_servo_2 = None
        self.use_crickit_servo_3 = None
        self.oled = None
        self.oled_output = None
        self.app_name = None
        self.use_buttons = []
        self.button_a_pin = None 
        self.button_b_pin = None
        self.button_c_pin = None
        self.pcf8523 = None  # RTC on Adalogger Featherwing
        self.sdcard = None  # SD card reader/writer on Adalogger Featherwing
        self.sdcard_vfs = None
        self.motor_l = None # Left motor controller (FeatherWing Crickit motor 1, +ve throttle is forward)
        self.motor_throttle_l = MainApp.SPEED_INITIAL_VALUE
        self.motor_r = None # Right motor controller (FeatherWing Crickit motor 2, +ve throttle is forward)
        self.motor_throttle_r = MainApp.SPEED_INITIAL_VALUE
        self.servos = [None, None, None]
        self.servo_1 = None
        self.servo_2 = None
        self.servo_3 = None
        
        # Added application-specific properties
        try:
            from secrets import secrets

            if "use_oled_featherwing" in secrets:
                self.use_oled_featherwing = secrets["use_oled_featherwing"]
            else:
                self.use_oled_featherwing = False

            if "verbose_startup" in secrets:
                self.verbose = secrets["verbose_startup"]
            else:
                self.verbose = False

            if "use_logger_sdcard" in secrets:
                self.use_logger_sdcard = secrets["use_logger_sdcard"]
            else:
                self.use_logger_sdcard = False

            if "use_logger_rtc" in secrets:
                self.use_logger_rtc = secrets["use_logger_rtc"]
            else:
                self.use_logger_rtc = False

            if "use_crickit_motor_1" in secrets:
                self.use_crickit_motor_1 = secrets["use_crickit_motor_1"]
            else:
                self.use_crickit_motor_1 = False

            if "use_crickit_motor_2" in secrets:
                self.use_crickit_motor_2 = secrets["use_crickit_motor_2"]
            else:
                self.use_crickit_motor_2 = False

            if "use_crickit_servo_1" in secrets:
                self.use_crickit_servo_1 = secrets["use_crickit_servo_1"]
            else:
                self.use_crickit_servo_1 = False

            if "use_crickit_servo_2" in secrets:
                self.use_crickit_servo_2 = secrets["use_crickit_servo_2"]
            else:
                self.use_crickit_servo_2 = False

            if "use_crickit_servo_3" in secrets:
                self.use_crickit_servo_3 = secrets["use_crickit_servo_3"]
            else:
                self.use_crickit_servo_3 = False

        except ImportError:
            self.use_oled_featherwing = False
            self.verbose = False
            self.use_logger_sdcard = False
            self.use_logger_rtc = False
            self.use_crickit_motor_1 = False
            self.use_crickit_motor_2 = False
            self.use_crickit_servo_1 = False
            self.use_crickit_servo_2 = False
            self.use_crickit_servo_3 = False
        
        # Update the "Singleton" class-scoped reference to refer to "this" object instance
        # and to be used in place of "self" within relevant class-scoped functions
        MainApp.this = self
        
        self.frames = 0

    def init(self):
        # Instantiate application-specific connected device objects
        self.app_name = "MinskyBot"  # Maximum of 18 characters when using font5x8
        if len(self.app_name) > 18:
            self.app_name = self.app_name[:19]
        
        if self.use_oled_featherwing:
            from oledfeatherwing import Oled_FeatherWing as OLED
            
            self.use_buttons = ["A", "B", "C"]
            self.button_a_pin = board.D5 
            self.button_b_pin = board.D21
            self.button_c_pin = board.D20

            self.oled = OLED(i2c=self.i2c,
                             use_buttons=self.use_buttons,
                             button_a_pin=self.button_a_pin,
                             button_b_pin=self.button_b_pin,
                             button_c_pin=self.button_c_pin,
                             button_a_callback=self.action_button_a,
                             button_b_callback=self.action_button_b,
                             button_c_callback=self.action_button_c)

            self.oled_output = ["", "", "", "", "", ""]
        
        if self.oled and self.oled.is_on and self.debug_on and self.verbose:
            self.oled.clear()
            self.oled.fill(0, 0, self.oled.width - 1, 9, 1)  # Each string character is 6.4 x 10.67 pixels 
            self.oled.text("Device: {0}".format("FeatherS2"), 4, 1, 0)
            self.oled.text("{0}".format(sys.implementation[0]), 4, 10)
            self.oled.text("ver{0}.{1}.{2}".format(sys.implementation[1][0], sys.implementation[1][1],
                                                   sys.implementation[1][2]), 4, 20)
            self.oled.display()
            sleep(1)

            self.oled.invert()
            self.oled.clear()
            self.oled.vline(4, 10, 12)
            self.oled.hline(4, 10, self.oled.width - 8)
            self.oled.vline(self.oled.width - 4, 10, 12)
            self.oled.hline(4, 21, self.oled.width - 8)
            self.oled.text(self.app_name, ((self.oled.width - 16 - int(len(self.app_name) * 6.05)) // 2) + 9, 12)
            self.oled.display()
            sleep(1)

        if self.oled:
            if self.oled.is_inverted():
                self.oled.invert()
            self.oled.clear()
            self.oled.display()

        if self.use_logger_rtc:
            from adafruit_pcf8523 import PCF8523
            self.pcf8523 = PCF8523(i2c_bus=self.i2c)
            self.rtc.datetime = self.pcf8523.datetime
        
        now = self.rtc.datetime

        strng = "App {0} began: {1} {2:02}/{3:02}/{4} at {5:02}:{6:02}:{7:02}"
        title_str = strng.format(self.app_name, self.DAY_NAMES[now.tm_wday], now.tm_mday, now.tm_mon, now.tm_year,
                                 now.tm_hour, now.tm_min, now.tm_sec)

        if self.debug_on:
            print(title_str)
            
        if self.use_logger_sdcard:
            from sdcardio import SDCard
            from storage import VfsFat, mount
            self.sdcard = SDCard(spi=self.spi, cs=board.D6, baudrate=8000000)
            self.sdcard_vfs = VfsFat(self.sdcard)
            mount(self.sdcard_vfs, "/sd")

            if self.debug_on:
                print(os.listdir("/sd"))

            now = self.rtc.datetime
                
            with open("/sd/data.csv", "w") as f:
                f.write(title_str + "\n")
                f.write("----------------------------------------------------------\n")
        
            if self.debug_on:
                with open("/sd/data.csv", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        print(line.replace("\n", ""))

        if self.use_wifi:
            if self.debug_on:
                print("IP Address: {0}".format(self.wifi_ip_address))
                print("Connecting to WiFi...")
           
            # Control when to connect to WiFi
            connected = self.connect_to_wifi()

            if self.debug_on:
                print("IP Address: {0}".format(self.wifi_ip_address))
            
            if not connected:
                # Not connected to WiFi so indicate this if debug is on
                if self.debug_on:
                    print("Tried to connect to WiFi SSID [{0}] but failed".format(self.wifi_ssid))
            else:
                if self.use_mqtt:
                    # Ensure MQTT is registered and required subscriptions are made
                    self.register_to_mqtt(broker=self.mqtt_broker, port=self.mqtt_port,
                                          username=self.mqtt_username, password=self.mqtt_password)
                    self.mqtt_client.subscribe(self.MQTT_TIME_SYNC_TOPIC)
                    self.mqtt_client.add_topic_callback(self.MQTT_TIME_SYNC_TOPIC, self.on_time_sync_topic)
                    self.mqtt_client.subscribe(self.MQTT_SPEED_SYNC_TOPIC)
                    self.mqtt_client.add_topic_callback(self.MQTT_SPEED_SYNC_TOPIC, self.on_speed_sync_topic)
                    self.mqtt_client.subscribe(self.MQTT_COMMAND_TOPIC)
                    self.mqtt_client.add_topic_callback(self.MQTT_COMMAND_TOPIC, self.on_command_topic)

                    # Request a time sync via MQTT_REQUEST_SYNC_TOPIC
                    if self.mqtt_client:
                        self.mqtt_client.publish(self.MQTT_REQUEST_SYNC_TOPIC, "time_sync")
                        self.mqtt_client.loop()

        self.use_crickit_motors = self.use_crickit_motor_1 or self.use_crickit_motor_2
                                  
        self.use_crickit_servos = self.use_crickit_servo_1 or self.use_crickit_servo_2 or self.use_crickit_servo_3
                                  
        self.use_crickit = self.use_crickit_motors or self.use_crickit_servos

        if self.use_crickit :
            from adafruit_seesaw.seesaw import Seesaw
            
            self.crickit = Crickit(seesaw=Seesaw(i2c_bus=self.i2c))
            
        if self.use_crickit_motors:
            # Set up motors
            if self.use_crickit_motor_1:
                self.motor_l = self.crickit.dc_motor_1  # Left wheel motor
                self.motor_l.throttle = self.motor_throttle_l
                
            if self.use_crickit_motor_2:    
                self.motor_r = self.crickit.dc_motor_2  # Right wheel motor
                self.motor_r.throttle = self.motor_throttle_r

        if self.use_crickit_servos:
            # Set up servos
            if self.use_crickit_servo_1:
                self.servo_1 = self.servos[0] = self.crickit.servo_1
                self.servo_1.set_pulse_width_range(min_pulse=750, max_pulse=2350)
                self.servo_1.angle = 90
                sleep(1)

            if self.use_crickit_servo_2:
                self.servo_2 = self.servos[1] = self.crickit.servo_2

            if self.use_crickit_servo_3:
                self.servo_3 = self.servos[2] = self.crickit.servo_3

        # Create tick timer and soil sensor reading and start all timers
        self.tick_timer = self.add_timer(name="Tick_Timer", period=5000,
                                         callback=self.tick_timer_callback)
        self.start_all_timers()

        # If debug on then show memory usage
        if self.debug_on:
            def disk_mem_free():
                s = os.statvfs("//")
                return (s[0] * s[3]) / 1048576

            def sram_mem_free(by_percentage=False):
                import gc

                gc.collect()
                F = gc.mem_free()
                A = gc.mem_alloc()
                T = F + A
                P = F / T * 100
    
                if not by_percentage:
                    return (T, A, F, P)
                else:
                    return P

            D = disk_mem_free()
            print("Disk - {0} MB free".format(D))

            T, A, F, P = sram_mem_free()
            print("SRAM - Total: {0}\n       Alloc: {1}\n       Free:  {2} ({3}%)".format(T, A, F, P))
        
        self.frames = 0
        self.triggers = 0
        
    def loop(self):
        # Action any OLED button presses
        if self.oled:
            if self.oled.is_on:
                self.oled.clear()
                
                y_pos = 4
                for output in self.oled_output:
                    self.oled.text(output, 1, y_pos, 1)
                    y_pos += 10

                self.oled.display()
            
            
            now = self.rtc.datetime
            self.oled.action_buttons(now)

        # Poll the MQTT queue if connected
        if self.mqtt_client:
            try:
                self.mqtt_client.loop()
                
                if self.motor_l and self.motor_r:
                    telemetry_str = "{0}|{1}|{2}".format(self.frames, self.motor_throttle_l, self.motor_throttle_r)
                    self.mqtt_client.publish(self.MQTT_STATUS_TOPIC, "telemetry|{0}".format(telemetry_str))
            except Exception as ex:
                if self.debug_on:
                    print("loop: Fubar'd {0}".format(ex))
                    self.mqtt_client = None
#                 self.mqtt_client.unsubscribe(self.MQTT_TIME_SYNC_TOPIC)
#                 self.mqtt_client.remove_topic_callback(self.MQTT_TIME_SYNC_TOPIC)
#                 self.mqtt_client.unsubscribe(self.MQTT_SPEED_SYNC_TOPIC)
#                 self.mqtt_client.remove_topic_callback(self.MQTT_SPEED_SYNC_TOPIC)
#                 self.mqtt_client.unsubscribe(self.MQTT_COMMAND_TOPIC)
#                 self.mqtt_client.remove_topic_callback(self.MQTT_COMMAND_TOPIC)
#                 self.mqtt_client.disconnect()
#                 self.register_to_mqtt(broker=self.CURRENT_IP, port=self.MQTT_BROKER_PORT)
#                 self.mqtt_client.subscribe(self.MQTT_TIME_SYNC_TOPIC)
#                 self.mqtt_client.add_topic_callback(self.MQTT_TIME_SYNC_TOPIC, self.on_time_sync_topic)
#                 self.mqtt_client.subscribe(self.MQTT_SPEED_SYNC_TOPIC)
#                 self.mqtt_client.add_topic_callback(self.MQTT_SPEED_SYNC_TOPIC, self.on_speed_sync_topic)
#                 self.mqtt_client.subscribe(self.MQTT_COMMAND_TOPIC)
#                 self.mqtt_client.add_topic_callback(self.MQTT_COMMAND_TOPIC, self.on_command_topic)
# 
#                 # Request a time sync
#                 if self.mqtt_client:
#                     self.mqtt_client.publish(self.MQTT_REQUEST_SYNC_TOPIC, "")
        
#         if self.servo_1:
#             print("Move servo #1 to 45")
#             self.servo_1.angle = 135
#             sleep(1)
#             print("Move servo #1 to 90")
#             self.servo_1.angle = 180
#             sleep(1)
#             print("Move servo #1 to 135")
#             self.servo_1.angle = 135
#             sleep(1)
#             print("Move servo #1 to 180")
#             self.servo_1.angle = 90
#             sleep(1)
#             print("Move servo #1 to 135")
#             self.servo_1.angle = 45
#             sleep(1)
#             print("Move servo #1 to 90")
#             self.servo_1.angle = 0
#             sleep(1)
#             print("Move servo #1 to 45")
#             self.servo_1.angle = 45
#             sleep(1)
#             print("Move servo #1 to 0")
#             self.servo_1.angle = 90
#             sleep(1)

        # Wait for 10 milliseconds
        sleep(0.01)

        # Increment application loop frame counter
        self.frames += 1

    def deinit(self):
        if self.motor_l:
            self.motor_l.throttle = 0.0
        
        if self.motor_r:
            self.motor_r.throttle = 0.0

        if self.mqtt_client:
            self.mqtt_client.publish(self.MQTT_STATUS_TOPIC, "shutdown")
            self.mqtt_client.loop()

            self.mqtt_client.unsubscribe(self.MQTT_TIME_SYNC_TOPIC)
            self.mqtt_client.remove_topic_callback(self.MQTT_TIME_SYNC_TOPIC)
            self.mqtt_client.unsubscribe(self.MQTT_SPEED_SYNC_TOPIC)
            self.mqtt_client.remove_topic_callback(self.MQTT_SPEED_SYNC_TOPIC)
            self.mqtt_client.unsubscribe(self.MQTT_COMMAND_TOPIC)
            self.mqtt_client.remove_topic_callback(self.MQTT_COMMAND_TOPIC)
            self.mqtt_client.disconnect()

        # Clear OLED display to black
        if self.oled:
            if self.oled.is_inverted():
                self.oled.invert()
            self.oled.clear()
            self.oled.display()

    # Implementations of MQTT callback methods (overriding those in App base class)
    def on_mqtt_connected(self, client, userdata, flags, rc):
        if self.debug_on:
            print("MQTT connected")
        return

    def on_mqtt_disconnected(self, client, userdata, rc):
        if self.debug_on:
            print("MQTT disconnected")
        return

    def on_mqtt_subscribe(self, client, userdata, topic, granted_qos):
        if self.debug_on:
            print("MQTT subscribed to topic: {0}".format(topic))
        return

    def on_mqtt_unsubscribe(self, client, userdata, topic, pid):
        if self.debug_on:
            print("MQTT unsubscribed to topic: {0}".format(topic))
        return

    #def on_mqtt_publish(self, client, userdata, topic, pid):
    #    if self.debug_on:
    #    print("MQTT published to topic: {0}".format(topic))
    #    return

    def on_mqtt_message(self, client, topic, message):
        if self.debug_on:
            print("MQTT Message: {0}\n{1}\n{2} {3}".format(self.ident, client.client_id, topic, message))
        return
        
    def on_time_sync_topic(self, client, topic, message):
        if self.debug_on:
            print("Command: {0}\n{1}\n{2} {3}".format(self.ident, client.client_id, topic, message))

        dt = message.split("|")
        datetime = (int(dt[0]), int(dt[1]), int(dt[2]), int(dt[3]), int(dt[4]), int(dt[5]), int(dt[6]),
                    int(dt[7]), 1 if self.apply_dst else 0)
        self.set_rtc_by_datetime(datetime=datetime)
        
    def on_speed_sync_topic(self, client, topic, message):
        if self.debug_on:
            print("Command: {0}\n{1}\n{2} {3}".format(self.ident, client.client_id, topic, message))

        ss = message.split("|")
        MainApp.set_speed_cmd(ss)
        
    def on_command_topic(self, client, topic, message):
        if self.debug_on:
            print("Command: {0}\n{1}\n{2} {3}".format(self.ident, client.client_id, topic, message))

        cmd = message.split("|")
            
        if len(cmd) > 1:
            eval("MainApp.{0}_cmd({1})".format(cmd[0], cmd[1:]))
        else:
            eval("MainApp.{0}_cmd()".format(cmd[0]))

    @staticmethod
    def restrict_motor_speed(speed):
        if speed < 0.0:
            return max(speed, MainApp.SPEED_MIN_VALUE)
        else:
            return min(speed, MainApp.SPEED_MAX_VALUE)
        

    @staticmethod
    def set_speed_cmd(args):
        speed = MainApp.restrict_motor_speed(float(args[0]))

        MainApp.this.motor_l.throttle = speed
        MainApp.this.motor_throttle_l = MainApp.this.motor_l.throttle
        MainApp.this.motor_r.throttle = speed
        MainApp.this.motor_throttle_r = MainApp.this.motor_r.throttle

    @staticmethod
    def increment_speed_cmd(args):
        delta = float(args[0])
        MainApp.this.motor_l.throttle = MainApp.restrict_motor_speed(MainApp.this.motor_l.throttle + delta)
        MainApp.this.motor_throttle_l = MainApp.this.motor_l.throttle
        MainApp.this.motor_r.throttle = MainApp.restrict_motor_speed(MainApp.this.motor_r.throttle + delta)
        MainApp.this.motor_throttle_r = MainApp.this.motor_r.throttle

    @staticmethod
    def decrement_speed_cmd(args):
        delta = float(args[0])
        MainApp.this.motor_l.throttle = MainApp.restrict_motor_speed(MainApp.this.motor_l.throttle - delta)
        MainApp.this.motor_throttle_l = MainApp.this.motor_l.throttle
        MainApp.this.motor_r.throttle = MainApp.restrict_motor_speed(MainApp.this.motor_r.throttle - delta)
        MainApp.this.motor_throttle_r = MainApp.this.motor_r.throttle

    @staticmethod
    def halt_speed_cmd():
        MainApp.this.motor_l.throttle = 0.0
        MainApp.this.motor_throttle_l = MainApp.this.motor_l.throttle
        MainApp.this.motor_r.throttle = 0.0
        MainApp.this.motor_throttle_r = MainApp.this.motor_r.throttle

    @staticmethod
    def straight_on_cmd():
        if MainApp.this.motor_l.throttle == 0.0:
            MainApp.this.motor_l.throttle = MainApp.this.motor_r.throttle
            MainApp.this.motor_throttle_l = MainApp.this.motor_l.throttle
        else:
            MainApp.this.motor_r.throttle = MainApp.this.motor_l.throttle
            MainApp.this.motor_throttle_r = MainApp.this.motor_r.throttle

    @staticmethod
    def fast_rotate_left_cmd():
        if MainApp.this.motor_l.throttle == 0.0:
            return

#         current_target_speed = self.motor1.target_speed
#         self.motor1.target_speed = 0.0
#         self.motor2.target_speed = current_target_speed

    @staticmethod
    def rotate_left_cmd():
        if MainApp.this.motor_l.throttle == 0.0:
            return

#         current_target_speed = self.motor1.target_speed
#         self.motor1.target_speed = 0.0
#         self.motor2.target_speed = current_target_speed

    @staticmethod
    def rotate_right_cmd():
        if MainApp.this.motor_r.throttle == 0.0:
            return

#         current_target_speed = self.motor2.target_speed
#         self.motor2.target_speed = 0.0
#         self.motor1.target_speed = current_target_speed

    @staticmethod
    def fast_rotate_right_cmd():
        if MainApp.this.motor_r.throttle == 0.0:
            return

#         current_target_speed = self.motor2.target_speed
#         self.motor2.target_speed = 0.0
#         self.motor1.target_speed = current_target_speed

    @staticmethod
    def shutdown_cmd():
        # Note how "MainApp.this" replaces "self"
        MainApp.this.finish()

    def tick_timer_callback(self, source, triggered_at):
        self.triggers += 1
        
        if self.debug_on:
            print("\n{0} triggered {1} time{2}".format(source.name, self.triggers,
                                                       "s" if not self.triggers == 1 else ""))

        if self.debug_on and self.use_wifi:
            import wifi
            print("IP Address: {0}".format(wifi.radio.ipv4_address))

        if self.mqtt_client:
            self.mqtt_client.publish(self.MQTT_REQUEST_SYNC_TOPIC, "Hello from FeatherS2")
            if self.debug_on:
                print("MQTT client OK at {0}".format(self.mqtt_broker))
        else:
            if self.debug_on:
                print("No MQTT client at {0}".format(self.mqtt_broker))

        if self.oled:
            self.oled.fill(16, 32, 8, 8, 1)            
            self.oled.display()
            sleep(0.1)
            self.oled.fill(16, 32, 8, 8, 0)            
            self.oled.display()
    
    def action_button_a(self, datetime):
        if self.debug_on:
            print("Button A pressed!")

    def action_button_b(self, datetime):
        if self.debug_on:
            print("Button B pressed!")

    def action_button_c(self, datetime):
        if self.debug_on:
            print("Button C pressed!")

        MainApp.shutdown_cmd()

    # Temperature converter functions
    @staticmethod
    def celsius_to_fahrenheit(deg_c):  # convert C to F; round to 1 degree C
        return round(((9 / 5) * deg_c) + 32)

    @staticmethod
    def fahrenheit_to_celsius(deg_f):  # convert F to C; round to 1 degree F
        return round((deg_f - 32) * (5 / 9))
