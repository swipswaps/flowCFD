#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def debug_timeline_render():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture all console messages
        page.on('console', lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
        page.on('pageerror', lambda error: print(f"PAGE ERROR: {error}"))
        
        try:
            print("=== DEBUGGING TIMELINE RENDERING ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(3000)
            
            # Check for MultiTrackTimeline element
            timeline_main = await page.query_selector('.multi-track-timeline')
            print(f"MultiTrackTimeline element found: {timeline_main is not None}")
            
            # Check all divs to see what's actually on the page
            all_divs = await page.query_selector_all('div')
            print(f"Total DIV elements: {len(all_divs)}")
            
            # Look for any elements with track in text
            elements_with_track_text = await page.query_selector_all('text=/.*Track.*/')
            print(f"Elements with 'Track' text: {len(elements_with_track_text)}")
            
            for i, elem in enumerate(elements_with_track_text[:5]):
                try:
                    text = await elem.inner_text()
                    print(f"  {i+1}. '{text}'")
                except:
                    print(f"  {i+1}. Error getting text")
            
            # Check if there are any error boundaries or fallbacks
            error_elements = await page.query_selector_all('text=/.*error.*/')
            print(f"Elements with 'error' text: {len(error_elements)}")
            
            # Take a screenshot for manual inspection
            await page.screenshot(path='/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/debug_timeline.png', full_page=True)
            print("Screenshot saved: debug_timeline.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_timeline_render())
