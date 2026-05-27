import asyncio
import subprocess
import time
import urllib.request
import urllib.error
import os
import signal
from playwright.async_api import async_playwright

async def wait_for_server(url, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url)
            return True
        except urllib.error.URLError:
            await asyncio.sleep(1)
    return False

async def run():
    print("Starting Vite dev server...")
    # Start the dev server
    # Use shell=True for Windows compatibility with npm
    process = subprocess.Popen(
        "npm run dev -- --port 5174", 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        cwd=os.path.join(os.path.dirname(__file__), "..")
    )

    url = "http://localhost:5174/?class=B240402"
    
    print(f"Waiting for server to be ready at {url}...")
    server_ready = await wait_for_server("http://localhost:5174")
    
    if not server_ready:
        print("Error: Dev server did not start in time.")
        process.kill()
        return

    print("Server is ready! Launching Playwright...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            # 1. Desktop Screenshot
            print("Capturing Desktop screenshot...")
            page_desktop = await browser.new_page(viewport={"width": 1200, "height": 800})
            await page_desktop.goto(url)
            # Wait for main content animation to finish
            await page_desktop.wait_for_selector(".fade-in", state="visible")
            await asyncio.sleep(1.5) 
            await page_desktop.screenshot(path=os.path.join(os.path.dirname(__file__), "../public/assets/desktop_demo.png"))
            await page_desktop.close()
            print("Desktop screenshot saved as desktop_demo.png")
            
            # 2. Mobile Screenshot
            print("Capturing Mobile screenshot (iPhone 13)...")
            iphone_13 = p.devices['iPhone 13']
            context = await browser.new_context(**iphone_13)
            page_mobile = await context.new_page()
            await page_mobile.goto(url)
            # Wait for main content animation to finish
            await page_mobile.wait_for_selector(".fade-in", state="visible")
            await asyncio.sleep(1.5)
            await page_mobile.screenshot(path=os.path.join(os.path.dirname(__file__), "../public/assets/mobile_demo.png"))
            await context.close()
            print("Mobile screenshot saved as mobile_demo.png")
            
            await browser.close()
    finally:
        print("Shutting down dev server...")
        # Cross-platform kill for subprocess created with shell=True
        if os.name == 'nt':
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        print("All done!")

if __name__ == "__main__":
    asyncio.run(run())
