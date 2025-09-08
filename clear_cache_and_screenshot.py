#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime

async def clear_cache_and_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible browser
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("=== CLEARING ALL CACHE ===")
            await context.clear_cookies()
            await context.clear_permissions()
            
            print("=== GOING TO LOCALHOST:5173 ===")
            await page.goto("http://localhost:5173", timeout=15000)
            
            print("=== HARD REFRESH (CTRL+SHIFT+R) ===")
            await page.keyboard.press("Control+Shift+r")
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            print("=== WAITING FOR TIMELINE TO LOAD ===")
            await page.wait_for_selector('text="Multi-Track Timeline"', timeout=10000)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_after_cache_clear_{timestamp}.png"
            
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")
            
            # Check what buttons are actually present
            buttons = await page.query_selector_all('button')
            print(f"=== FOUND {len(buttons)} BUTTONS ===")
            
            for i, button in enumerate(buttons[:10]):  # First 10 buttons
                text = await button.inner_text()
                print(f"Button {i+1}: '{text}'")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(clear_cache_and_screenshot())
