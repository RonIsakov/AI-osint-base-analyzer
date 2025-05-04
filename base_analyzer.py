import json
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from PIL import Image
import base64
import httpx
from dotenv import load_dotenv


# Ensure .env is loaded
load_dotenv()  

# === Load API Key ===
api_key = os.getenv("OPENROUTER_API_KEY")

# Constants
CSV_PATH = 'military_bases.csv'
ROWS_TO_PROCESS = 1
WAIT_TIME = 7
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

        # === Fetch country info for prompt ===
    country = row["country"]

    # === Read and encode image ===
    with open(jpg_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    # === Build prompt ===
    prompt = (
    f"You are an expert in understanding satellite imagery and you work for the US army. "
    f"We got intel that this area is a base/facility of the military of {country}. "
    "Analyze this image and respond ONLY with a JSON object containing the following keys:\n"
    "1. 'findings': A list of findings that you think are important for the US army to know, including "
    "all man-made structures, military equipment, and infrastructure make sure to start each finding in a new line.\n"
    "2. 'analysis': A detailed analysis of your findings make sure to start each finding in a new line.\n"
    "3. 'things_to_continue_analyzing': A list of things that you think are important to continue "
    "analyzing in further images make sure to start each thing in a new line.\n"
    "4. 'action': One of ['zoom-in', 'zoom-out', 'move-left', 'move-right', 'finish'] based on what "
    "would help you analyze the image or area better.\n"
    "Respond ONLY with valid JSON. Do not include explanations or extra text."
    )

    # === OpenRouter API call ===
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://yourproject.com",  # required by OpenRouter
        "X-Title": "osint-military-analysis"
    }

    payload = {
        "model": "google/gemini-2.5-flash-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]
    }

    try:
        response = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
        result = response.json()
        if "choices" in result:
            analysis = result["choices"][0]["message"]["content"]
        else:
            print("❌ Unexpected response format:")
            print(result)
            
        analysis = result["choices"][0]["message"]["content"]

        # Clean up the analysis string
        analysis_clean = analysis.strip()
        if analysis_clean.startswith("```json"):
            analysis_clean = analysis_clean.replace("```json", "").replace("```", "").strip()

        try:
            parsed_json = json.loads(analysis_clean)
            print("\n✅ Parsed JSON:")
            print(parsed_json)
            
        
        except json.JSONDecodeError as e:
            print("❌ JSON parsing failed:")
            print(e)
            print("Raw response:")
            print(analysis_clean)

    except Exception as e:
        print(f"❌ Error analyzing {base_id}: {e}")

    # Keep browser open after loop (optional for debug)
    input("Press Enter to close browser...")

driver.quit()