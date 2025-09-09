#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_manual_drag():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable detailed console logging
        def handle_console(msg):
            if any(keyword in msg.text for keyword in ['DRAG:', 'API:', '❌', '✅', '🎬', '🌐']):
                print(f"🔍 CONSOLE: {msg.text}")
                
        page.on('console', handle_console)
        
        try:
            print("=== MANUAL DRAG TEST ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Get elements
            clips = await page.query_selector_all('.timeline-clip')
            tracks = await page.query_selector_all('.timeline-track')
            
            print(f"Found {len(clips)} clips and {len(tracks)} tracks")
            
            if len(clips) >= 1 and len(tracks) >= 2:
                # Get bounding boxes
                clip_box = await clips[0].bounding_box()
                track_box = await tracks[1].bounding_box()
                
                if clip_box and track_box:
                    # Manual drag using mouse events
                    print(f"Dragging from {clip_box} to {track_box}")
                    
                    # Start drag
                    await page.mouse.move(clip_box['x'] + clip_box['width']/2, clip_box['y'] + clip_box['height']/2)
                    await page.mouse.down()
                    
                    # Move to target
                    await page.mouse.move(track_box['x'] + 200, track_box['y'] + track_box['height']/2)
                    
                    # Drop
                    await page.mouse.up()
                    
                    print("Drag completed - waiting for logs...")
                    await page.wait_for_timeout(3000)
                else:
                    print("Could not get bounding boxes")
            else:
                print("Not enough elements for drag test")
            
            print("Test completed.")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_manual_drag())
