# Author: Chris Knowles
# File: launcher.py
# Version: 1.0.0
# Notes: Launcher for MinskyBot controller application

# imports
import tkinter as tk
from main_window import MainWindow


# Program entrance function
def main():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


# Invoke main() program entrance
if __name__ == "__main__":
    # execute only if run as a script
    main()
