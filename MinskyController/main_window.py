# Author: Chris Knowles
# File: main_window.py
# Version: 1.0.0
# Notes: Main window for MinskyBot controller application using TKinter GUI library

# imports
import tkinter as tk
import tkinter.messagebox as tkmb
import platform, subprocess
import paho.mqtt.client as mqtt
from datetime import datetime
from threading import Timer
from motion_panel import MotionPanel
from status_panel import StatusPanel
from control_panel import ControlPanel


# Global Functions
def ping(host_or_ip, packets=1, timeout=1000):
    """
    Calls system "ping" command, returns True if ping succeeds.
    Required parameter: host_or_ip (str, address of host to ping)
    Optional parameters: packets (int, number of retries), timeout (int, ms to wait for response)
    Does not show any output, either as popup window or in command line.
    Python 3.5+, Windows and Linux compatible (Mac not tested, should work)
    """
    # The ping command is the same for Windows and Linux, except for the "number of packets" flag.
    if platform.system().lower() == 'windows':
        command = ['ping', '-n', str(packets), '-w', str(timeout), host_or_ip]
        # run parameters: capture output, discard error messages, do not show window
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        # 0x0800000 is a windows-only Popen flag to specify that a new process will not create a window.
        # On Python 3.7+, you can use a subprocess constant:
        #   result = subprocess.run(command, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # On windows 7+, ping returns 0 (ok) when host is not reachable; to be sure host is responding,
        # we search the text "TTL=" on the command output. If it's there, the ping really had a response.
        return result.returncode == 0 and b'TTL=' in result.stdout
    else:
        command = ['ping', '-c', str(packets), '-w', str(timeout), host_or_ip]
        # run parameters: discard output and error messages
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        return result.returncode == 0


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


