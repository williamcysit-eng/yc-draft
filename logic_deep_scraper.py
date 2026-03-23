import json
import time
import random
from playwright.sync_api import sync_playwright

def deep_scrape_stealth(input_file="final_yc_links.jsonl", output_file="yc_details.jsonl"):
    with open(input_file, 'r') as f:
        urls = [json.loads(line)['url'] for line in f]

    with sync_playwright() as p:
        # 1. Run with headless=False to see if a CAPTCHA appears
        browser = p.chromium.launch(headless=False) 
        
        # 2. Add a convincing User-Agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        with open(output_file, 'a', encoding='utf-8') as f_out:
            for i, url in enumerate(urls):
                print(f"[{i+1}/{len(urls)}] Accessing: {url}")
                try:
                    # Randomize wait time between 3-7 seconds to look human
                    time.sleep(random.uniform(3, 7)) 
                    
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # Check for Cloudflare/Block page
                    if "Pardon our interruption" in page.content() or "Cloudflare" in page.content():
                        print("!! BLOCKED: Human intervention needed. Solve the CAPTCHA in the browser window !!")
                        page.wait_for_timeout(30000) # Wait for you to solve it manually
                    
                    # Wait for the specific company title
                    page.wait_for_selector("h1", timeout=15000)

                    data = {
                        "company_name": page.inner_text("h1"),
                        "description": page.inner_text("p") if page.query_selector("p") else "N/A",
                        "url": url
                    }
                    f_out.write(json.dumps(data) + '\n')
                    f_out.flush() # Ensure it saves even if it crashes later

                except Exception as e:
                    print(f"Skipping {url} due to error: {e}")
                    # Requirement: Handle exceptions correctly [cite: 121]
                    continue

        browser.close()

if __name__ == "__main__":
    deep_scrape_stealth()
