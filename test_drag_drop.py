#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime

async def test_drag_drop():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable console logging
        page.on('console', lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
        page.on('pageerror', lambda error: print(f"PAGE ERROR: {error}"))
        
        try:
            print("=== TESTING DRAG AND DROP ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            # Wait for clips to load
            await page.wait_for_timeout(2000)
            
            # Look for draggable clips
            clips = await page.query_selector_all('[class*="timeline-clip"]')
            tracks = await page.query_selector_all('[class*="timeline-track"]')
            
            print(f"=== FOUND {len(clips)} CLIPS AND {len(tracks)} TRACKS ===")
            
            if len(clips) > 0 and len(tracks) > 1:
                # Get first clip and second track
                source_clip = clips[0]
                target_track = tracks[1]
                
                # Check if elements are visible
                clip_visible = await source_clip.is_visible()
                track_visible = await target_track.is_visible()
                
                print(f"Clip visible: {clip_visible}, Track visible: {track_visible}")
                
                if clip_visible and track_visible:
                    print("=== ATTEMPTING DRAG AND DROP ===")
                    
                    # Get positions
                    clip_box = await source_clip.bounding_box()
                    track_box = await target_track.bounding_box()
                    
                    if clip_box and track_box:
                        print(f"Clip at: {clip_box}, Track at: {track_box}")
                        
                        # Try drag and drop
                        await page.drag_and_drop(
                            f'[class*="timeline-clip"]:first-child',
                            f'[class*="timeline-track"]:nth-child(2)'
                        )
                        
                        print("=== DRAG DROP COMPLETED ===")
                        await page.wait_for_timeout(2000)
                    else:
                        print("Could not get bounding boxes")
                else:
                    print("Elements not visible")
            else:
                print("Not enough clips or tracks for drag test")
            
            # Take screenshot
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_dragdrop_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot: {screenshot_path}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drag_drop())
