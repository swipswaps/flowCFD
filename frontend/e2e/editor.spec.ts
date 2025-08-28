import { test, expect } from '@playwright/test';
import path from 'path';

test('full user journey', async ({ page }) => {
  // 1. Navigate to the app
  await page.goto('/');

  // 2. Upload a video
  const videoFilename = 'test-video.mp4';
  const videoPath = path.join(__dirname, 'assets', videoFilename);
  
  const fileChooserPromise = page.waitForEvent('filechooser');
  await page.locator('input[type="file"]').click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(videoPath);

  // 3. Wait for upload to complete and assert success
  const successLocator = page.getByTestId('upload-success');
  const errorLocator = page.getByTestId('upload-error');

  // Wait for either the success or error message to appear
  await expect(successLocator.or(errorLocator)).toBeVisible({ timeout: 15000 });

  // Check if the error message is present and fail the test if it is
  const isError = await errorLocator.isVisible();
  if (isError) {
    const errorMessage = await errorLocator.textContent();
    throw new Error(`File upload failed with error: "${errorMessage}"`);
  }

  // If no error, assert that the success message is visible
  await expect(successLocator).toContainText(`Uploaded: ${videoFilename}`);

  // 4. Wait for the video player to be ready and loaded
  await page.waitForSelector('.vjs-tech', { state: 'visible' });
  await page.evaluate(() => {
    const video = document.querySelector('.vjs-tech') as HTMLVideoElement;
    return new Promise((resolve, reject) => {
      video.addEventListener('loadeddata', resolve);
      video.addEventListener('error', reject);
      if (video.readyState >= 3) { // HAVE_FUTURE_DATA
        resolve(true);
      }
    });
  });

  // 5. Mark a clip using keyboard shortcuts
  // Play the video for a moment, then mark in and out points
  await page.keyboard.press('k'); // Play
  await page.waitForTimeout(1000); // Wait 1 second
  const timeAfterPlay = await page.evaluate(() => (document.querySelector('.vjs-tech') as HTMLVideoElement).currentTime);
  expect(timeAfterPlay).toBeGreaterThan(0);

  await page.keyboard.press('i');  // Mark IN point
  await page.waitForTimeout(2000); // Wait 2 seconds
  await page.keyboard.press('o');  // Mark OUT point
  await page.keyboard.press('k'); // Pause

  // Check that the IN/OUT points have updated
  await expect(page.locator('.font-mono').nth(0)).not.toHaveText('00:00:00.000');
  await expect(page.locator('.font-mono').nth(1)).not.toHaveText('00:00:00.000');
  
  // 6. Add the clip to the timeline and verify player time doesn't jump
  const timeBeforeAdd = await page.evaluate(() => (document.querySelector('.vjs-tech') as HTMLVideoElement).currentTime);
  await page.getByRole('button', { name: 'Add Clip' }).click();
  
  // Verify the clip appears in the list
  await expect(page.locator('ul > li')).toHaveCount(1);
  await expect(page.locator('ul > li').first()).toContainText('→');

  const timeAfterAdd = await page.evaluate(() => (document.querySelector('.vjs-tech') as HTMLVideoElement).currentTime);
  expect(timeAfterAdd).toBeCloseTo(timeBeforeAdd, 1);

  // 7. Build the project and wait for success confirmation
  await page.getByRole('button', { name: 'Build Project (.osp)' }).click();
  await expect(page.locator('text=Project built successfully!')).toBeVisible({ timeout: 10000 });
  
  // 8. Export the video
  await page.getByRole('button', { name: 'Start Export' }).click();

  // 9. Wait for the export to complete and check for success or failure
  const downloadLink = page.getByRole('link', { name: 'Download MP4' });
  const exportError = page.locator('text=Export failed:');

  await expect(downloadLink.or(exportError)).toBeVisible({ timeout: 60000 });

  const isExportError = await exportError.isVisible();
  if (isExportError) {
    const errorMessage = await exportError.textContent();
    throw new Error(`Export failed with UI error: "${errorMessage}"`);
  }

  // 10. Verify the download link is valid
  await expect(downloadLink).toBeVisible();
  const href = await downloadLink.getAttribute('href');
  expect(href).toContain('/api/exports/');
  expect(href).toContain('/download');
});
