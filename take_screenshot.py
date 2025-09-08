#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime

async def take_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto("http://localhost:5173", timeout=10000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_current_{timestamp}.png"
            
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshot())
