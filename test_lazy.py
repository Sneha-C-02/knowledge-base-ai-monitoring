import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to KB_Chem/Sample_Preparation")
        await page.goto('https://support.waters.com/KB_Chem/Sample_Preparation', wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        links = await page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href)")
        articles = [l for l in links if "WKB" in l or "WAT" in l]
        print(f"Found {len(set(articles))} articles statically")
        
        # Try to click any pagination next buttons or load more
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(2000)
            
            # Click ui-pagination next if it exists
            next_exists = await page.evaluate("document.querySelector('.ui-pagination-next a') !== null")
            if next_exists:
                print("Clicking pagination next...")
                await page.click('.ui-pagination-next a')
                await page.wait_for_timeout(3000)
                
            # Click load more if it exists
            load_more_exists = await page.evaluate("document.querySelector('.mt-load-more') !== null")
            if load_more_exists:
                print("Clicking load more...")
                await page.click('.mt-load-more')
                await page.wait_for_timeout(3000)
                
        links2 = await page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href)")
        articles2 = [l for l in links2 if "WKB" in l or "WAT" in l]
        print(f"Found {len(set(articles2))} articles after interactions")
        
        await browser.close()

asyncio.run(main())
