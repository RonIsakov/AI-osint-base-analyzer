import streamlit as st
import json
import os
from PIL import Image
import csv

# Load data.json
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Normalize data per base
bases = list(data.keys())
st.sidebar.title("Military Base Selection")
selected_base = st.sidebar.selectbox("Choose a base:", bases)

# Load base data
base_data = data[selected_base]
screenshots_dir = "screenshots"

import pandas as pd

csv_path = "military_bases.csv"
csv_coords = []

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        base_name = row.get("base") or row.get("base_name") or row.get("id")
        if base_name in data:
            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
            csv_coords.append({"base": base_name, "lat": lat, "lon": lon})

# Convert to DataFrame and plot
df_coords = pd.DataFrame(csv_coords)
st.subheader("🗺️ Base Locations Overview")
st.map(df_coords, zoom=2)


st.title(f"📍 Analysis for Base {selected_base}")

# Show screenshots
st.subheader("🖼️ Screenshot")
for file in sorted(os.listdir(screenshots_dir)):
    if file.endswith(".jpg") and file.split("_")[1].startswith(str(selected_base)):
        img_path = os.path.join(screenshots_dir, file)
        st.image(Image.open(img_path), caption=file, use_container_width=True)


# Show analyst findings
st.subheader("🔍 Analyst Observations")
analyst_history = base_data.get("analyst_history", [])

if not analyst_history:
    st.info("No analyst observations available for this base.")
else:
    for idx, entry in enumerate(analyst_history, start=1):
        with st.expander(f"Observation {idx}"):
            findings = entry.get("findings", [])
            analysis = entry.get("analysis", [])
            todo = entry.get("things_to_continue_analyzing", [])

            if findings:
                st.markdown("**Findings:**")
                st.markdown("\n".join(f"- {item}" for item in findings))

            if analysis:
                st.markdown("**Analysis:**")
                st.markdown("\n".join(f"- {item}" for item in analysis))

            if todo:
                st.markdown("**To Continue Analyzing:**")
                st.markdown("\n".join(f"- {item}" for item in todo))


# Show commander summary
st.subheader("🧠 Commander Summary")
commander = base_data.get("commander_summary", {})
st.markdown(f"**Summary:** {commander.get('summary', 'N/A')}")

st.markdown("**Insights:**")
for insight in commander.get("insights", []):
    st.markdown(f"- ✅ {insight}")

st.markdown("**Recommendations:**")
for rec in commander.get("recommendations", []):
    st.markdown(f"- ⚠️ {rec}")
