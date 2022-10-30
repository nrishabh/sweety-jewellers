import os
import sys
import json
import pandas as pd
import tkinter as tk

from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw
from tkinter.filedialog import askopenfilename, askdirectory, asksaveasfile

# Hard-code Vars
NEW_STOCK_DATE = datetime.utcnow()+timedelta(hours=5, minutes=30)-timedelta(days=28)

USEFUL_COLS = ["Product Code", "Name", "Group", "Category", "Base Unit", "To Clear", "Min Qty", "Ord Unit"]
PRICE_COLS = list()

FONT_SIZE = 45
GENERAL_FONT_FILE = r"assets/general_font.ttf"
MARKETING_FONT_FILE = r"assets/marketing_font.ttf"
LINE_HEIGHT = 100
LABELS_PER_LINE = 2

DB = pd.DataFrame()

def printer(msg):
    now = datetime.now().strftime("%d-%b-%y %H:%M:%S - ")
    print(now+msg)

def eprinter(msg):
    now = datetime.now().strftime("%d-%b-%y %H:%M:%S - ")
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
def select_file(entry_widget, loader=None):
    filename = askopenfilename(initialdir = "/",
                                          title = "Select a File",
                                          filetypes = (("Excel files", "*.xlsx*"),
                                                       ("All files", "*.*")))
    
    if filename!='':
        if loader is not None:
            globals()[loader](filename)
        
        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(tk.INSERT, filename)
        entry_widget.configure(state='readonly')
        entry_widget.xview_moveto(1)

# Function to select folder
def select_folder(entry_widget, loader=None):
    dir_path = askdirectory()
    
    if dir_path!='':
        if loader is not None:
            globals()[loader](dir_path)

        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(tk.INSERT, dir_path)
        entry_widget.configure(state='readonly')
        entry_widget.xview_moveto(1)

# Main XLSX File Validator
def load_main_xlsx(path):

    global DB

    # Read Main Excel File
    DB = pd.read_excel(path, engine='openpyxl', skiprows=5)

    # Strip whitespace in str columns
    for col in DB.columns:
        if DB.dtypes[col]=='O':
            DB[col].str.strip()
            DB.fillna(value={col: ""})

    DB.drop(index=0, inplace=True)

    DB.set_index("Product Code", inplace=True)

    DB["Min Qty"] = pd.to_numeric(DB["Min Qty"], downcast="integer")

    printer("Loaded Main XLSX file successfully.")
    pass

# Purchase Order XLSX File Validator
def load_purchase_xlsx(path):

    global DB

    # Reading Purchase Order Excel File
    purchase_data = pd.read_excel(path)

    for col in purchase_data.columns:
        if purchase_data.dtypes[col]=='O':
            purchase_data[col].str.strip()
            purchase_data.fillna(value={col: ""})

    purchase_data.set_index("Item Name", inplace=True)

    printer("Loaded Purchase Order file successfully.")

    DB['time_tag'] = "Regular"

    for i in list(DB.index):
        if DB.at[i, "To Clear"] in ["Y", "y"]:
            DB.at[i, 'time_tag'] = "To Clear"
            continue
        else:
            try:
                last_purchase_date = max(purchase_data.at[i, 'Date'])
            except KeyError as e:
                DB.at[i, 'time_tag'] = 'Regular'
                continue
            except TypeError as e:
                last_purchase_date = purchase_data.at[i, 'Date']

            if last_purchase_date>=NEW_STOCK_DATE:
                DB.at[i, 'time_tag'] = 'New This Month'
            else:
                DB.at[i, 'time_tag'] = 'Regular'

    printer("Finished assigning time tags.")

def read_inp_imgs(path):
    
    DB['ip_file_path'] = ''
    filepaths = os.listdir(path)
    for item in DB.index:
        if ((item+".jpg") in filepaths):
            DB.at[item, 'ip_file_path'] = path+r"/"+item+".jpg"
        elif ((item+".jpeg") in filepaths):
            DB.at[item, 'ip_file_path'] = path+r"/"+item+".jpeg"
        else:
            eprinter(f"No image found for {item}. This item will be skipped.")

    printer("Finished reading images folder.")
    
    pass

