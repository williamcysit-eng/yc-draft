import json
import asyncio
import random
from playwright.async_api import async_playwright

INPUT_FILE = "final_yc_links.jsonl"
OUTPUT_FILE = "yc_detailed_data.jsonl"
CONCURRENCY = 5

async def get_clean_text(page, selector):
    """Helper to get text even if the element is 'hidden' or weird."""
    try:
        element = page.locator(selector).first
        await element.wait_for(state="attached", timeout=10000)
        return await element.evaluate("el => el.textContent")
    except:
        return None

async def worker(semaphore, browser, url, index, total, f_out):
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        print(f"[{index+1}/{total}] Processing: {url}")
        
        try:
            # We use 'commit' (the moment the URL starts loading) 
            # instead of waiting for full load, then we handle the wait ourselves.
            await page.goto(url, wait_until="commit", timeout=60000)
            
            await asyncio.sleep(2) # Small buffer for JS to kick in

            name = await get_clean_text(page, "h1")
            
            # Fallback: If H1 fails, use the page Title (YC usually puts company name there)
            if not name:
                name = await page.title()
                name = name.replace(" | Y Combinator", "").strip()

            description = await get_clean_text(page, "p.whitespace-pre-line") or "N/A"

            data = {
                "company_name": name,
                "description": description[:500],
                "url": url
            }
            
            f_out.write(json.dumps(data) + '\n')
            f_out.flush()
            print(f"✓ Success: {name}")

        except Exception as e:
            print(f"× Failed {url}: {str(e)[:50]}")
        finally:
            await context.close()

async def main():
    with open(INPUT_FILE, 'r') as f:
        urls = [json.loads(line)['url'] for line in f]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        semaphore = asyncio.Semaphore(CONCURRENCY)

        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
            tasks = [worker(semaphore, browser, url, i, len(urls), f_out) for i, url in enumerate(urls)]
            await asyncio.gather(*tasks, return_exceptions=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
