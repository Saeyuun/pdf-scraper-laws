import os
import re
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# === Directories ===
INPUT_DIR = "jurisprudence_downloads"
OUTPUT_DIR = "jurisprudence_cleaned"
MAX_WORKERS = 3  # Tune depending on your machine

# === Redundant watermark text to remove ===
texts_to_remove = [
    "Source: Supreme Court E-Library",
    "This page was dynamically generated",
    "by the E-Library Content Management System (E-LibCMS)"
]

# === Utility to sanitize a filename ===
def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|,\n\r]', "", text).strip().replace(" ", "_")

# === Counter and log for untitled files ===
untitled_counter = defaultdict(int)
untitled_logs = []

# === Extract case number title (e.g. G.R. No. 123456) ===
def extract_case_number_title(doc):
    try:
        text = doc[0].get_text("text")

        # Pattern for "Act No. ####" (case-insensitive)
        act_pattern = r"(Acts?\s+No\.?\s?\d+)"
        
        match = re.search(act_pattern, text, flags=re.IGNORECASE)
        if match:
            return sanitize_filename(match.group(1).strip())

        return None
    except Exception:
        return None


# === Clean a single PDF file ===
def clean_pdf(input_path):
    try:
        doc = fitz.open(input_path)

        # Get relative path for logging (e.g., 2024/01/file.pdf)
        rel_path = os.path.relpath(input_path, INPUT_DIR)
        year, month = rel_path.split(os.sep)[:2]
        original_file = os.path.basename(input_path)

        # Try to extract case number title
        title = extract_case_number_title(doc)
        if not title:
            untitled_counter["Untitled"] += 1
            untitled_num = untitled_counter["Untitled"]
            title = f"Untitled_{untitled_num}"
            untitled_logs.append(f"{title} -> {original_file} ({year}/{month})")

        for page in doc:
            # Remove all images
            for img in page.get_images(full=True):
                page.delete_image(img[0])
            page.wrap_contents()

            # Remove predefined text
            for text in texts_to_remove:
                rects = page.search_for(text)
                for rect in rects:
                    page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

        # === Output path with renamed file ===
        output_folder = os.path.join(OUTPUT_DIR, year, month)
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, f"{title}.pdf")

        doc.save(output_path)
        doc.close()

        return f"🧼 Cleaned & Renamed: {output_path}"
    except Exception as e:
        return f"❌ Failed: {input_path} — {e}"


# === Collect all PDF files to process ===
pdf_files = []
for root, _, files in os.walk(INPUT_DIR):
    for file in files:
        if file.endswith(".pdf"):
            pdf_files.append(os.path.join(root, file))

# === Run using multithreading ===
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(clean_pdf, path) for path in pdf_files]
    for future in as_completed(futures):
        print(future.result())

# === Write untitled logs to file ===
if untitled_logs:
    log_path = os.path.join(OUTPUT_DIR, "untitled_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(untitled_logs))
    print(f"\n📝 Untitled logs saved to: {log_path}")

print("\n✅ All PDFs cleaned and renamed.")
