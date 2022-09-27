import tkinter as tk
from datetime import datetime
from app.gui_page import Toplevel1

SETTINGS = r"data/settings.json"
LOG_FILE = "Session_"+(datetime.now().strftime("%d%b%y_%H%M%S"))+".log"
TK_ROOT = tk.Tk()
TK_ROOT.protocol( 'WM_DELETE_WINDOW' , TK_ROOT.destroy)
TK_WINDOW = Toplevel1(TK_ROOT)
ITEM_CATALOG = ""
PURCHASE_ORDERS = ""

def custom_logging(msg):

    global TK_WINDOW

    timestamp = datetime.now().strftime("%d-%b-%y %H:%M:%S")
    output = timestamp+": "+msg+"\n"

    TK_WINDOW.txtScrolled.insert(tk.INSERT, output)
    with open(r'data/logs/'+LOG_FILE, mode='a', encoding='utf-8-sig') as f:
        print(output,file=f)

from app import functions, gui_custom