# Author: Chris Knowles
# File: motion_panel.py
# Version: 1.0.0
# Notes: Panel that contains widgets for controlling motion of MinskyBot

# imports
import tkinter as tk


# Classes
class MotionPanel(tk.Frame):
    SPEED_INITIAL_VALUE = 0.0
    SPEED_MIN_VALUE = -1.0
    SPEED_MAX_VALUE = 1.0
    SPEED_DELTA_VALUE = 0.05

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        self.inc_btn = None
        self.dec_btn = None
        self.straight_btn = None
        self.fast_left_btn = None
        self.left_btn = None
        self.right_btn = None
        self.fast_right_btn = None
        self.halt_btn = None
        self.set_speed_scl = None

        self.init_frame()

    def init_frame(self):
        # Set the size of this frame
        self.config(width=390, height=510, background="SeaGreen3")

        # Place frame at specified location on master frame
        self.place(x=16, y=9)

        # Build all the widgets on this frame
        self.build_widgets()

    def build_widgets(self):
        # Creating the "Straight forward/reverse" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.straight_btn = tk.Button(self, width=3, height=2, text="^", state="disabled",
                                      command=self.straight_cmd)

        # Creating the "Increment Speed" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.inc_btn = tk.Button(self, width=3, height=2, text="+", state="disabled",
                                 command=self.inc_cmd)

        # Creating the "Immediate Halt" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.halt_btn = tk.Button(self, width=3, height=2, text="X", state="disabled",
                                  command=self.halt_cmd)

        # Creating the "Decrement Speed" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.dec_btn = tk.Button(self, width=3, height=2, text="-", state="disabled",
                                 command=self.dec_cmd)

        # Creating the "Fast Rotate Left" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.fast_left_btn = tk.Button(self, width=3, height=2, text="<<", state="disabled",
                                       command=self.fast_left_cmd)

        # Creating the "Rotate Left" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.left_btn = tk.Button(self, width=3, height=2, text="<", state="disabled",
                                  command=self.left_cmd)

        # Creating the "Rotate Right" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.right_btn = tk.Button(self, width=3, height=2, text=">", state="disabled",
                                   command=self.right_cmd)

        # Creating the "Fast Rotate Right" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.fast_right_btn = tk.Button(self, width=3, height=2, text=">>", state="disabled",
                                        command=self.fast_right_cmd)

        # Creating the "Set Speed" scale instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.set_speed_scl = tk.Scale(self, length=325, from_=MotionPanel.SPEED_MIN_VALUE,
                                      to=MotionPanel.SPEED_MAX_VALUE, resolution=MotionPanel.SPEED_DELTA_VALUE,
                                      orient=tk.HORIZONTAL, state="disabled")
        self.set_speed_scl.bind("<ButtonRelease-1>", self.set_speed_cmd)
        self.set_speed_scl.set(MotionPanel.SPEED_INITIAL_VALUE)

        # Placing the widgets on the frame
        self.straight_btn.place(x=170, y=10)
        self.inc_btn.place(x=170, y=120)
        self.halt_btn.place(x=170, y=230)
        self.dec_btn.place(x=170, y=340)
        self.fast_left_btn.place(x=30, y=230)
        self.left_btn.place(x=100, y=230)
        self.right_btn.place(x=240, y=230)
        self.fast_right_btn.place(x=310, y=230)
        self.set_speed_scl.place(x=30, y=440)

    # Delegate this command to the master frame function for the command
    def straight_cmd(self):
        self.master.straight_on_cmd()

    # Delegate this command to the master frame function for the command
    def inc_cmd(self):
        self.set_speed_scl.set(self.set_speed_scl.get() + MotionPanel.SPEED_DELTA_VALUE)
        self.master.increment_speed_cmd()

    # Delegate this command to the master frame function for the command
    def halt_cmd(self):
        self.set_speed_scl.set(0.0)
        self.master.halt_speed_cmd()

    # Delegate this command to the master frame function for the command
    def dec_cmd(self):
        self.set_speed_scl.set(self.set_speed_scl.get() - MotionPanel.SPEED_DELTA_VALUE)
        self.master.decrement_speed_cmd()

    # Delegate this command to the master frame function for the command
    def fast_left_cmd(self):
        self.master.fast_rotate_left_cmd()

    # Delegate this command to the master frame function for the command
    def left_cmd(self):
        self.master.rotate_left_cmd()

    # Delegate this command to the master frame function for the command
    def right_cmd(self):
        self.master.rotate_right_cmd()

    # Delegate this command to the master frame function for the command
    def fast_right_cmd(self):
        self.master.fast_rotate_right_cmd()

    # Delegate this command to the master frame function for the command
    def set_speed_cmd(self, event):
        self.master.set_speed_cmd(value=self.set_speed_scl.get())

    # Invoke when setting speed directly (rather than using the set_speed_scl widget)
    def set_speed(self, value):
        self.master.set_speed_cmd(value=value)

    # Invoke when the bot publishes its status as active
    def bot_is_active(self):
        for widget in self.winfo_children():
            widget.configure(state="active")

    # Invoke when the bot publishes its status as shutdown
    def bot_is_shutdown(self):
        for widget in self.winfo_children():
            widget.configure(state="disable")
