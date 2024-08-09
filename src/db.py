import pandas as pd
from datetime import datetime, timedelta
from pdf import create_pdf

# Hard-code Vars
NEW_STOCK_DATE = datetime.utcnow() + timedelta(hours=5, minutes=30) - timedelta(days=28)

USEFUL_COLS = [
    "Product Code",
    "Name",
    "Group",
    "Category",
    "Base Unit",
    "To Clear",
    "Min Qty",
    "Ord Unit",
]
PRICE_COLS = list()

DB = pd.DataFrame()

ROOT = ""


def set_root(root):

    global ROOT

    ROOT = root


def preprocess(main_xlsx_path, purchase_order_xlsx_path, inp_img_dir):

    import os
    from utils import printer, eprinter

    global DB, PRICE_COLS

    # Read Main Excel File
    DB = pd.read_excel(main_xlsx_path, engine="openpyxl", skiprows=5)

    DB["Category"] = DB["Category"].astype(object)
    DB["Category"].fillna(value="", inplace=True)

    printer("Columns in Main XLSX file: " + str(DB.columns))
    # Strip whitespace in str columns
    for col in DB.columns:
        if DB.dtypes[col] == "O":
            DB[col].str.strip()
            DB.fillna(value={col: ""})

    DB.drop(index=0, inplace=True)

    DB.set_index("Product Code", inplace=True)

    DB["Min Qty"] = pd.to_numeric(DB["Min Qty"], downcast="integer")

    printer("Loaded Main XLSX file successfully.")

    # Reading Purchase Order Excel File
    purchase_data = pd.read_excel(
        purchase_order_xlsx_path, engine="openpyxl", skiprows=5
    )

    # Strip whitespace in str columns
    for col in purchase_data.columns:
        if purchase_data.dtypes[col] == "O":
            purchase_data[col].str.strip()
            purchase_data.fillna(value={col: ""})

    purchase_data.drop(index=0, inplace=True)
    print(purchase_data.columns)
    purchase_data.set_index("Code", inplace=True)

    purchase_data = pd.read_excel(purchase_order_xlsx_path)

    printer("Loaded Purchase Order file successfully.")

    DB["time_tag"] = "Regular"

    for i in list(DB.index):
        if DB.at[i, "To Clear"] in ["Y", "y"]:
            DB.at[i, "time_tag"] = "To Clear"
            continue
        else:
            try:
                last_purchase_date = max(purchase_data.at[i, "Date"])
            except KeyError as e:
                last_purchase_date = ""
                DB.at[i, "time_tag"] = "Regular"
                continue
            except TypeError as e:
                last_purchase_date = purchase_data.at[i, "Date"]

            if last_purchase_date >= NEW_STOCK_DATE:
                DB.at[i, "time_tag"] = "New This Month"
            else:
                DB.at[i, "time_tag"] = "Regular"

    printer("Finished assigning time tags.")

    DB["ip_file_path"] = ""
    DB["MissingImage"] = True
    filepaths = os.listdir(inp_img_dir)
    for item in DB.index:
        if (item + ".jpg") in filepaths:
            DB.at[item, "MissingImage"] = False
            DB.at[item, "ip_file_path"] = inp_img_dir + r"/" + item + ".jpg"
        elif (item + ".jpeg") in filepaths:
            DB.at[item, "MissingImage"] = False
            DB.at[item, "ip_file_path"] = inp_img_dir + r"/" + item + ".jpeg"
        else:
            eprinter(f"No image found for {item}. This item will be skipped.")

    printer("Finished reading images folder.")

    # TODO: del(filepaths, item)

    for col_index in range(len(PRICE_COLS)):
        col = PRICE_COLS[col_index]
        DB["ValueMissing_Column_" + col] = False
        new_col = "Rate_" + col

        DB[new_col] = ""
        for i in list(DB.index):
            if pd.isna(DB.at[i, col]) is True:
                DB.at[item, "ValueMissing_Column_" + col] = True
                eprinter(
                    f"{i} is missing value in column {col}. This item will be skipped for column {col}."
                )
            else:
                DB.at[i, new_col] = f"Rs. {DB.at[i, col]:.2f} per " + str(
                    DB.at[i, "Base Unit"]
                )

        # PRICE_COLS[col_index] = new_col
    # TODO: del(new_col, i)

    DB["Min Ord"] = ""
    DB["MissingMinQty"] = False
    DB["MissingOrdUnit"] = False
    DB["MissingCategory"] = False
    for item in DB.index:
        if pd.isna(DB.at[item, "Min Qty"]) is True:
            DB.at[item, "MissingMinQty"] = True
            eprinter(f"{item} is missing value for Min Qty. This item will be skipped.")
        elif pd.isna(DB.at[item, "Ord Unit"]) is True:
            DB.at[item, "MissingOrdUnit"] = True
            eprinter(
                f"{item} is missing value for Ord Unit. This item will be skipped."
            )
        elif (pd.isna(DB.at[item, "Category"]) is True) or (
            DB.at[item, "Category"] == ""
        ):
            DB.at[item, "MissingCategory"] = True
            eprinter(
                f"{item} is missing value for Category. This item will be skipped."
            )
        else:
            DB.at[item, "Min Ord"] = (
                str(DB.at[item, "Min Qty"]) + " " + DB.at[item, "Ord Unit"]
            )


