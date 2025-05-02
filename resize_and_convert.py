from PIL import Image
import os

# Constants
INPUT_FOLDER = 'screenshots'
OUTPUT_FOLDER = 'screenshots_resized'
TARGET_WIDTH = 1024

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Loop through .png screenshots
for filename in os.listdir(INPUT_FOLDER):
    if filename.lower().endswith(".png"):
        input_path = os.path.join(INPUT_FOLDER, filename)

        with Image.open(input_path) as img:
            # Maintain aspect ratio
            w_percent = TARGET_WIDTH / float(img.size[0])
            new_height = int(img.size[1] * w_percent)
            img_resized = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)

            # Save as JPEG
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(OUTPUT_FOLDER, f"{base_name}.jpg")
            img_resized.save(output_path, "JPEG", quality=90)

            print(f"Converted and saved: {output_path}")