def db_prep():

    global DB, PRICE_COLS

    for col_index in range(len(PRICE_COLS)):
        col = PRICE_COLS[col_index]
        new_col = "Rate_"+col

        DB[new_col] = ""
        for i in list(DB.index):
            if pd.isna(DB.at[i, col]) is True:
                eprinter(f"{i} is missing value in column {col}. This item will be skipped.")
            else:
                DB.at[i, new_col] = f"Rs. {DB.at[i, col]:.2f} per "+str(DB.at[i, "Base Unit"])

        # PRICE_COLS[col_index] = new_col

    DB["Min Ord"] = ""
    for item in DB.index:
        if pd.isna(DB.at[item, "Min Qty"]) is True:
            eprinter(f"{item} is missing value for Min Qty. This item will be skipped.")
        elif pd.isna(DB.at[item, "Ord Unit"]) is True:
            eprinter(f"{item} is missing value for Ord Unit. This item will be skipped.")
        else:
            DB.at[item, "Min Ord"] = str(DB.at[item, "Min Qty"]) + " " + DB.at[item, "Ord Unit"]

def create_image(DB, primary_key, labels, rate_col=None):
    
    global FONT_SIZE, FONT_FILE, LINE_HEIGHT, LABELS_PER_LINE

    pipeline = list()
    total_height = 0
    
    raw_image = Image.open(DB.at[primary_key, 'ip_file_path'])
    
    # Resizing image
    w,h = raw_image.size
    
    pipeline.append(raw_image)
    total_height += h

    font_size = int((w/2100)*FONT_SIZE)
    line_height = int((w/2100)*LINE_HEIGHT) # pixels
    printer("Line Height: "+str(line_height))
    
    # Marketing line first
    marketing_font = ImageFont.truetype(MARKETING_FONT_FILE, font_size)
    im = Image.new(mode="RGB",size=(w, line_height), color=(236, 159, 5))
    draw = ImageDraw.Draw(im)
    msg = "From the collection of Sweety Jewellers"
    draw.fontmode = "L"
    draw.text((w/2, line_height/2), msg, fill=(41, 51, 92), font=marketing_font, anchor='mm')
    pipeline.append(im)
    total_height += int(line_height)
    
    # Blank line above
    im = Image.new(mode="RGB",size=(w, int(line_height/2)), color=(250, 250, 250))
    pipeline.append(im)
    total_height += int(line_height/2)
    
    # Preparing text to write
    txt_lines = [[]]
    for i in range(len(labels)):
        
        if len(txt_lines[-1])==LABELS_PER_LINE:
            txt_lines.append(list())
        
        if labels[i]==DB.index.name:
            msg = labels[i]+": "+primary_key
        elif labels[i]=="Rate":
            msg = "Rate: "+str(DB.at[primary_key, "Rate_"+rate_col])
        else:
            msg = labels[i]+": "+str(DB.at[primary_key, labels[i]])
        
        txt_lines[-1].append(msg)
    
    # Writing text to image line-by-line
    general_font = ImageFont.truetype(GENERAL_FONT_FILE, font_size)
    for lines in txt_lines:
        im = Image.new(mode="RGB",size=(w, line_height), color=(250, 250, 250))
        draw = ImageDraw.Draw(im)
        msg = "        ".join(lines)
        draw.text((w/2, line_height/2), msg, fill='black', font=general_font, anchor='mm')
        pipeline.append(im)
        total_height += line_height
    
    # Blank line below
    im = Image.new(mode="RGB",size=(w, int(line_height/2)), color=(250, 250, 250))
    pipeline.append(im)
    total_height += int(line_height/2)
    
    # Final Image
    final_img = Image.new(mode='RGB', size=(w, total_height))
    
    height_counter = 0
    for i in range(len(pipeline)):
        final_img.paste(pipeline[i], box=(0, height_counter))
        _, h = pipeline[i].size
        height_counter += h
    
    return final_img