def generate_missing_report(OUT_FOLDER=None, OUT_FILE=None):

    global DB

    report = DB[DB.any(axis=1, bool_only=True)]

    if len(report) > 0:
        if OUT_FILE is not None:
            report.to_csv(
                OUT_FILE,
                index=True,
                columns=[col for col in DB.columns if "Missing" in col],
            )
        if OUT_FOLDER is not None:
            report.to_csv(
                OUT_FOLDER + r"/" + "SkippedItems_IMG_.csv",
                index=True,
                columns=[col for col in DB.columns if "Missing" in col],
            )


def generate_jpgs(
    entryMainXLSXPath,
    entryPurchaseXLSXPath,
    entryImagesFolder,
    entryOutputFolder,
    entryLabelsPerLine,
    entryPriceCols,
    objProgressBar,
):

    import os
    from jpg import create_image
    from datetime import datetime
    from utils import printer, eprinter

    global DB, PRICE_COLS, LABELS_PER_LINE

    OUT_FOLDER = entryOutputFolder.get()
    date_time = datetime.now().strftime("%d_%b_%y_%H_%M_%S")
    OUT_FOLDER = OUT_FOLDER + r"/Img_" + date_time
    printer("Set output folder.")

    PRICE_COLS = entryPriceCols.get().split(",")
    if PRICE_COLS != [""]:
        for i in range(len(PRICE_COLS)):
            PRICE_COLS[i] = PRICE_COLS[i].strip()
    else:
        PRICE_COLS = list()

    printer("Set price columns.")

    LABELS_PER_LINE = int(entryLabelsPerLine.get())
    printer("Set number of labels per line.")

    preprocess(
        entryMainXLSXPath.get(), entryPurchaseXLSXPath.get(), entryImagesFolder.get()
    )

    objProgressBar.configure(length=100)
    incr = 100 / len(DB.index)
    progress = 0
    for item in DB.index:

        if DB.at[item, "Category"] == "":
            printer(f"{item} - Skipped for wholesale due to missing category.")
            continue

        if DB.at[item, "MissingImage"] is True:

            # update progress bar
            progress += incr
            objProgressBar["value"] = progress
            ROOT.update_idletasks()

            continue

        path_by_time_tag = (
            r"BY_TIME_TAG/"
            + DB.at[item, "time_tag"]
            + r"/"
            + DB.at[item, "Group"]
            + r"/"
            + DB.at[item, "Category"]
        )
        path_by_group = (
            r"BY_GROUP/"
            + DB.at[item, "Group"]
            + r"/"
            + DB.at[item, "Category"]
            + r"/"
            + DB.at[item, "time_tag"]
        )

        printer(f"{item} - Creating image for wholesale.")

        if not os.path.isdir(OUT_FOLDER + r"/" + "Wholesale" + r"/" + path_by_time_tag):
            os.makedirs(OUT_FOLDER + r"/" + "Wholesale" + r"/" + path_by_time_tag)

        if not os.path.isdir(OUT_FOLDER + r"/" + "Wholesale" + r"/" + path_by_group):
            os.makedirs(OUT_FOLDER + r"/" + "Wholesale" + r"/" + path_by_group)

        if not os.path.isdir(OUT_FOLDER + r"/" + "Wholesale" + r"/" + "ALL"):
            os.makedirs(OUT_FOLDER + r"/" + "Wholesale" + r"/" + "ALL")

        img = create_image(DB, item, labels=["Product Code", "Group", "Category"])
        img.save(
            OUT_FOLDER
            + r"/"
            + "Wholesale"
            + r"/"
            + path_by_time_tag
            + r"/"
            + item
            + ".jpg"
        )
        img.save(
            OUT_FOLDER
            + r"/"
            + "Wholesale"
            + r"/"
            + path_by_group
            + r"/"
            + item
            + ".jpg"
        )
        img.save(OUT_FOLDER + r"/" + "Wholesale" + r"/" + "ALL" + r"/" + item + ".jpg")
        printer(f"{item} - Created image for wholesale.")

        if (DB.at[item, "MissingMinQty"] is True) or (
            (DB.at[item, "MissingOrdUnit"] is True)
        ):
            eprinter(f"{item} - Skipped due to missing 'Min Ord' value.")

            # update progress bar
            progress += incr
            objProgressBar["value"] = progress
            ROOT.update_idletasks()

            continue

        for price_col in PRICE_COLS:

            if DB.at[item, "Category"] == "":
                printer(
                    f"{item} - Skipped for col {price_col} due to missing category."
                )
                continue

            if DB.at[item, "ValueMissing_Column_" + price_col] is False:
                # eprinter(f"{item} - Skipped for col {price_col} due to missing value.")

                printer(f"{item} - Creating retail image for col {price_col}.")
                img = create_image(
                    DB,
                    item,
                    labels=["Product Code", "Group", "Category", "Rate", "Min Ord"],
                    rate_col=price_col,
                )
                if not os.path.isdir(
                    OUT_FOLDER + r"/" + price_col + r"/" + path_by_time_tag
                ):
                    os.makedirs(OUT_FOLDER + r"/" + price_col + r"/" + path_by_time_tag)

                if not os.path.isdir(
                    OUT_FOLDER + r"/" + price_col + r"/" + path_by_group
                ):
                    os.makedirs(OUT_FOLDER + r"/" + price_col + r"/" + path_by_group)

                if not os.path.isdir(OUT_FOLDER + r"/" + price_col + r"/" + "ALL"):
                    os.makedirs(OUT_FOLDER + r"/" + price_col + r"/" + "ALL")

                img.save(
                    OUT_FOLDER
                    + r"/"
                    + price_col
                    + r"/"
                    + path_by_group
                    + r"/"
                    + item
                    + ".jpg"
                )
                img.save(
                    OUT_FOLDER
                    + r"/"
                    + price_col
                    + r"/"
                    + path_by_time_tag
                    + r"/"
                    + item
                    + ".jpg"
                )
                img.save(
                    OUT_FOLDER + r"/" + price_col + r"/" + "ALL" + r"/" + item + ".jpg"
                )
                # TODO: del(img)
                printer(f"{item} - Created retail image for col {price_col}.")

        # update progress bar
        progress += incr
        objProgressBar["value"] = progress
        ROOT.update_idletasks()

    printer("Finished generating JPGs.")

    generate_missing_report(OUT_FOLDER=OUT_FOLDER)


