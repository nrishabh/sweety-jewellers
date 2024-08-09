import sys
import json
import tkinter as tk
from datetime import datetime

LOGFILE = ""

def set_logfile(filename):
    
    global LOGFILE
    
    LOGFILE = r"logs/"+filename

def printer(msg):
    global LOGFILE
    
    now = datetime.now().strftime("%d-%b-%y %H:%M:%S - ")
    with open(LOGFILE, mode='a+') as logfile:
        logfile.write(now+msg+"\n")
    print(now+msg)

def eprinter(msg):
    now = datetime.now().strftime("%d-%b-%y %H:%M:%S - ")
    with open(LOGFILE, mode='a') as logfile:
        logfile.write(now+msg+"\n")
    print(now+msg, file=sys.stderr)

# Print to GUI console
class PrintLogger(object):  # create file like object

    def __init__(self, textbox):  # pass reference to text widget
        self.textbox = textbox  # keep ref

    def write(self, text):
        
        self.textbox.configure(state="normal")  # make field editable
        self.textbox.insert("insert", text)  # write text to textbox
        self.textbox.see("end")  # scroll to end
        self.textbox.configure(state="disabled")  # make field readonly

    def flush(self):  # needed for file like object
        pass

# Log errors to GUI console
class ErrorLogger(object):  # create file like object

    def __init__(self, textbox):  # pass reference to text widget
        self.textbox = textbox  # keep ref

    def write(self, text):
        self.textbox.tag_config('warning', background="yellow", foreground="red")
        self.textbox.configure(state="normal")  # make field editable
        self.textbox.insert("end", text, 'warning')  # write text to textbox
        self.textbox.see("end")  # scroll to end
        self.textbox.configure(state="disabled")  # make field readonly

    def flush(self):  # needed for file like object
        pass

# Function to select file
def select_file(entry_widget):

    from tkinter.filedialog import askopenfilename

    filename = askopenfilename(initialdir = "/",
                                          title = "Select a File",
                                          filetypes = (("Excel files", "*.xlsx*"),
                                                       ("All files", "*.*")))
    
    if filename!='':
        
        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(tk.INSERT, filename)
        entry_widget.configure(state='readonly')
        entry_widget.xview_moveto(1)

# Function to select folder
def select_folder(entry_widget):

    from tkinter.filedialog import askdirectory

    dir_path = askdirectory()
    
    if dir_path!='':

        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(tk.INSERT, dir_path)
        entry_widget.configure(state='readonly')
        entry_widget.xview_moveto(1)
        

def save_settings(window):

    from tkinter.filedialog import asksaveasfile
    
    filetypes = (('Sweety Jewellers Files', '*.sj'),
                ('All Files', '*.*'))
    file = asksaveasfile(filetypes = filetypes, defaultextension = filetypes)
    if file:
        settings = dict()
        settings['main_xlsx_path'] = window.entryMainXLSXPath.get()
        settings['purchase_xlsx_path'] = window.entryPurchaseXLSXPath.get()
        settings['in_path'] = window.entryImagesFolder.get()
        settings['price_cols'] = window.entryPriceCols.get()
        settings['labels_per_line'] = window.entryLabelsPerLine.get()
        settings['out_path'] = window.entryOutputFolder.get()
        
        json.dump(settings, file)    
        printer("Settings saved successfully.")

def load_settings(window):

    from tkinter.filedialog import askopenfilename

    filename = askopenfilename(initialdir = "/",
                                          title = "Select a File",
                                          filetypes = (('Sweety Jewellers Files', '*.sj'),
                                                       ("All files", "*.*")))
    
    if filename!='':
        with open(filename, mode='r') as file:
            settings = json.load(file)
    
    window.entryMainXLSXPath.configure(state='normal')
    window.entryMainXLSXPath.delete(0, tk.END)
    window.entryMainXLSXPath.insert(tk.INSERT, settings['main_xlsx_path'])
    window.entryMainXLSXPath.configure(state='readonly')
    window.entryMainXLSXPath.xview_moveto(1)

    window.entryPurchaseXLSXPath.configure(state='normal')
    window.entryPurchaseXLSXPath.delete(0, tk.END)
    window.entryPurchaseXLSXPath.insert(tk.INSERT, settings['purchase_xlsx_path'])
    window.entryPurchaseXLSXPath.configure(state='readonly')
    window.entryPurchaseXLSXPath.xview_moveto(1)

    window.entryPriceCols.configure(state='normal')
    window.entryPriceCols.delete(0, tk.END)
    window.entryPriceCols.insert(tk.INSERT, settings['price_cols'])
    window.entryPriceCols.xview_moveto(1)

    window.entryLabelsPerLine.configure(state='normal')
    window.entryLabelsPerLine.delete(0, tk.END)
    window.entryLabelsPerLine.insert(tk.INSERT, settings['labels_per_line'])
    window.entryLabelsPerLine.xview_moveto(1)

    window.entryOutputFolder.configure(state='normal')
    window.entryOutputFolder.delete(0, tk.END)
    window.entryOutputFolder.insert(tk.INSERT, settings['out_path'])
    window.entryOutputFolder.configure(state='readonly')
    window.entryOutputFolder.xview_moveto(1)

    window.entryImagesFolder.configure(state='normal')
    window.entryImagesFolder.delete(0, tk.END)
    window.entryImagesFolder.insert(tk.INSERT, settings['in_path'])
    window.entryImagesFolder.configure(state='readonly')
    window.entryImagesFolder.xview_moveto(1)

    printer("Settings loaded successfully.")