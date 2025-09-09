#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime

async def debug_ui_elements():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("=== DEBUGGING UI ELEMENTS ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            # Count all buttons
            all_buttons = await page.query_selector_all('button')
            print(f"=== FOUND {len(all_buttons)} TOTAL BUTTONS ===")
            
            # Get button text
            button_texts = []
            for i, button in enumerate(all_buttons[:15]):  # First 15 buttons
                try:
                    text = await button.inner_text()
                    visible = await button.is_visible()
                    button_texts.append(f"Button {i+1}: '{text}' (visible: {visible})")
                except:
                    button_texts.append(f"Button {i+1}: <error getting text>")
            
            for text in button_texts:
                print(text)
            
            # Check for specific elements
            timeline_sections = await page.query_selector_all('[class*="timeline"]')
            print(f"\n=== FOUND {len(timeline_sections)} TIMELINE ELEMENTS ===")
            
            # Look for any text containing key words
            add_elements = await page.query_selector_all('text=/.*Add.*/')
            mark_elements = await page.query_selector_all('text=/.*Mark.*/')
            video_elements = await page.query_selector_all('text=/.*Video.*/')
            
            print(f"\n=== TEXT SEARCH RESULTS ===")
            print(f"Elements with 'Add': {len(add_elements)}")
            print(f"Elements with 'Mark': {len(mark_elements)}")
            print(f"Elements with 'Video': {len(video_elements)}")
            
            # Take screenshot
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_debug_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"\nScreenshot saved to: {screenshot_path}")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ui_elements())
