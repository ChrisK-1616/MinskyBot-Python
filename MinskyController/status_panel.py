# Author: Chris Knowles
# File: status_panel.py
# Version: 1.0.0
# Notes: Panel that contains widgets for displaying the status of MinskyBot

# imports
import tkinter as tk


# Classes
class StatusPanel(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master

        self.tspeed_m1_name_lbl = None
        self.mspeed_m1_name_lbl = None
        self.tspeed_m1_value_lbl = None
        self.tspeed_m1_value_var = tk.StringVar()
        self.mspeed_m1_value_lbl = None
        self.mspeed_m1_value_var = tk.StringVar()
        self.tspeed_m2_name_lbl = None
        self.mspeed_m2_name_lbl = None
        self.tspeed_m2_value_lbl = None
        self.tspeed_m2_value_var = tk.StringVar()
        self.mspeed_m2_value_lbl = None
        self.mspeed_m2_value_var = tk.StringVar()

        self.init_frame()

    def init_frame(self):
        # Set the size of this frame
        self.config(width=654, height=510, background="SteelBlue3")

        # Place frame at specified location on master frame
        self.place(x=610, y=9)

        # Build all the widgets on this frame
        self.build_widgets()

    def build_widgets(self):
        # Creating the "Target Speed Name" label instance for motor 1
        self.tspeed_m1_name_lbl = tk.Label(self, width=9, height=1, bg="SteelBlue3", fg="Snow", anchor="w",
                                           text="Target:")

        # Creating the "Measured Speed Name" label instance for motor 1
        self.mspeed_m1_name_lbl = tk.Label(self, width=9, height=1, bg="SteelBlue3", fg="Snow", anchor="w",
                                           text="Measured:")

        # Creating the "Target Speed Value" label instance for motor 1
        self.tspeed_m1_value_lbl = tk.Label(self, width=13, height=1, bg="SteelBlue3", fg="Snow", anchor="e",
                                            textvariable=self.tspeed_m1_value_var)

        # Creating the "Measured Speed Value" label instance for motor 1
        self.mspeed_m1_value_lbl = tk.Label(self, width=13, height=1, bg="SteelBlue3", fg="Snow", anchor="e",
                                            textvariable=self.mspeed_m1_value_var)

        # Creating the "Target Speed Name" label instance for motor 2
        self.tspeed_m2_name_lbl = tk.Label(self, width=9, height=1, bg="SteelBlue3", fg="Snow", anchor="w",
                                           text="Target:")

        # Creating the "Measured Speed Name" label instance for motor 2
        self.mspeed_m2_name_lbl = tk.Label(self, width=9, height=1, bg="SteelBlue3", fg="Snow", anchor="w",
                                           text="Measured:")

        # Creating the "Target Speed Value" label instance for motor 2
        self.tspeed_m2_value_lbl = tk.Label(self, width=13, height=1, bg="SteelBlue3", fg="Snow", anchor="e",
                                            textvariable=self.tspeed_m2_value_var)

        # Creating the "Measured Speed Value" label instance for motor 2
        self.mspeed_m2_value_lbl = tk.Label(self, width=13, height=1, bg="SteelBlue3", fg="Snow", anchor="e",
                                            textvariable=self.mspeed_m2_value_var)

        # Initialise var values
        self.tspeed_m1_value_var.set("+0.00 mm/s")
        self.mspeed_m1_value_var.set("+0.00 mm/s")
        self.tspeed_m2_value_var.set("+0.00 mm/s")
        self.mspeed_m2_value_var.set("+0.00 mm/s")

        # Placing the widgets on the frame
        self.tspeed_m1_name_lbl.place(x=30, y=20)
        self.tspeed_m1_value_lbl.place(x=153, y=20)
        self.mspeed_m1_name_lbl.place(x=30, y=60)
        self.mspeed_m1_value_lbl.place(x=153, y=60)
        self.tspeed_m2_name_lbl.place(x=30, y=100)
        self.tspeed_m2_value_lbl.place(x=153, y=100)
        self.mspeed_m2_name_lbl.place(x=30, y=140)
        self.mspeed_m2_value_lbl.place(x=153, y=140)

    def update_telemetry(self, args):
        self.tspeed_m1_value_var.set("{0:+.02f} mm/s".format(args[0]))
        self.mspeed_m1_value_var.set("{0:+.02f} mm/s".format(args[1]))
        self.tspeed_m2_value_var.set("{0:+.02f} mm/s".format(args[2]))
        self.mspeed_m2_value_var.set("{0:+.02f} mm/s".format(args[3]))
