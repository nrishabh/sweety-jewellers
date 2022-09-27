import os
import json
import tkinter as tk
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw

def custom_logging(msg, obj_text, logfile_name):
    timestamp = datetime.now().strftime("%d-%b-%y %H:%M:%S")
    output = timestamp+": "+msg+"\n"
    obj_text.insert(tk.INSERT, output)
    with open(r'data/logs/'+logfile_name, mode='a', encoding='utf-8-sig') as f:
        print(output,file=f)

def read_settings():
    
    SETTINGS_FILE = r"data/settings.json"
    
    with open(SETTINGS_FILE, mode='r', encoding='utf-8-sig') as f:
        settings = json.load(f)

# Import Settings
try:
    

    

except Exception as e:
    logging.error("ERROR while reading settings: \n")
    logging.error(e)


# Functions

def read_excel_file(file_details):
        
        # Read excel file
        df = pd.read_excel(file_details['xlsx_file'], engine='openpyxl', skiprows=file_details['skip_rows'])
        
        # Strip whitespace in str columns
        for col in df.columns:
            if df.dtypes[col]=='O':
                df[col].str.strip()
                df.fillna(value={col: ""})
        
        # Set primary key
        df.set_index(file_details['primary_key'], inplace=True)
        
        return df

def create_captioned_img(df, primary_key, labels, cat=None):
        
        global settings
        
        pipeline = list()
        total_height = 0
        
        raw_image = Image.open(df.at[primary_key, 'ip_file_path'])
        
        # Resizing image
        w,h = raw_image.size

        IMG_WIDTH = w
        new_height = h
        
        # new_height = int((h/w)*IMG_WIDTH)

    #     logging.debug(f"Resizing image to {IMG_WIDTH}px x {new_height}px.")
    #     raw_image = raw_image.resize((IMG_WIDTH, new_height))
        pipeline.append(raw_image)
        total_height += new_height
        
        font_size = int((w/2100)*settings['labelling_schema']['font_size'])
        FONT_SETTINGS = ImageFont.truetype(settings['labelling_schema']['font_file'], font_size)
        LINE_HEIGHT = int((w/2100)*settings['labelling_schema']['line_height']) # pixels
        LABELS_PER_LINE = settings['labelling_schema']['labels_per_line']
        
        
        # Blank line above
        im = Image.new(mode="RGB",size=(IMG_WIDTH, int(LINE_HEIGHT/2)), color=(250, 250, 250))
        pipeline.append(im)
        total_height += int(LINE_HEIGHT/2)
        
        # Preparing text to write
        txt_lines = [[]]
        for i in range(len(labels)):
            
            if len(txt_lines[-1])==LABELS_PER_LINE:
                txt_lines.append(list())
            
            if labels[i]==df.index.name:
                msg = labels[i]+": "+primary_key
            elif labels[i]=="Rate/Unit":
                rate_per_unit = f"{df.at[primary_key, cat]:.2f}/"+str(df.at[primary_key, 'Base Unit']) 
                msg = "Rate: ₹ "+rate_per_unit
            elif labels[i]=="Min Qty/Ord":
                msg = f"Min Ord: {df.at[primary_key, 'Min Qty']} {df.at[primary_key, 'Ord Unit']}" 
            else:
                msg = labels[i]+": "+str(df.at[primary_key, labels[i]])
            
            txt_lines[-1].append(msg)
        
        # Writing text to image line-by-line
        for lines in txt_lines:
            im = Image.new(mode="RGB",size=(IMG_WIDTH, LINE_HEIGHT), color=(250, 250, 250))
            draw = ImageDraw.Draw(im)
            msg = "        ".join(lines)
            draw.text((IMG_WIDTH/2, LINE_HEIGHT/2), msg, fill='black', font=FONT_SETTINGS, anchor='mm')
            pipeline.append(im)
            total_height += LINE_HEIGHT
        
        # Blank line below
        im = Image.new(mode="RGB",size=(IMG_WIDTH, int(LINE_HEIGHT/2)), color=(250, 250, 250))
        pipeline.append(im)
        total_height += int(LINE_HEIGHT/2)
        
        # Final Image
        final_img = Image.new(mode='RGB', size=(IMG_WIDTH, total_height))
        
        height_counter = 0
        for i in range(len(pipeline)):
            final_img.paste(pipeline[i], box=(0, height_counter))
            _, h = pipeline[i].size
            height_counter += h
        
        return final_img

