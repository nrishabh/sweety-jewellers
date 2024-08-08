def drawNewSection(c, group, category, y_pos):

    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import cm

    y = (2.35 * cm) + (6.25 * cm * (y_pos - 1))

    c.setFillColor(HexColor("#F0F0F0"))
    c.rect(
        0.5 * cm,
        841.89 - ((y - 0.05) + (0.65 * cm)),
        20 * cm,
        0.65 * cm,
        stroke=0,
        fill=1,
    )

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Roboto Medium", 10)
    c.drawCentredString(
        (0.5 * cm) + ((20 * cm) / 2),
        841.89 - (y + ((0.9 * cm) / 2)),
        group + ": " + category,
    )


def drawBG(c):

    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import cm

    c.setFillColor(HexColor("#161B33"))
    c.rect(0.5 * cm, 27.35 * cm, 20 * cm, 2 * cm, stroke=0, fill=1)
    c.rect(0.5 * cm, 0.35 * cm, 20 * cm, 1.35 * cm, stroke=0, fill=1)

    # ADD 0.35cm to Y
    c.setFillColorRGB(255, 255, 255)
    c.setFont("Roboto Italic", 12)
    c.drawString(0.75 * cm, 28.8 * cm, "Collection Catalogue")
    # c.setFont("Roboto Medium", 24)
    # c.drawString(13.75*cm, 27.7*cm, "")
    c.setFont("Roboto Italic", 12)
    c.drawString(0.75 * cm, 0.9 * cm, "Order on WhatsApp, Pan-India Delivery")
    c.drawString(14.65 * cm, 0.9 * cm, "Reach us on +91 93201 69254")
    c.setStrokeColor(HexColor("#FFFFFF"))
    # c.setFillColorRGB(255, 255, 255)
    c.line(17 * cm, 0.8 * cm, 20.21 * cm, 0.8 * cm)
    c.linkURL(
        "http://wa.me/919320169254",
        (14.5 * cm, 0.7 * cm, 20.45 * cm, 1.4 * cm),
        relative=1,
    )


def incr_y(c, x_pos, y_pos):

    global isBlankPage

    # print("Increasing Y_Pos.\nCurrent Y_Pos: "+str(y_pos))

    if y_pos < 4:
        y_pos += 1
        x_pos = 1

    else:
        # print("Ending this page.")
        c.showPage()
        isBlankPage = True
        y_pos = 1
        x_pos = 1

    # print("New X_Pos: "+str(x_pos)+"\tNew Y_Pos: "+str(y_pos))
    return x_pos, y_pos


def incr_x(c, x_pos, y_pos):

    # print("Increasing X_Pos.\nCurrent X_Pos: "+str(x_pos))

    if x_pos < 3:
        x_pos += 1
    else:
        x_pos, y_pos = incr_y(c, x_pos, y_pos)

    # print("New X_Pos: "+str(x_pos)+"\tNew Y_Pos: "+str(y_pos))
    return x_pos, y_pos


def addItemDetails(c, DB, item, price_col, x_pos, y_pos):

    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import cm

    if DB.at[item, "ip_file_path"] != "":
        x = (0.5 * cm) + ((x_pos - 1) * 6.83 * cm)
        y = (3.1 * cm) + ((y_pos - 1) * 6.25 * cm)
        c.drawImage(
            DB.at[item, "ip_file_path"],
            x,
            841.89 - (y + (4 * cm)),
            width=(6.33 * cm),
            height=(4 * cm),
            preserveAspectRatio=True,
        )

    c.setFont("Roboto Medium", 8)
    c.setFillColor(HexColor("#000000"))
    # Line 1
    x = ((x_pos - 1) * 6.83 * cm) + (3.665 * cm)
    y = ((y_pos - 1) * 6.25 * cm) + (7.6 * cm)
    msg = "Item Code: " + item
    c.drawCentredString(x, 841.89 - y, msg)

    # Line 2
    x = ((x_pos - 1) * 6.83 * cm) + (3.665 * cm)
    y = ((y_pos - 1) * 6.25 * cm) + (8.1 * cm)
    msg = (
        "Rate: "
        + str(DB.at[item, "Rate_" + price_col])
        + "    Min. Order: "
        + DB.at[item, "Min Ord"]
    )
    c.drawCentredString(x, 841.89 - y, msg)


def create_pdf(raw_DB, price_col, OUT_FILE, objProgressBar, ROOT):

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from utils import printer

    pdfmetrics.registerFont(TTFont("Roboto", r"assets/Roboto-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("Roboto Italic", r"assets/Roboto-Italic.ttf"))
    pdfmetrics.registerFont(TTFont("Roboto Medium", r"assets/Roboto-Medium.ttf"))

    c = canvas.Canvas(
        filename=OUT_FILE + ".pdf", pagesize=(595.27, 841.89), bottomup=1
    )  # A4 Size of 72PPI, Use Top-Left as origin

    y_pos = 0  # 1, 2, 3, 4
    x_pos = 0  # 1, 2, 3
    isBlankPage = True
    curr_group = ""
    curr_category = ""

    DB = raw_DB[
        -raw_DB[
            [
                "MissingImage",
                "MissingMinQty",
                "MissingOrdUnit",
                "ValueMissing_Column_" + price_col,
            ]
        ].any(axis=1, bool_only=True)
    ].copy()
    DB.sort_values(by=["Group", "Category"], inplace=True)

    objProgressBar.configure(length=100)
    incr = 100 / len(DB.index)
    progress = 0

    for item in DB.index:

        if DB.at[item, "Category"] == "":
            printer(f"{item} - Skipped due to missing category.")
            continue

        printer(f"Adding {item} to PDF.")
        if isBlankPage is True:
            drawBG(c)
            isBlankPage = False

        if (DB.at[item, "Group"] != curr_group) or (
            DB.at[item, "Category"] != curr_category
        ):
            if x_pos != 1:
                x_pos, y_pos = incr_y(c, x_pos, y_pos)
            curr_group = DB.at[item, "Group"]
            curr_category = DB.at[item, "Category"]
            drawNewSection(c, curr_group, curr_category, y_pos)

        addItemDetails(c, DB, item, price_col, x_pos, y_pos)

        x_pos, y_pos = incr_x(c, x_pos, y_pos)

        # update progress bar
        progress += incr
        objProgressBar["value"] = progress
        ROOT.update_idletasks()

    c.showPage()
    printer("Generating PDF...")
    c.save()
    printer("Finished generating PDF.")
