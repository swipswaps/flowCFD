#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def inspect_classes():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto("http://localhost:5173", timeout=15000)
            await page.wait_for_load_state('networkidle', timeout=15000)
            await page.wait_for_timeout(2000)
            
            print("=== INSPECTING CSS CLASSES ===")
            
            # Check all elements with timeline in the class
            timeline_elements = await page.query_selector_all('[class*="timeline"]')
            print(f"Elements with 'timeline' in class: {len(timeline_elements)}")
            
            for i, elem in enumerate(timeline_elements[:10]):
                try:
                    class_name = await elem.get_attribute('class')
                    tag_name = await elem.evaluate('el => el.tagName')
                    print(f"  {i+1}. {tag_name}: {class_name}")
                except:
                    print(f"  {i+1}. Error getting attributes")
            
            # Check for track classes
            track_elements = await page.query_selector_all('[class*="track"]')
            print(f"\nElements with 'track' in class: {len(track_elements)}")
            
            for i, elem in enumerate(track_elements[:5]):
                try:
                    class_name = await elem.get_attribute('class')
                    tag_name = await elem.evaluate('el => el.tagName')
                    print(f"  {i+1}. {tag_name}: {class_name}")
                except:
                    print(f"  {i+1}. Error getting attributes")
            
            # Check for clip classes
            clip_elements = await page.query_selector_all('[class*="clip"]')
            print(f"\nElements with 'clip' in class: {len(clip_elements)}")
            
            for i, elem in enumerate(clip_elements[:5]):
                try:
                    class_name = await elem.get_attribute('class')
                    tag_name = await elem.evaluate('el => el.tagName')
                    inner_text = await elem.inner_text()
                    print(f"  {i+1}. {tag_name}: {class_name} - '{inner_text[:30]}'")
                except:
                    print(f"  {i+1}. Error getting attributes")
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_classes())