try:
    root = tk.Tk()

    canvas_1 = tk.Canvas(root, width=300, height=300)
    canvas_1.pack()

except Exception as e:

    logging.error("ERROR: \n")
    logging.error(e)


def main_stuff():

    item_catalog = read_excel_file(settings['item_catalog'])

    purchase_orders = read_excel_file(settings['purchase_orders'])

    # Sorting items according to purchase order dates
    item_catalog['last_purchase_date'] = datetime(year=1990, month=1, day=1)
    item_catalog['last_purchase'] = ''

    for i in list(item_catalog.index):
        try:
            last_purchase_date = max(purchase_orders.at[i, 'Date'])
        except KeyError as e:
            item_catalog.at[i, 'last_purchase'] = 'Others'
            continue
        except TypeError as e:
            last_purchase_date = purchase_orders.at[i, 'Date']
        item_catalog.at[i, 'last_purchase_date'] = last_purchase_date
        if last_purchase_date>=(datetime.now()-timedelta(weeks=4)):
            item_catalog.at[i, 'last_purchase'] = 'This Month'
        elif last_purchase_date>=(datetime.now()-timedelta(weeks=8)):
            item_catalog.at[i, 'last_purchase'] = 'Last Month'
        else:
            item_catalog.at[i, 'last_purchase'] = 'Others'

    # Reading JPG file paths
    item_catalog['ip_file_path'] = ''
    filepaths = os.listdir(settings['img_input_folder'])

    for i in list(item_catalog.index):
        if ((i+".jpg") in filepaths):
            item_catalog.at[i, 'ip_file_path'] = settings['img_input_folder']+r"/"+i+".jpg"
        elif ((i+".jpeg") in filepaths):
            item_catalog.at[i, 'ip_file_path'] = settings['img_input_folder']+r"/"+i+".jpeg"
        else:
            logging.warning(f"Image not found for item {i}")
            continue

    OUTPUT_FOLDER = settings["img_output_folder"]

    for i in tqdm(list(item_catalog[item_catalog['ip_file_path']!=''].index), desc='Creating images: ', unit='item'):
        if item_catalog.at[i, 'ip_file_path']!='':
            for variation in settings['labelling_schema']['label_variations']:

                img = create_captioned_img(item_catalog, i, variation['label_cols'], cat=variation['price_col'])
                
                if item_catalog.at[i, settings['labelling_schema']["to_clear_col_name"]] in ["Y", "y"]:
                    heading = settings['labelling_schema']["to_clear_col_name"]
                else:
                    heading = item_catalog.at[i, 'last_purchase']
                
                output_path = OUTPUT_FOLDER + r'/' + variation['price_col'] + r'/' + heading + r'/' + item_catalog.at[i, 'Group'] + r'/' + item_catalog.at[i, 'Category'] + r'/'
                
                if not os.path.isdir(output_path):
                    os.makedirs(output_path)
                
                img.save(output_path+i+".jpg", format='JPEG')

    label1 = tk.Label(root, text= 'Main Stuff Done', fg='blue', font=('helvetica', 12, 'bold'))
    canvas_1.create_window(150, 200, window=label1)


try:
    button1 = tk.Button(text='Click Me', command=main_stuff, bg='brown',fg='white')
    canvas_1.create_window(150, 150, window=button1)
    
    
    root.mainloop()

except Exception as e:
    logging.error("ERROR: \n")
    logging.error(e)


