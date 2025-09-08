#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime
import time

async def verify_changes():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("=== WAITING FOR HOT RELOAD ===")
            time.sleep(3)  # Wait for hot reload
            
            print("=== LOADING LOCALHOST:5173 ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            print("=== TAKING VERIFICATION SCREENSHOT ===")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_after_removal_{timestamp}.png"
            
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")
            
            # Count timeline headers
            timeline_headers = await page.query_selector_all('text="🎬 Multi-Track Timeline"')
            print(f"=== FOUND {len(timeline_headers)} TIMELINE HEADERS ===")
            
            # Count all buttons
            all_buttons = await page.query_selector_all('button')
            print(f"=== FOUND {len(all_buttons)} TOTAL BUTTONS ===")
            
            # Look for specific button text from original screenshot
            play_buttons = await page.query_selector_all('text="Play"')
            mark_in_buttons = await page.query_selector_all('text="Mark IN"')
            print(f"=== FOUND {len(play_buttons)} PLAY BUTTONS, {len(mark_in_buttons)} MARK IN BUTTONS ===")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_changes())
