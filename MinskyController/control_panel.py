# Author: Chris Knowles
# File: control_panel.py
# Version: 1.0.0
# Notes: Panel that contains widgets for controlling this app and MinskyBot operation

# imports
import tkinter as tk


# Classes
class ControlPanel(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        self.init_frame()

    def init_frame(self):
        # Set the size of this frame
        self.config(width=195, height=510, background="Red")

        # Place frame at specified location on master frame
        self.place(x=410, y=9)

        # Build all the widgets on this frame
        self.build_widgets()

    def build_widgets(self):
        # Creating the "Shutdown" button instance - this is initially disabled until the bot is deemed
        # to be active, then it is activated
        self.shutdown_button = tk.Button(self, width=10, height=1, text="Shutdown", state="disabled",
                                         command=self.shutdown_cmd)

        # Placing the widgets on the frame
        self.shutdown_button.place(x=30, y=20)

    # Delegate this command to the master frame function for the command
    def shutdown_cmd(self):
        self.master.shutdown_cmd()

    # Invoke when the bot publishes its status as active
    def bot_is_active(self):
        for widget in self.winfo_children():
            widget.configure(state="active")

    # Invoke when the bot publishes its status as shutdown
    def bot_is_shutdown(self):
        for widget in self.winfo_children():
            widget.configure(state="disable")
