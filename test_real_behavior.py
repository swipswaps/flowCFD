#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_real_behavior():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture ALL console messages to see what's really happening
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        page.on('pageerror', lambda error: print(f"ERROR: {error}"))
        
        try:
            print("=== TESTING REAL SLIDING/SNAPPING BEHAVIOR ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(3000)
            
            # Take initial screenshot
            await page.screenshot(path='/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/before_drag.png', full_page=True)
            print("📸 Before screenshot: before_drag.png")
            
            # Get actual clip positions and sizes
            clips = await page.query_selector_all('.timeline-clip')
            print(f"\n=== FOUND {len(clips)} CLIPS ===")
            
            for i, clip in enumerate(clips):
                try:
                    box = await clip.bounding_box()
                    text = await clip.inner_text()
                    print(f"Clip {i+1}: {text.strip()} at {box}")
                except:
                    print(f"Clip {i+1}: Error getting info")
            
            if len(clips) >= 2:
                print("\n=== TESTING MANUAL SNAP BEHAVIOR ===")
                clip1 = clips[0]
                clip2 = clips[1]
                
                clip1_box = await clip1.bounding_box()
                clip2_box = await clip2.bounding_box()
                
                if clip1_box and clip2_box:
                    print(f"Dragging clip from {clip1_box} near {clip2_box}")
                    
                    # Try to drag clip 1 very close to clip 2 (should snap)
                    start_x = clip1_box['x'] + clip1_box['width']/2
                    start_y = clip1_box['y'] + clip1_box['height']/2
                    
                    # Target: just 10 pixels before clip 2 (should trigger snapping)
                    target_x = clip2_box['x'] - 10
                    target_y = clip2_box['y'] + clip2_box['height']/2
                    
                    print(f"Drag from ({start_x}, {start_y}) to ({target_x}, {target_y})")
                    
                    await page.mouse.move(start_x, start_y)
                    await page.mouse.down()
                    await page.mouse.move(target_x, target_y)
                    await page.mouse.up()
                    
                    print("⏱️ Waiting for snapping to complete...")
                    await page.wait_for_timeout(4000)
                    
                    # Take after screenshot
                    await page.screenshot(path='/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/after_drag.png', full_page=True)
                    print("📸 After screenshot: after_drag.png")
                    
                    # Check final positions
                    final_clips = await page.query_selector_all('.timeline-clip')
                    print(f"\n=== FINAL POSITIONS ({len(final_clips)} clips) ===")
                    
                    for i, clip in enumerate(final_clips):
                        try:
                            box = await clip.bounding_box()
                            text = await clip.inner_text()
                            print(f"Clip {i+1}: {text.strip()} at {box}")
                        except:
                            print(f"Clip {i+1}: Error getting final info")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_real_behavior())
