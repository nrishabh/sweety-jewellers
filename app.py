import os
import json
import time
import logging
import pandas as pd

from tqdm import tqdm
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw

if not os.path.exists(r"backend/logs/"):
    logging.warning("No directory for logs found. Creating logs directory.")
    os.makedirs(r"backend/logs/")

# Set up logging to file
LOGGING_DIR = r'backend/logs/'
session_startTime = datetime.now()
local_tzname = (((session_startTime).astimezone()).tzinfo).tzname((session_startTime).astimezone())
logfile = session_startTime.strftime("Session_%d%b%y_%H%M%S.log")
# NOTE: File logging has not been restricted
logging.basicConfig(format='%(name)s %(asctime)s: %(message)s', level=logging.INFO, datefmt='%d-%b-%y %H:%M:%S', filename=LOGGING_DIR+logfile)

# Set up logging for display stdout
console = logging.StreamHandler()
# NOTE: File logging has been not restricted
console.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

try:
    SETTINGS_FILE = "settings.json"

    with open(SETTINGS_FILE, mode='r', encoding='utf-8-sig') as f:
        settings = json.load(f)

    # Read XLSX File
    df = pd.read_excel(settings['xlsx_file'], engine='openpyxl')
    for col in df.columns:
        if df.dtypes[col]=='O':
            df[col].str.strip()
    df.set_index("Item Code", inplace=True)

    # Check columns of XLSX file
    assert set([df.index.name]+list(df.columns))==set(settings['price_headings']+settings['non_price_headings']), f"Columns configured in settings file do not match with columns in xlsx file.\n"

    df['ip_file_path'] = ''
    df['time_period'] = ''
    df['op_file_path'] = ''

    accepted_files = ['.jpg', ".jpeg"]

    for time_period in settings['time_period_folders']:
        for filename in os.listdir(settings["raw_img_folder"]+r"/"+time_period+r"/"):
            
            # Check file extension
            assert filename[-4:] in accepted_files, f"Non-supported file found: {settings['raw_img_folder']}/{time_period}/{filename}"
            
            item_code = filename[:-4]
            
            # If item_code not found in XLSX file
            if item_code not in list(df.index):
                logging.info(f"Item '{item_code}' not found in XLSX file. Skipping item.")
                continue
            
            # Check if file was already found
            assert df.loc[item_code]['ip_file_path']=='', f"Image for {item_code} exists in two locations.\nLocation 1: {settings['raw_img_folder']}/{time_period}/{filename}\nLocation 2: {df.loc[item_code]['ip_file_path']}"
            
            df.at[item_code, 'ip_file_path'] = settings['raw_img_folder']+r'/'+time_period+r'/'+filename
            df.at[item_code, 'time_period'] = time_period
            
            op_file_path = df.at[item_code, 'Group']+r'/'+df.at[item_code, 'Category']+r'/'
            if df.at[item_code, 'To Clear'] in ['Y', 'y']:
                op_file_path = r'/To Clear/' + op_file_path
            else:
                op_file_path = time_period + r'/' + op_file_path
            
            df.at[item_code, 'op_file_path'] = op_file_path

    # Check if any entries did not find image
    for item_code in list(df[df['ip_file_path']==''].index):
        logging.error("Did not find image for item code: "+item_code)

    def create_captioned_img(df, item_code, labels, cat=None):
        
        global settings

        FONT_SETTINGS = ImageFont.truetype(r"backend/Roboto/Roboto-Regular.ttf", 27)
        IMG_WIDTH = 1000 # pixels
        LINE_HEIGHT = 45 # pixels
        LABELS_PER_LINE = settings['labels_per_line']
        
        pipeline = list()
        total_height = 0
        
        raw_image = Image.open(df.at[item_code, 'ip_file_path'])
        
        # Resizing image
        w,h = raw_image.size

        new_height = int((h/w)*IMG_WIDTH)

        # logging.debug(f"Resizing image to {IMG_WIDTH}px x {new_height}px.")
        raw_image = raw_image.resize((IMG_WIDTH, new_height))
        pipeline.append(raw_image)
        total_height += new_height
        
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
                msg = labels[i]+": "+item_code
            elif labels[i]=="Rate/Unit":
                rate_per_unit = f"{df.at[item_code, cat]:.2f}/"+str(df.at[item_code, 'Unit']) 
                msg = "Rate: ₹ "+rate_per_unit
            else:
                msg = labels[i]+": "+str(df.at[item_code, labels[i]])
            
            txt_lines[-1].append(msg)
        
        # Writing text to image line-by-line
        for lines in txt_lines:
            im = Image.new(mode="RGB",size=(IMG_WIDTH, LINE_HEIGHT), color=(250, 250, 250))
            draw = ImageDraw.Draw(im)
            msg = "        ".join(lines)
            draw.text((IMG_WIDTH/2, LINE_HEIGHT/2), msg, fill='black', font=FONT_SETTINGS, anchor='mm')
            pipeline.append(im)
            total_height += LINE_HEIGHT
        
        # Blank line above
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

    OUTPUT_FOLDER = settings["out_img_folder"]

    output = list()

    for item_code in tqdm(list(df.index), desc='Creating images: ', unit='item'):
        
        logging.info(f"Creating images for item '{item_code}'")
        
        common_img = create_captioned_img(df, item_code, settings['common_labels'])
        
        for heading in settings['price_headings']:
            if heading not in settings['exclusive_price_cols']:
                
                output_path = OUTPUT_FOLDER + r'/' + heading + r'/' + df.at[item_code, 'op_file_path']
                
                if not os.path.isdir(output_path):
                    os.makedirs(output_path)
                
                common_img.save(output_path+item_code+".jpg", format='JPEG')
                
        for heading in settings['exclusive_price_cols']:
            
            img = create_captioned_img(df, item_code, settings['common_labels']+settings['exclusive_labels'], cat=heading)
            
            output_path = OUTPUT_FOLDER + r'/' + heading + r'/' + df.at[item_code, 'op_file_path']
                
            if not os.path.isdir(output_path):
                os.makedirs(output_path)

            img.save(output_path+item_code+".jpg", format='JPEG')
        
        logging.info("Images created.")

except Exception as e:
    logging.error("ERROR ENCOUNTERED\n")
    logging.error(e)
