import os
import re
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# === Directories ===
INPUT_DIR = "jurisprudence_downloads"
OUTPUT_DIR = "jurisprudence_cleaned"
MAX_WORKERS = 6  # Adjust based on your CPU

# === Texts to remove ===
texts_to_remove = [
    "Source: Supreme Court E-Library",
    "This page was dynamically generated",
    "by the E-Library Content Management System (E-LibCMS)"
]

untitled_counter = defaultdict(int)

# === Sanitize title to filename ===
def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|,\n\r]', "", text).strip().replace(" ", "_")

# === Extract readable title from first page ===
def extract_title(doc):
    try:
        text = doc[0].get_text("text")
        # Match citations like: 322 Phil. 122, 123 SCRA 456, etc.
        citation_match = re.search(r"\b(\d+)\s+(Phil\.|SCRA|OG|SCAD)\s+(\d+)", text)
        if citation_match:
            part1 = citation_match.group(1)
            part2 = citation_match.group(2).replace('.', '')  # remove dot from Phil.
            part3 = citation_match.group(3)
            return f"{part1}_{part2}_{part3}"
        return "Untitled"
    except Exception:
        return "Untitled"

# === Clean + Rename Single PDF ===
def clean_pdf(input_path):
    try:
        doc = fitz.open(input_path)

        title = extract_title(doc)
        if title == "Untitled":
            untitled_counter["Untitled"] += 1
            title = f"Untitled_{untitled_counter['Untitled']}"

        for page in doc:
            for img in page.get_images(full=True):
                page.delete_image(img[0])
            page.wrap_contents()

            for text in texts_to_remove:
                rects = page.search_for(text)
                for rect in rects:
                    page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

        # Build output path
        rel_path = os.path.relpath(input_path, INPUT_DIR)
        year, month = rel_path.split(os.sep)[:2]
        output_folder = os.path.join(OUTPUT_DIR, year, month)
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{title}.pdf")
        doc.save(output_file)
        doc.close()

        return f"🧼 Cleaned & Renamed: {output_file}"
    except Exception as e:
        return f"❌ Failed: {input_path} — {e}"

# === Collect all PDF paths ===
pdf_files = []
for root, _, files in os.walk(INPUT_DIR):
    for file in files:
        if file.endswith(".pdf"):
            pdf_files.append(os.path.join(root, file))

# === Run multithreaded cleaning ===
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(clean_pdf, path) for path in pdf_files]
    for future in as_completed(futures):
        print(future.result())

print("\n✅ All PDFs cleaned and renamed with multithreading.")
