#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_native_drag():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on('console', lambda msg: print(f"CONSOLE: {msg.text}"))
        
        try:
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(2000)
            
            print("=== TESTING NATIVE DRAG EVENTS ===")
            
            # Get clips
            clips = await page.query_selector_all('.timeline-clip')
            tracks = await page.query_selector_all('.timeline-track')
            
            print(f"Found {len(clips)} clips and {len(tracks)} tracks")
            
            if clips and tracks and len(tracks) >= 2:
                # Force click to test basic interaction
                print("\n=== TESTING FORCE CLICK ===")
                try:
                    await clips[0].click(force=True)
                    await page.wait_for_timeout(1000)
                    print("✅ Force click successful")
                except Exception as e:
                    print(f"❌ Force click failed: {e}")
                
                # Test drag using native HTML5 drag events
                print("\n=== TESTING NATIVE DRAG ===")
                
                source_clip = clips[0]
                target_track = tracks[1]
                
                # Get positions
                source_box = await source_clip.bounding_box()
                target_box = await target_track.bounding_box()
                
                if source_box and target_box:
                    print(f"Dragging from {source_box} to {target_box}")
                    
                    # Try using CDP (Chrome DevTools Protocol) for low-level events
                    await page.evaluate("""
                        (sourceSelector, targetSelector) => {
                            const source = document.querySelector(sourceSelector);
                            const target = document.querySelector(targetSelector);
                            
                            if (source && target) {
                                console.log('🎬 NATIVE: Starting drag simulation');
                                
                                // Create and dispatch dragstart event
                                const dragStart = new DragEvent('dragstart', {
                                    bubbles: true,
                                    cancelable: true,
                                    dataTransfer: new DataTransfer()
                                });
                                
                                source.dispatchEvent(dragStart);
                                console.log('🎬 NATIVE: Dragstart dispatched');
                                
                                // Create and dispatch dragover on target
                                const dragOver = new DragEvent('dragover', {
                                    bubbles: true,
                                    cancelable: true,
                                    dataTransfer: dragStart.dataTransfer
                                });
                                
                                target.dispatchEvent(dragOver);
                                console.log('🎬 NATIVE: Dragover dispatched');
                                
                                // Create and dispatch drop on target
                                const drop = new DragEvent('drop', {
                                    bubbles: true,
                                    cancelable: true,
                                    dataTransfer: dragStart.dataTransfer
                                });
                                
                                target.dispatchEvent(drop);
                                console.log('🎬 NATIVE: Drop dispatched');
                                
                                // Create and dispatch dragend on source
                                const dragEnd = new DragEvent('dragend', {
                                    bubbles: true,
                                    cancelable: true,
                                    dataTransfer: dragStart.dataTransfer
                                });
                                
                                source.dispatchEvent(dragEnd);
                                console.log('🎬 NATIVE: Dragend dispatched');
                            }
                        }
                    """, '.timeline-clip', '.timeline-track:nth-child(2)')
                    
                    print("⏱️ Waiting for drag events to process...")
                    await page.wait_for_timeout(3000)
                    
            print("Native drag test completed")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_native_drag())
