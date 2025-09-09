#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import datetime

async def test_drag_with_logs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable detailed console logging
        def handle_console(msg):
            if any(keyword in msg.text for keyword in ['DRAG:', 'API:', '❌', '✅', '🎬', '🌐']):
                print(f"🔍 {msg.type.upper()}: {msg.text}")
            elif 'error' in msg.type.lower():
                print(f"❌ ERROR: {msg.text}")
                
        page.on('console', handle_console)
        page.on('pageerror', lambda error: print(f"💥 PAGE ERROR: {error}"))
        
        try:
            print("=== TESTING DRAG WITH DETAILED LOGS ===")
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            # Wait for timeline to load
            await page.wait_for_timeout(3000)
            
            # Look for specific clip elements
            clips = await page.query_selector_all('.timeline-clip')
            tracks = await page.query_selector_all('.timeline-track')
            
            print(f"📊 Found {len(clips)} clips and {len(tracks)} tracks")
            
            if len(clips) >= 1 and len(tracks) >= 2:
                print("🎯 Attempting drag and drop...")
                
                # Get clip and track positions
                clip = clips[0]
                source_track = tracks[0] 
                target_track = tracks[1]
                
                clip_text = await clip.inner_text()
                print(f"📎 Dragging clip: {clip_text}")
                
                # Perform drag and drop
                await clip.drag_to(target_track)
                
                print("⏱️ Waiting for API response...")
                await page.wait_for_timeout(3000)
                
                print("✅ Drag operation completed")
            else:
                print("❌ Not enough clips/tracks for testing")
            
            # Take screenshot
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/home/owner/Documents/11jCGEGBvO1kUgS4ZunQjvgbnxiz3n-_4/screenshot_dragtest_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot: {screenshot_path}")
            
        except Exception as e:
            print(f"💥 Test Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drag_with_logs())
