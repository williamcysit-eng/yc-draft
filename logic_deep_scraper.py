import json
import asyncio
import random
from playwright.async_api import async_playwright

INPUT_FILE = "final_yc_links.jsonl"
OUTPUT_FILE = "yc_detailed_data.jsonl"
CONCURRENCY = 5

async def extract_field(page, selector, attribute=None):
    try:
        element = page.locator(selector).first
        await element.wait_for(state="attached", timeout=5000)
        if attribute:
            return await element.get_attribute(attribute)
        return await element.evaluate("el => el.textContent.trim()")
    except:
        return "N/A"

async def worker(semaphore, browser, url, index, total, f_out):
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        print(f"[{index+1}/{total}] Deep Scraping: {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            page_title = await page.title()
            name_from_tab = page_title.replace(" | Y Combinator", "").strip()

            try:
                await page.wait_for_function('document.querySelector("h1")?.innerText.length > 0', timeout=5000)
                name = await page.inner_text("h1")
            except:
                name = name_from_tab

            one_liner = "N/A"
            one_liner_loc = page.locator("div.text-xl")
            if await one_liner_loc.count() > 0:
                one_liner = await one_liner_loc.first.inner_text()

            stats = {}
            rows = await page.locator(".flex.flex-row.justify-between").all()
            for row in rows:
                row_text = await row.inner_text()
                if "\n" in row_text:
                    k, v = row_text.split("\n", 1)
                    stats[k.strip()] = v.strip()

            founders = []
            founder_section = page.locator("section:has-text('Founders')")
            if await founder_section.count() > 0:
                names = await founder_section.locator("div.font-bold").all_inner_texts()
                founders = [f.strip() for f in names if f.strip() and f.strip() not in ["Founders", "Active Founders"]]

            website = "N/A"
            links = await page.locator("a[href^='http']").all()
            for link in links:
                href = await link.get_attribute("href")
                # Strict ignore list for YC/StartupSchool/Socials
                if href and not any(x in href.lower() for x in ["ycombinator.com", "startupschool.org", "twitter.com", "linkedin.com", "facebook.com"]):
                    website = href
                    break

            data = {
                "company_name": name,
                "one_liner": one_liner,
                "description": await page.locator(".whitespace-pre-line").first.inner_text() if await page.locator(".whitespace-pre-line").count() > 0 else "N/A",
                "batch": stats.get("Batch", "N/A"),
                "location": stats.get("Location", "N/A"),
                "team_size": stats.get("Team Size", "N/A"),
                "founders": list(set(founders)),
                "website": website,
                "url": url
            }
            
            f_out.write(json.dumps(data) + '\n')
            f_out.flush()
            print(f"✓ Scraped: {name}")

        except Exception as e:
            print(f"× Error on {url}: {str(e)[:100]}")
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