# classes
class MainWindow(tk.Frame):
    """
    Useful URLs
    -----------
    Main Tk documentation: https://www.tcl.tk/man/tcl8.6/TkCmd/contents.htm
    Tkinter tutorial: https://www.tutorialspoint.com/python/python_gui_programming.htm
    Colour names: https://wiki.tcl-lang.org/page/Color+Names%2C+running%2C+all+screens
    More on styling: https://effbot.org/tkinterbook/tkinter-widget-styling.htm
                     http://effbot.org/zone/tkinter-option-database.htm
    """
    KUMQUAT_PI_IP = "192.168.235.1"  # AP is Kumquat Pi
    HIVE_MQTT_IP = "broker.hivemq.com"  # AP is Kumquat Pi
    # CURRENT_IP = KUMQUAT_PI_IP  # Used for MQTT messages
    CURRENT_IP = HIVE_MQTT_IP  # Used for MQTT messages

    MQTT_BROKER_PORT = 1883  # MQTT broker port number
    MQTT_REQUEST_SYNC_TOPIC = "minskybot/REQUEST_SYNC_TOPIC"
    MQTT_TIME_SYNC_TOPIC = "minskybot/TIME_SYNC_TOPIC"
    MQTT_SPEED_SYNC_TOPIC = "minskybot/SPEED_SYNC_TOPIC"
    MQTT_COMMAND_TOPIC = "minskybot/COMMAND_TOPIC"
    MQTT_STATUS_TOPIC = "minskybot/STATUS_TOPIC"

    TIME_SYNC_PERIOD = 60  # Period of the time sync publishing (in seconds)

    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.quit_cmd)

        # if not ping(MainWindow.CURRENT_IP):
        #     self.master.withdraw()
        #     tkmb.showinfo("MQTT Broker Connection Error",
        #                   "Cannot connect to MQTT broker at IP Address: {0}, aborting".format(MainWindow.CURRENT_IP))
        #     quit(0)

        tk.Frame.__init__(self, self.master)

        self.bot_active = False

        self.time_sync_timer = None

        self.motion_panel = None

        self.shutdown_button = None
        self.quit_button = None

        self.main_menu = None
        self.main_menu_file = None
        self.main_menu_control = None
        self.main_menu_help = None

        self.init_window()

        self.broker_url = MainWindow.CURRENT_IP  # As allocated above
        self.broker_port = MainWindow.MQTT_BROKER_PORT

        self.__client_p = mqtt.Client(client_id="{0}-P".format("MinskyController"))
        self.__client_s = mqtt.Client(client_id="{0}-S".format("MinskyController"))
        self.client_p.on_connect = self.on_client_p_connect
        self.client_p.on_disconnect = self.on_client_p_disconnect
        self.client_s.on_connect = self.on_client_s_connect
        self.client_s.on_disconnect = self.on_client_s_disconnect

        try:
            self.client_p.connect(host=self.broker_url, port=self.broker_port)
            self.client_s.connect(host=self.broker_url, port=self.broker_port)
            self.client_s.subscribe([(MainWindow.MQTT_REQUEST_SYNC_TOPIC, 0)])
            self.client_s.message_callback_add(MainWindow.MQTT_REQUEST_SYNC_TOPIC, self.on_request_sync_topic)
            self.client_s.subscribe([(MainWindow.MQTT_STATUS_TOPIC, 0)])
            self.client_s.message_callback_add(MainWindow.MQTT_STATUS_TOPIC, self.on_status_topic)

            self.client_p.loop_start()
            self.client_s.loop_start()

            # Start a continuously running timer to send time sync message to subscribers
            self.time_sync_timer = RepeatTimer(MainWindow.TIME_SYNC_PERIOD, self.time_sync_notifier)
            self.time_sync_timer.start()

            # Publish the initial value for the MotionPanel set_speed_scl widget
            self.set_speed_cmd(self.motion_panel.set_speed_scl.get())
        except Exception as ex:
            print(ex)
            tkmb.showinfo("Connection Error", ex)
            self.quit_cmd()

    @property
    def client_p(self):
        return self.__client_p

    @property
    def client_s(self):
        return self.__client_s

    def init_window(self):
        # Change size of the main window
        self.master.geometry("1280x620+320+265")

        # Changing the title of the main window
        self.master.title("MinskyBot Controller")

        # Allowing the main window to take the full space of the root window
        self.pack(fill=tk.BOTH, expand=1)

        # Add panels to main window
        self.add_panels()

        # Build main menu
        self.build_main_menu()

    def add_panels(self):
        # Create the "Motion Panel"
        self.motion_panel = MotionPanel(self)

        # Create the "Control Panel"
        self.control_panel = ControlPanel(self)

        # Create the "Status Panel"
        self.status_panel = StatusPanel(self)

        # Creating the "Quit" button instance
        self.quit_button = tk.Button(self, width=10, height=1, text="Quit", command=self.quit_cmd)

        # Placing the button on the main window
        self.quit_button.place(x=16, y=542)

    def build_main_menu(self):
        # Creating a "Main Menu" instance
        self.main_menu = tk.Menu(self.master)
        self.master.config(menu=self.main_menu)

        # Create the "File" sub-menu instance
        self.main_menu_file = tk.Menu(self.main_menu)

        # Adds a command to the "File" sub-menu, calling it "Quit", and the
        # command it runs on event is quit_cmd()
        self.main_menu_file.add_command(label="Quit", command=self.quit_cmd)

        # Added "File" sub-menu to the "Main Menu"
        self.main_menu.add_cascade(label="File", menu=self.main_menu_file)

        # Create the "Motion" sub-menu instance
        self.main_menu_motion = tk.Menu(self.main_menu)

        # Adds a command to the "Motion" sub-menu, calling it "Increment Speed", and the
        # command it runs on event is increment_speed_cmd()
        self.main_menu_motion.add_command(label="Increment Speed", command=self.increment_speed_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Decrement Speed", and the
        # command it runs on event is decrement_speed_cmd()
        self.main_menu_motion.add_command(label="Decrement Speed", command=self.decrement_speed_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Halt Speed", and the
        # command it runs on event is halt_cmd()
        self.main_menu_motion.add_command(label="Halt Speed", command=self.halt_speed_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Straight On", and the
        # command it runs on event is straight_on_cmd()
        self.main_menu_motion.add_command(label="Straight On", command=self.straight_on_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Fast Rotate Left", and the
        # command it runs on event is fast_rotate_left_cmd()
        self.main_menu_motion.add_command(label="Fast Rotate Left", command=self.fast_rotate_left_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Rotate Left", and the
        # command it runs on event is rotate_left_cmd()
        self.main_menu_motion.add_command(label="Rotate Left", command=self.rotate_left_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Rotate Right", and the
        # command it runs on event is rotate_right_cmd()
        self.main_menu_motion.add_command(label="Rotate Right", command=self.rotate_right_cmd)

        # Adds a command to the "Motion" sub-menu, calling it "Fast Rotate Right", and the
        # command it runs on event is fast_rotate_right_cmd()
        self.main_menu_motion.add_command(label="Fast Rotate Right", command=self.fast_rotate_right_cmd)

        # Added "Motion" sub-menu to the "Main Menu"
        self.main_menu.add_cascade(label="Motion", menu=self.main_menu_motion)

        # Create the "Help" sub-menu instance
        self.main_menu_help = tk.Menu(self.main_menu)

        # Adds a command to the "Help" sub-menu option, calling it "About", and the
        # command it runs on event is about_cmd
        self.main_menu_help.add_command(label="About", command=self.about_cmd)

        # Added "Help" sub-menu to the "Main Menu"
        self.main_menu.add_cascade(label="Help", menu=self.main_menu_help)

    def set_speed_cmd(self, value=0.0):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="set_speed|{0}".format(value),
                              qos=0, retain=False)

    def increment_speed_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC,
                              payload="increment_speed|{0}".format(MotionPanel.SPEED_DELTA_VALUE),
                              qos=0, retain=False)

    def decrement_speed_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC,
                              payload="decrement_speed|{0}".format(MotionPanel.SPEED_DELTA_VALUE),
                              qos=0, retain=False)

    def halt_speed_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="halt_speed", qos=0, retain=False)

    def straight_on_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="straight_on", qos=0, retain=False)

    def fast_rotate_left_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="fast_rotate_left", qos=0, retain=False)

    def rotate_left_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="rotate_left", qos=0, retain=False)

    def rotate_right_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="rotate_right", qos=0, retain=False)

    def fast_rotate_right_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="fast_rotate_right", qos=0, retain=False)

    def shutdown_cmd(self):
        self.client_p.publish(topic=MainWindow.MQTT_COMMAND_TOPIC, payload="shutdown", qos=0, retain=False)

    def quit_cmd(self):
        # Cancel time sync timer
        if self.time_sync_timer:
            self.time_sync_timer.cancel()

        # Disconnect from MQTT broker
        if self.client_p:
            self.client_p.disconnect()
            self.client_p.loop_stop()

        if self.client_s:
            self.client_s.disconnect()
            self.client_s.loop_stop()

        self.master.destroy()

    @staticmethod
    def about_cmd():
        tkmb.showinfo("About", "MinskyBot Controller v1.0")

    def time_sync_notifier(self):
        self.client_p.publish(topic=MainWindow.MQTT_TIME_SYNC_TOPIC,
                              payload=datetime.now().strftime("%Y|%m|%d|%H|%M|%S|%w|%j|-1"),
                              qos=0, retain=False)

    def on_client_p_connect(self, client, userdata, flags, rc):
        print("Client P: {0}    connected with code {1}".format(client._client_id.decode('utf-8'), rc))

    def on_client_p_disconnect(self, client, userdata, rc):
        print("Client P: {0} disconnected with code {1}".format(client._client_id.decode('utf-8'), rc))

    def on_client_s_connect(self, client, userdata, flags, rc):
        print("Client S: {0}    connected with code {1}".format(client._client_id.decode('utf-8'), rc))

    def on_client_s_disconnect(self, client, userdata, rc):
        print("Client S: {0} disconnected with code {1}".format(client._client_id.decode('utf-8'), rc))

    def on_request_sync_topic(self, client, userdata, message):
        # Synchronise with the publisher
        self.client_p.publish(topic=MainWindow.MQTT_TIME_SYNC_TOPIC,
                              payload=datetime.now().strftime("%Y|%m|%d|%H|%M|%S|%w|%j|-1"),
                              qos=0, retain=False)
        self.client_p.publish(topic=MainWindow.MQTT_SPEED_SYNC_TOPIC,
                              payload="{0}".format(self.motion_panel.set_speed_scl.get()),
                              qos=0, retain=False)

    def on_status_topic(self, client, userdata, message):
        status = message.payload.decode().split("|")

        if len(status) > 1:
            eval("self.{0}_status({1})".format(status[0], status[1:]))
        else:
            eval("self.{0}_status()".format(status[0]))

    def shutdown_status(self):
        if self.bot_active:
            self.bot_active = False
            self.motion_panel.bot_is_shutdown()
            self.control_panel.bot_is_shutdown()
        print("MinskyBot has shutdown")

    def telemetry_status(self, args):
        if not self.bot_active:
            self.bot_active = True
            self.motion_panel.bot_is_active()
            self.control_panel.bot_is_active()
        print("[MinskyBot: {0}] [left throttle: {1}] [right throttle: {2}]".format(int(args[0]),
              float(args[1]), float(args[2])))
        # self.status_panel.update_telemetry([float(args[0]), float(args[1]), float(args[2]), float(args[3])])

    def message_status(self, args):
        print("MinskyBot message: {0}".format(args[0]))
