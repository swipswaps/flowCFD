#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def debug_drag_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        
        try:
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(2000)
            
            print("=== DEBUGGING DRAG EVENTS ===")
            
            # Check if clips are actually draggable
            clips = await page.query_selector_all('.timeline-clip')
            print(f"Found {len(clips)} clips")
            
            if clips:
                clip = clips[0]
                
                # Check element properties
                draggable = await clip.get_attribute('draggable')
                style = await clip.get_attribute('style')
                class_name = await clip.get_attribute('class')
                
                print(f"Clip draggable attribute: {draggable}")
                print(f"Clip class: {class_name}")
                print(f"Clip style: {style[:100]}...")
                
                # Test basic click
                print("\n=== TESTING BASIC CLICK ===")
                await clip.click()
                await page.wait_for_timeout(1000)
                
                # Test mousedown/mouseup without movement
                print("\n=== TESTING MOUSEDOWN/MOUSEUP ===")
                box = await clip.bounding_box()
                if box:
                    x = box['x'] + box['width']/2
                    y = box['y'] + box['height']/2
                    
                    await page.mouse.move(x, y)
                    await page.mouse.down()
                    await page.wait_for_timeout(500)
                    await page.mouse.up()
                    await page.wait_for_timeout(1000)
                
                # Test if React DnD is working by checking for drag cursor
                print("\n=== TESTING DRAG START ===")
                await page.mouse.move(x, y)
                await page.mouse.down()
                await page.wait_for_timeout(1000)  # Hold down longer
                
                # Check if cursor changed (indicates drag started)
                cursor_info = await page.evaluate("document.body.style.cursor")
                print(f"Cursor during drag: {cursor_info}")
                
                await page.mouse.up()
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_drag_events())
