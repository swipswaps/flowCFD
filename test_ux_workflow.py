#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime

async def test_ux_workflow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("=== TESTING UX WORKFLOW ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            print("=== TAKING SCREENSHOT OF UPDATED UI ===")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_ux_fixed_{timestamp}.png"
            
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")
            
            # Check for essential controls
            add_timeline_btn = await page.query_selector('text="Add to Timeline"')
            video_track_btn = await page.query_selector('text="Video Track"')
            mark_in_btn = await page.query_selector('text="Mark IN"')
            
            print(f"=== UX ELEMENTS FOUND ===")
            print(f"Add to Timeline button: {'✅' if add_timeline_btn else '❌'}")
            print(f"Video Track button: {'✅' if video_track_btn else '❌'}")
            print(f"Mark IN button: {'✅' if mark_in_btn else '❌'}")
            
            if add_timeline_btn:
                print("✅ Add to Timeline functionality restored")
            else:
                print("❌ Add to Timeline button not found")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ux_workflow())