def generate_jpgs(entryPriceCols, entryLabelsPerLine, entryOutFolder):

    global PRICE_COLS, LABELS_PER_LINE

    PRICE_COLS = entryPriceCols.get().split(",")
    if PRICE_COLS!=['']:
        for i in range(len(PRICE_COLS)):
            PRICE_COLS[i] = PRICE_COLS[i].strip()
    else:
        PRICE_COLS = list()

    printer("Set price columns.")

    LABELS_PER_LINE = int(entryLabelsPerLine.get())
    printer("Set number of labels per line.")

    OUT_FOLDER = entryOutFolder.get()
    printer("Set output folder.")

    db_prep()

    for item in DB.index:
    
        if DB.at[item, "ip_file_path"]=='':
            eprinter(f"{item} - Skipped.")
            continue
        
        path_by_time_tag = r"/BY_TIME_TAG/"+DB.at[item, 'time_tag']+r"/"+DB.at[item, 'Group']+r"/"+DB.at[item, 'Category']
        path_by_group = r"/BY_GROUP/"+DB.at[item, 'Group']+r"/"+DB.at[item, 'Category']+r"/"+DB.at[item, 'time_tag']

        printer(f"{item} - Creating image for wholesale.")
        
        if not os.path.isdir(OUT_FOLDER+r"/"+"Wholesale"+r"/"+path_by_time_tag):
            os.makedirs(OUT_FOLDER+r"/"+"Wholesale"+r"/"+path_by_time_tag)

        if not os.path.isdir(OUT_FOLDER+r"/"+"Wholesale"+r"/"+path_by_group):
            os.makedirs(OUT_FOLDER+r"/"+"Wholesale"+r"/"+path_by_group)    
        
        img = create_image(DB, item, labels=["Product Code", "Group", "Category"])
        img.save(OUT_FOLDER+r"/"+"Wholesale"+r"/"+path_by_time_tag+r"/"+item+".jpg")
        img.save(OUT_FOLDER+r"/"+"Wholesale"+r"/"+path_by_group+r"/"+item+".jpg")
        del(img)
        printer(f"{item} - Created image for wholesale.")
        
        if DB.at[item, "Min Ord"]=='':
            eprinter(f"{item} - Skipped due to missing 'Min Ord' value.")
            continue
        for price_col in PRICE_COLS:
            
            if DB.at[item, price_col]=='':
                eprinter(f"{item} - Skipped for col {price_col} due to missing value.")
            else:
                printer(f"{item} - Creating retail image for col {price_col}.")
                img = create_image(DB, item, labels=["Product Code", "Group", "Category", "Rate", "Min Ord"], rate_col=price_col)
                
                if not os.path.isdir(OUT_FOLDER+r"/"+price_col+r"/"+path_by_time_tag):
                    os.makedirs(OUT_FOLDER+r"/"+price_col+r"/"+path_by_time_tag)

                if not os.path.isdir(OUT_FOLDER+r"/"+price_col+r"/"+path_by_group):
                    os.makedirs(OUT_FOLDER+r"/"+price_col+r"/"+path_by_group)

                img.save(OUT_FOLDER+r"/"+price_col+r"/"+path_by_group+r"/"+item+".jpg")
                img.save(OUT_FOLDER+r"/"+price_col+r"/"+path_by_time_tag+r"/"+item+".jpg")
                del(img)
                printer(f"{item} - Created retail image for col {price_col}.")
    
    printer("Finished generating JPGs.")

def save_settings(window):
    
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
    load_main_xlsx(settings['main_xlsx_path'])

    window.entryPurchaseXLSXPath.configure(state='normal')
    window.entryPurchaseXLSXPath.delete(0, tk.END)
    window.entryPurchaseXLSXPath.insert(tk.INSERT, settings['purchase_xlsx_path'])
    window.entryPurchaseXLSXPath.configure(state='readonly')
    window.entryPurchaseXLSXPath.xview_moveto(1)
    load_purchase_xlsx(settings['purchase_xlsx_path'])

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
    read_inp_imgs(settings['in_path'])

    printer("Settings loaded successfully.")