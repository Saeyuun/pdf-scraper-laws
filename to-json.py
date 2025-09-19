import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Constants
BASE_URL = "https://elibrary.judiciary.gov.ph"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CURRENT_YEAR = datetime.now().year
CURRENT_MONTH_INDEX = datetime.now().month - 1  # 0-indexed

def get_case_links(docmonth_url):
    print(f"🔍 Visiting: {docmonth_url}")
    try:
        response = requests.get(docmonth_url)
        if response.status_code != 200:
            print(f"❌ Failed to fetch {docmonth_url}")
            return []
    except Exception as e:
        print(f"❌ Error fetching {docmonth_url}: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    case_links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/thebookshelf/showdocs/28/" in href:
            full_url = href if href.startswith("http") else BASE_URL + href
            link_number = href.split("/")[-1]
            case_links.append({
                "link_number": link_number,
                "url": full_url
            })

    return case_links


def extract_case_data(case):
    url = case["url"]
    link_number = case["link_number"]

    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            print(f"❌ Failed to fetch {url}")
            return None

        soup = BeautifulSoup(res.content, "html.parser")

        # Extract title
        title_tag = soup.find("h3")
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"

        # Extract date
        date_tag = title_tag.find_next("p") if title_tag else None
        date = date_tag.get_text(strip=True) if date_tag else "Unknown"

        # Extract full content
        content = soup.find("div", class_="content")
        full_text = content.get_text(separator="\n", strip=True) if content else ""

        return {
            "link_number": link_number,
            "url": url,
            "title": title,
            "date": date,
            "full_text": full_text[:1000]  # Optional preview
        }

    except Exception as e:
        print(f"⚠️ Error processing {url}: {e}")
        return None

# === Loop through each year and month ===
for year in range(1900, CURRENT_YEAR + 1):
    for month_index, month in enumerate(MONTHS):
        if year == CURRENT_YEAR and month_index > CURRENT_MONTH_INDEX:
            break

        docmonth_url = f"{BASE_URL}/thebookshelf/docmonth/{month}/{year}/28"
        cases = get_case_links(docmonth_url)

        if not cases:
            print(f"📭 No cases found for {month} {year}, skipping...\n")
            continue

        results = []
        print(f"🚀 Starting multithreaded scraping for {month} {year}...")

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_case = {executor.submit(extract_case_data, case): case for case in cases}
            for future in as_completed(future_to_case):
                data = future.result()
                if data:
                    results.append(data)

        if results:
            os.makedirs("jurisprudence_detailed", exist_ok=True)
            filename = f"jurisprudence_detailed/jurisprudence_{year}_{month}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(results)} cases to {filename}\n")
        else:
            print(f"⚠️ No valid cases extracted for {month} {year}\n")
