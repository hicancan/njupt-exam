import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        # Desktop Screenshot
        page_desktop = await browser.new_page(viewport={"width": 1200, "height": 800})
        await page_desktop.goto("http://localhost:5174/?class=B240402")
        await page_desktop.wait_for_selector(".fade-in") # Wait for rendering
        await asyncio.sleep(1) # Extra wait for animation
        await page_desktop.screenshot(path="public/assets/desktop_demo.png")
        await page_desktop.close()
        
        # Mobile Screenshot
        iphone_13 = p.devices['iPhone 13']
        context = await browser.new_context(**iphone_13)
        page_mobile = await context.new_page()
        await page_mobile.goto("http://localhost:5174/?class=B240402")
        await page_mobile.wait_for_selector(".fade-in")
        await asyncio.sleep(1)
        await page_mobile.screenshot(path="public/assets/mobile_demo.png")
        await context.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
