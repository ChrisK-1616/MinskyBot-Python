"""
Author: Chris Knowles
File: launcher.py
Version: 1.0.0
Notes: Always executes the run() method from the MainApp class as implemented in
       the mainapp module, if there is no mainapp module then nothing can be
       executed and the code module aborts
"""
try:
    # Imports
    from mainapp import MainApp

    def main():
        app = MainApp()
        app.run()

    # Execute as a script rather than a module
    if __name__ == "__main__":
        main()

except ImportError as e:
    print("Module import error, therefore nothing is executed: ", e)
    