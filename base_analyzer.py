import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from PIL import Image

# === Load API Key ===
api_key = os.getenv("OPENROUTER_API_KEY")

# Constants
CSV_PATH = 'military_bases.csv'
ROWS_TO_PROCESS = 5
WAIT_TIME = 5
SCREENSHOT_DIR = 'screenshots'
TARGET_WIDTH = 1024

# Folder for screenshots
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# Load CSV
df = pd.read_csv(CSV_PATH)
df_subset = df.head(ROWS_TO_PROCESS)

# Selenium Chrome setup (non-headless for debugging)
options = Options()
options.headless = False
driver = webdriver.Chrome(options=options)

# Loop over rows and open Google Earth URLs
for index, row in df_subset.iterrows():
    base_id  = row['id']
    lat = row['latitude']
    lon = row['longitude']
    
    url = f"https://earth.google.com/web/@{lat},{lon},500a,1000d,35y,0h,0t,0r"
    print(f"\nOpening {base_id } at URL:\n{url}")
    
    driver.get(url)
    time.sleep(WAIT_TIME)  # Allow Earth to load

    # Take a screenshot
    png_path = os.path.join(SCREENSHOT_DIR, f"{index+1}_{base_id}.png")
    jpg_path = os.path.join(SCREENSHOT_DIR, f"{index+1}_{base_id}.jpg")
    driver.save_screenshot(png_path)
    print(f"Saved screenshot: {png_path}")

    # --- Resize + Convert to JPG ---
    with Image.open(png_path) as img:
        w_percent = TARGET_WIDTH / float(img.size[0])
        new_height = int(img.size[1] * w_percent)
        img_resized = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
        img_resized.save(jpg_path, "JPEG", quality=90)
        print(f"Resized and saved as JPEG: {jpg_path}")

        # --- Remove the original PNG ---
    os.remove(png_path)
    print(f"Deleted original PNG: {png_path}")

# Keep browser open after loop (optional for debug)
input("Press Enter to close browser...")

driver.quit()