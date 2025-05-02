import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os


# Constants
CSV_PATH = 'military_bases.csv'
ROWS_TO_PROCESS = 5
WAIT_TIME = 5  # seconds

# Folder for screenshots
SCREENSHOT_DIR = "screenshots"
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
    name = row['id']
    lat = row['latitude']
    lon = row['longitude']
    
    url = f"https://earth.google.com/web/@{lat},{lon},500a,1000d,35y,0h,0t,0r"
    print(f"\nOpening {name} at URL:\n{url}")
    
    driver.get(url)
    time.sleep(WAIT_TIME)  # Allow Earth to load

    # Take a screenshot
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{index+1}_{name}.png")
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{index+1}_{name}.png")
    driver.save_screenshot(screenshot_path)
    print(f"Saved screenshot: {screenshot_path}")

# Keep browser open after loop (optional for debug)
input("Press Enter to close browser...")

driver.quit()