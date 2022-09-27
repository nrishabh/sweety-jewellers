import os
import json
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw
from app import ITEM_CATALOG, PURCHASE_ORDERS, TK_WINDOW, SETTINGS, custom_logging

# STANDALONE FUNCTION: Read Excel File and return a df
def read_excel_file(file_details):
    
    try:
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

    except Exception as e:
        custom_logging(Exception)


# STANDALONE FUNCTION: Create Captioned Image
def create_captioned_img(df, primary_key, labels, cat=None):
    
    global SETTINGS
    
    try:

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
        
        font_size = int((w/2100)*SETTINGS['labelling_schema']['font_size'])
        FONT_SETTINGS = ImageFont.truetype(SETTINGS['labelling_schema']['font_file'], font_size)
        LINE_HEIGHT = int((w/2100)*SETTINGS['labelling_schema']['line_height']) # pixels
        LABELS_PER_LINE = SETTINGS['labelling_schema']['labels_per_line']
        
        
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
    
    except Exception as e:
        custom_logging(e)

# DEPENDENT FUNCTION: Create images for a given set of raw images and details
def create_images():
    
    global TK_WINDOW, SETTINGS, ITEM_CATALOG
    try:

        OUTPUT_FOLDER = SETTINGS["img_output_folder"]
        

        current_count = 0
        total_count = len(list(ITEM_CATALOG[ITEM_CATALOG['ip_file_path']!=''].index))

        for i in list(ITEM_CATALOG[ITEM_CATALOG['ip_file_path']!=''].index):

            if ITEM_CATALOG.at[i, 'ip_file_path']!='':
                for variation in SETTINGS['labelling_schema']['label_variations']:

                    img = create_captioned_img(ITEM_CATALOG, i, variation['label_cols'], cat=variation['price_col'])
                    
                    if ITEM_CATALOG.at[i, SETTINGS['labelling_schema']["to_clear_col_name"]] in ["Y", "y"]:
                        heading = SETTINGS['labelling_schema']["to_clear_col_name"]
                    else:
                        heading = ITEM_CATALOG.at[i, 'last_purchase']
                    
                    output_path = OUTPUT_FOLDER + r'/' + variation['price_col'] + r'/' + heading + r'/' + ITEM_CATALOG.at[i, 'Group'] + r'/' + ITEM_CATALOG.at[i, 'Category'] + r'/'
                    
                    if not os.path.isdir(output_path):
                        os.makedirs(output_path)
                    
                    img.save(output_path+i+".jpg", format='JPEG')

                    current_count += 1
                    TK_WINDOW.TProgressbar1.configure(value=(current_count/total_count))
    except Exception as e:
        custom_logging(e)

# DEPENDENT FUNCTION: Create database
def create_db():

    global SETTINGS, ITEM_CATALOG, PURCHASE_ORDERS
    try:
        custom_logging("Reading excel file for 'Item Catalog'.")
        ITEM_CATALOG = read_excel_file(SETTINGS["item_catalog"])
        custom_logging("Reading excel file for 'Purchase Orders'.")
        PURCHASE_ORDERS = read_excel_file(SETTINGS["purchase_orders"])

        # Sorting items according to purchase order dates
        custom_logging("Sorting items according to purchase order dates.")
        ITEM_CATALOG['last_purchase_date'] = datetime(year=1990, month=1, day=1)
        ITEM_CATALOG['last_purchase'] = ''

        for i in list(ITEM_CATALOG.index):
            try:
                last_purchase_date = max(PURCHASE_ORDERS.at[i, 'Date'])
            except KeyError as e:
                ITEM_CATALOG.at[i, 'last_purchase'] = 'Others'
                continue
            except TypeError as e:
                last_purchase_date = PURCHASE_ORDERS.at[i, 'Date']
            ITEM_CATALOG.at[i, 'last_purchase_date'] = last_purchase_date
            if last_purchase_date>=(datetime.now()-timedelta(weeks=4)):
                ITEM_CATALOG.at[i, 'last_purchase'] = 'This Month'
            elif last_purchase_date>=(datetime.now()-timedelta(weeks=8)):
                ITEM_CATALOG.at[i, 'last_purchase'] = 'Last Month'
            else:
                ITEM_CATALOG.at[i, 'last_purchase'] = 'Others'

        custom_logging("Reading image files.")
        ITEM_CATALOG['ip_file_path'] = ''
        filepaths = os.listdir(SETTINGS['img_input_folder'])

        for i in list(ITEM_CATALOG.index):
            if ((i+".jpg") in filepaths):
                ITEM_CATALOG.at[i, 'ip_file_path'] = SETTINGS['img_input_folder']+r"/"+i+".jpg"
            elif ((i+".jpeg") in filepaths):
                ITEM_CATALOG.at[i, 'ip_file_path'] = SETTINGS['img_input_folder']+r"/"+i+".jpeg"
            else:
                custom_logging(f"Image not found for item {i}")
                continue
        
        custom_logging("All details and files imported.")
        custom_logging("Ready to create images.")
        TK_WINDOW.btnCreateImages.configure(command=create_images, state='active')
    
    except Exception as e:
        custom_logging(e)
        
def read_settings():

    global SETTINGS

    if not os.path.isfile(SETTINGS):
        custom_logging("Settings file not found in data directory.")
    else:
        try:
            with open(SETTINGS, mode='r', encoding='utf-8-sig') as f:
                SETTINGS = json.load(f)
                custom_logging("Loaded settings file.")
                TK_WINDOW.btnLoadExcelFiles.configure(command=create_db, state='active')
        except Exception as e:
            custom_logging(e)