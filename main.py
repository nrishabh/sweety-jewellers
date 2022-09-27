import os
import app

if __name__ == '__main__':
    if not os.path.exists(r"data/logs/"):
        os.makedirs(r"data/logs/")
    try:
        app.gui_custom.main()
    except Exception as e:
        app.custom_logging(e)