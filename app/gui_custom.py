from functools import partial
import tkinter as tk
from app import TK_ROOT, TK_WINDOW
from app.functions import read_settings

def main():
    '''Main entry point for the application.'''

    # Assigns functions
    TK_WINDOW.btnLoadSettings.configure(command=read_settings)

    TK_ROOT.mainloop()

