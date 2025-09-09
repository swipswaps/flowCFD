#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        
        try:
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(2000)
            
            clips = await page.query_selector_all('.timeline-clip')
            print(f"Found {len(clips)} clips")
            
            if clips:
                print("Clicking first clip...")
                await clips[0].click()
                await page.wait_for_timeout(1000)
                print("Click test completed")
            else:
                print("No clips found")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_click())
