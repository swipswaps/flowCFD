#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_actual_drag():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        
        try:
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(2000)
            
            print("=== TESTING ACTUAL DRAG WITH WORKING CLICKS ===")
            
            clips = await page.query_selector_all('.timeline-clip')
            tracks = await page.query_selector_all('.timeline-track')
            
            print(f"Found {len(clips)} clips and {len(tracks)} tracks")
            
            if clips and tracks and len(tracks) >= 2:
                source_clip = clips[0]
                target_track = tracks[1]
                
                source_box = await source_clip.bounding_box()
                target_box = await target_track.bounding_box()
                
                if source_box and target_box:
                    print(f"Performing real drag from clip to track...")
                    
                    # Use actual mouse drag operations
                    start_x = source_box['x'] + source_box['width']/2
                    start_y = source_box['y'] + source_box['height']/2
                    
                    end_x = target_box['x'] + 300  # Middle of target track
                    end_y = target_box['y'] + target_box['height']/2
                    
                    print(f"Drag coordinates: ({start_x}, {start_y}) → ({end_x}, {end_y})")
                    
                    # Perform smooth drag operation
                    await page.mouse.move(start_x, start_y)
                    await page.mouse.down()
                    
                    # Slow drag to allow React DnD to register
                    steps = 10
                    for i in range(steps + 1):
                        progress = i / steps
                        curr_x = start_x + (end_x - start_x) * progress
                        curr_y = start_y + (end_y - start_y) * progress
                        await page.mouse.move(curr_x, curr_y)
                        await page.wait_for_timeout(50)  # Slow drag
                    
                    await page.mouse.up()
                    
                    print("⏱️ Waiting for drag events to complete...")
                    await page.wait_for_timeout(4000)
            
            print("Actual drag test completed")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_actual_drag())
