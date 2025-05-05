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
import re


# Ensure .env is loaded
load_dotenv()  

# === Load API Key ===
api_key = os.getenv("OPENROUTER_API_KEY")

# Constants
CSV_PATH = 'military_bases.csv'
ROWS_TO_PROCESS = 25
WAIT_TIME = 5
SCREENSHOT_DIR = 'screenshots'
TARGET_WIDTH = 1024
DATA_PATH = 'data.json'
NUMBER_OF_ANALYSTS = 8

# Load existing data if exists, otherwise create empty dict
if os.path.exists(DATA_PATH):
    with open(DATA_PATH, 'r') as f:
        all_data = json.load(f)
else:
    all_data = {}

# Folder for screenshots
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# Load CSV
df = pd.read_csv(CSV_PATH)
df_subset = df.head(ROWS_TO_PROCESS)

# Selenium Chrome setup (non-headless for debugging)
options = Options()
options.headless = False
driver = webdriver.Chrome(options=options)

# Function to parse latitude, longitude, and zoom from URL
def parse_lat_lon_zoom(url):
    try:
        parts = url.split("@")[1].split(",")
        lat = float(parts[0])
        lon = float(parts[1])
        zoom = float(parts[2].replace("a", ""))  # Strip the 'a'
        return lat, lon, zoom
    except Exception as e:
        print(f"❌ Failed to parse URL: {e}")
        return None, None, None

