from PIL import Image, ImageFont, ImageDraw

FONT_SIZE = 45
GENERAL_FONT_FILE = r"assets/RobotoSlab-Medium.ttf"
MARKETING_FONT_FILE = r"assets/Roboto-Italic.ttf"
LINE_HEIGHT = 100
LABELS_PER_LINE = 2


def create_image(DB, primary_key, labels, rate_col=None):
    
    from utils import printer
    global FONT_SIZE, LINE_HEIGHT, LABELS_PER_LINE, MARKETING_FONT_FILE, GENERAL_FONT_FILE

    pipeline = list()
    total_height = 0
    
    raw_image = Image.open(DB.at[primary_key, 'ip_file_path'])
    
    # Resizing image
    w,h = raw_image.size
    
    pipeline.append(raw_image)
    total_height += h

    font_size = int((w/2100)*FONT_SIZE)
    line_height = int((w/2100)*LINE_HEIGHT) # pixels
    
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
