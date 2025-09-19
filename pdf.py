import os
import json
import time
import re
import pdfkit
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Configuration ===
JSON_DIR = "jurisprudence_detailed"
OUTPUT_DIR = "jurisprudence_downloads"
MAX_WORKERS = 4

# === Configure wkhtmltopdf ===
config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")


# === Sanitize filename utility ===
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|,]', "", name).strip().replace(" ", "_")

# === Download and export PDF from URL directly ===
def download_case(case, year, month):
    try:
        link_number = case["link_number"]
        url = f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocsfriendly/28/{link_number}"

        folder_path = os.path.join(OUTPUT_DIR, year, month)
        os.makedirs(folder_path, exist_ok=True)
        output_pdf = os.path.join(folder_path, f"{link_number}.pdf")

        if os.path.exists(output_pdf):
            return f"✅ Already exists: {output_pdf}"

        # Generate PDF directly from URL
        pdfkit.from_url(url, output_pdf, configuration=config, options={
            'quiet': '',
            'no-stop-slow-scripts': '',
            'javascript-delay': '2000',
            'load-error-handling': 'ignore'
        })

        return f"📥 Saved PDF: {output_pdf}"

    except Exception as e:
        return f"❌ Error saving {case.get('link_number')}: {e}"

# === Main process ===
for filename in os.listdir(JSON_DIR):
    if not filename.endswith(".json"):
        continue

    year_month = filename.replace("jurisprudence_", "").replace(".json", "")
    try:
        year, month = year_month.split("_")
    except ValueError:
        print(f"⚠️ Skipping malformed filename: {filename}")
        continue

    year = sanitize_filename(year)
    month = sanitize_filename(month)
    json_path = os.path.join(JSON_DIR, filename)

    with open(json_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"\n📂 Processing {year}/{month} ({len(cases)} cases)")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_case, case, year, month) for case in cases]
        for future in as_completed(futures):
            print(future.result())

print("\n✅ All PDFs downloaded successfully.")