# Loop over rows and open Google Earth URLs
for index, row in df_subset.iterrows():
    base_id  = row['id']
    
    # Check if base_id already exists in all_dat
    if str(base_id) in all_data:
        print(f"⏩ Skipping base {base_id} — already analyzed.")
        continue

    lat = row['latitude']
    lon = row['longitude']
    country = row["country"]
    
    initial_url = f"https://earth.google.com/web/@{lat},{lon},500a,1000d,35y,0h,0t,0r"
    lat, lon, zoom = parse_lat_lon_zoom(initial_url)
    print(f"📍 Start view — lat={lat}, lon={lon}, zoom={zoom}")
    
    driver.get(initial_url)
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

    history_of_analysts = []

    for analyst in range(NUMBER_OF_ANALYSTS):
        
        # === Read and encode image ===
        with open(jpg_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # === Build prompt ===
        if analyst == 0:
            prompt = (
            f"You are an expert in understanding satellite imagery and you work for the US army. "
            f"We got intel that this area is a base/facility of the military of {country}. "
            "Analyze this image and respond ONLY with a JSON object containing the following keys:\n"
            "1. 'findings': A list of findings that you think are important for the US army to know, including "
            "all man-made structures, military equipment, and infrastructure make sure to start each finding in a new line.\n"
            "2. 'analysis': A detailed analysis of your findings make sure to start each finding in a new line.\n"
            "3. 'things_to_continue_analyzing': A list of things that you think are important to continue "
            "analyzing in further images make sure to start each thing in a new line.\n"
            "4. 'action': One of ['zoom-in', 'zoom-out', 'move-left', 'move-right'] based on what "
            "would help you analyze the image or area better.\n" 
            "Respond ONLY with valid JSON. Do not include explanations or extra text."
            )
        else:
            previous = "\n\n".join(
            [f"Analyst {i+1}: Findings: {h['findings']}\nAnalysis: {h['analysis']}\nAction: {h['action']}" for i, h in enumerate(history_of_analysts)]
            )
            prompt = (
                "Here is the analysis of previous analysts about this area and their recommendations.\n"
                f"You can use this data but don’t use it as fact, think for yourself:\n {previous}."
                "You are an expert in understanding satellite imagery and you work for the US army. "
                f"We got intel that this area is a base/facility of the military of {country}. "
                "Analyze this image and respond ONLY with a JSON object containing the following keys:\n"
                "1. 'findings': A list of findings that you think are important for the US army to know, including "
                "all man-made structures, military equipment, and infrastructure make sure to start each finding in a new line.\n"
                "2. 'analysis': A detailed analysis of your findings make sure to start each finding in a new line.\n"
                "3. 'things_to_continue_analyzing': A list of things that you think are important to continue "
                "analyzing in further images make sure to start each thing in a new line.\n"
                "4. 'action': One of ['zoom-in', 'zoom-out', 'move-left', 'move-right'] based on what "
                "would help you analyze the image or area better.\n"
                "answer zoom-in if you think that the image is not clear enough.\n or you are missing some key details.\n" 
                "dont answer zoom-in if you think that the image is clear enough.\n"
                "answer zoom-out if you think that the image is too zoomed in.\n" \
                "answer move-left if you think that the image is not showing the whole area and needs to be more centerd to the left.\n" 
                "answer move-right if you think that the image is not showing the whole area and needs to be more centerd to the right.\n"
                "Respond ONLY with valid JSON. Do not include explanations or extra text."
                )

        # === OpenRouter API call ===
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://yourproject.com",  # required by OpenRouter
            "X-Title": "osint-military-analysis"
        }

        payload = {
            "model":"meta-llama/llama-3-70b-instruct",
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
            analysis_clean = re.sub(r",\s*([\]}])", r"\1", analysis_clean)  # Remove trailing commas
            try:
                parsed_json = json.loads(analysis_clean)
                history_of_analysts.append(parsed_json)
                print("\n✅ Parsed JSON:")
                print(parsed_json)
                action = parsed_json.get("action", "finish")
                if action == "zoom-in":
                    zoom = max(0.01, zoom * 0.5)
                elif action == "zoom-out":
                    zoom = zoom * 1.5
                elif action == "move-left":
                    lon -= 0.05
                elif action == "move-right":
                        lon += 0.05
                new_url = f"https://earth.google.com/web/@{lat},{lon},{zoom}a,1000d,35y,0h,0t,0r"
                print(f"🔁 Analyst {analyst+1} action: {action} → New view:\n{new_url}")
                driver.get(new_url)
                time.sleep(WAIT_TIME)
            
            except json.JSONDecodeError as e:
                print("❌ JSON parsing failed:")
                print(e)
                print("Raw response:")
                print(analysis_clean)

        except Exception as e:
            print(f"❌ Error analyzing {base_id}: {e}")


    model = "meta-llama/llama-3-70b-instruct"
        
        # === Commander-Level Report ===
    commander_prompt = (
        "You are a senior US military commander reviewing satellite analysis of a potential enemy base.\n"
        "Here is the full history of analyst observations from multiple experts:\n\n"
        f"{json.dumps(history_of_analysts, indent=2)}\n\n"
        "Please synthesize these into:\n"
        "1. A concise executive summary (~4 sentences).\n"
        "2. A prioritized list of strategic insights.\n"
        "3. Final recommendations for further surveillance or action.\n\n"
        "Only return valid JSON with keys: 'summary', 'insights', and 'recommendations'."
    )
    print(f"📦 Commander prompt size (chars): {len(commander_prompt)}")

    commander_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": commander_prompt}]
            }
        ]
    }

    try:
        commander_response = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=commander_payload, timeout=60)
        result = commander_response.json()
        print(f"🔍 Commander response status: {commander_response.status_code}")

        try:
            final_report = result["choices"][0]["message"]["content"]
            if not final_report.strip():
                raise ValueError("Empty response from Phi-4 model")
        except Exception as e:
            print("❌ Commander summary missing or invalid:")
            print(result)
            raise e


        # Clean JSON if needed
                # === Strip explanation and extract JSON block ===
        match = re.search(r"\{.*\}", final_report, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON block found in commander response.")

        final_report_clean = match.group(0)
        if final_report_clean.startswith("```json"):
            final_report_clean = final_report_clean.replace("```json", "").replace("```", "").strip()
        final_report_clean = re.sub(r",\s*([\]}])", r"\1", final_report_clean)
        try:
            commander_json = json.loads(final_report_clean)
            print("\nFinal Commander Report:")
            print(json.dumps(commander_json, indent=2))
        except json.JSONDecodeError as e:
            print("❌ JSON decoding failed for commander report:")
            print(final_report_clean)
            raise e
        
            # Store all collected data
        all_data[str(base_id)] = {
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "analyst_history": history_of_analysts,
            "commander_summary": commander_json
        }
        
        
        with open(DATA_PATH, 'w') as f:
            json.dump(all_data, f, indent=2)
            print(f"💾 Saved analysis for base {base_id} to {DATA_PATH}")

    except Exception as e:
        print("❌ Commander summary generation failed:")
        print(e)

# Keep browser open after loop (optional for debug)
input("Press Enter to close browser...")

driver.quit()


    