def generate_pdf(
    entryMainXLSXPath,
    entryPurchaseXLSXPath,
    entryImagesFolder,
    entryOutputFolder,
    entryLabelsPerLine,
    entryPriceCols,
    objProgressBar,
):

    from tkinter import messagebox
    from utils import printer, eprinter

    global DB, PRICE_COLS, LABELS_PER_LINE, ROOT

    OUT_FOLDER = entryOutputFolder.get() + r"/"
    date_time = datetime.now().strftime("%d_%b_%y_%H_%M_%S")
    OUT_FILE = OUT_FOLDER + "Catalogue_" + date_time
    printer("Set output file.")

    PRICE_COLS = entryPriceCols.get().split(",")
    if PRICE_COLS != [""]:
        for i in range(len(PRICE_COLS)):
            PRICE_COLS[i] = PRICE_COLS[i].strip()
    else:
        eprinter(
            "No price columns specified! Please specify at least one price column to generate PDF."
        )
        messagebox.showerror(
            "Missing price columns",
            "No price columns specified! Please specify at least one price column to generate PDF.",
        )
        return

    printer("Set price columns.")

    LABELS_PER_LINE = int(entryLabelsPerLine.get())
    printer("Set number of labels per line.")

    preprocess(
        entryMainXLSXPath.get(), entryPurchaseXLSXPath.get(), entryImagesFolder.get()
    )
    DB.to_csv("Test.csv")
    for col in PRICE_COLS:
        create_pdf(DB, col, OUT_FILE, objProgressBar, ROOT)

    generate_missing_report(
        OUT_FILE=OUT_FOLDER + "SkippedItems_PDF_" + date_time + ".csv"
    )
