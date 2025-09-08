#!/usr/bin/env python3
"""
Phase 3: Quality Metrics Testing
Tests for SSIM/PSNR/VMAF quality analysis system.
"""

import unittest
import tempfile
import os
import shutil
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import ffmpeg_utils


class TestQualityMetrics(unittest.TestCase):
    """Test quality metrics calculation functions."""
    
    def setUp(self):
        """Set up test environment with temporary directories."""
        self.test_dir = tempfile.mkdtemp()
        self.test_video_path = None
        
        # Try to find an existing test video
        possible_paths = [
            "../store/uploads/de6dc9f0-e80a-4257-965a-f7b7e3f410dd.mp4",
            "store/uploads/de6dc9f0-e80a-4257-965a-f7b7e3f410dd.mp4",
            "../../store/uploads/de6dc9f0-e80a-4257-965a-f7b7e3f410dd.mp4"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.test_video_path = os.path.abspath(path)
                break
                
        self.test_output_path = os.path.join(self.test_dir, "test_output.mp4")
        
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    def test_quality_analysis_identical_files(self):
        """Test quality analysis with identical files (should show perfect quality)."""
        if not self.test_video_path:
            self.skipTest("No test video file available")
            
        # Analyze same file against itself
        result = ffmpeg_utils.analyze_quality_loss(self.test_video_path, self.test_video_path)
        
        self.assertTrue(result["success"], f"Quality analysis failed: {result.get('error')}")
        
        # SSIM should be perfect (1.0) for identical files
        self.assertEqual(result["ssim"], 1.0, "SSIM should be 1.0 for identical files")
        
        # File size ratio should be 1.0
        self.assertEqual(result["file_size_ratio"], 1.0, "File size ratio should be 1.0 for identical files")
        
        # Processing should complete in reasonable time
        self.assertLess(result["processing_time"], 60, "Quality analysis took too long")
        
        # Quality assessment should recognize excellent quality
        assessment = result.get("quality_assessment", {})
        self.assertEqual(assessment.get("ssim_grade"), "excellent", "SSIM grade should be excellent")
        
    def test_quality_analysis_with_processed_video(self):
        """Test quality analysis with a processed video clip."""
        if not self.test_video_path:
            self.skipTest("No test video file available")
            
        # Create a processed version by extracting a clip
        success = ffmpeg_utils.extract_clip(self.test_video_path, 0.0, 1.0, self.test_output_path)
        
        if not success:
            self.skipTest("Could not create test processed video")
            
        # Analyze quality between original and processed
        result = ffmpeg_utils.analyze_quality_loss(self.test_video_path, self.test_output_path)
        
        self.assertTrue(result["success"], f"Quality analysis failed: {result.get('error')}")
        
        # SSIM should be high (>0.9) for good quality
        self.assertGreater(result["ssim"], 0.9, "SSIM should be high for good quality processing")
        
        # Should have quality assessment
        self.assertIn("quality_assessment", result)
        assessment = result["quality_assessment"]
        self.assertIn("overall", assessment)
        
    def test_quality_metrics_error_handling(self):
        """Test error handling for invalid files."""
        # Test with non-existent files
        result = ffmpeg_utils.analyze_quality_loss("nonexistent1.mp4", "nonexistent2.mp4")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("not found", result["error"])
        
    def test_quality_assessment_grading(self):
        """Test quality assessment grading system."""
        # Test excellent quality metrics
        excellent_metrics = {"ssim": 0.99, "psnr": 50.0}
        assessment = ffmpeg_utils._assess_quality(excellent_metrics)
        
        self.assertEqual(assessment["ssim_grade"], "excellent")
        self.assertEqual(assessment["psnr_grade"], "excellent") 
        self.assertEqual(assessment["overall"], "lossless_quality")
        
        # Test poor quality metrics
        poor_metrics = {"ssim": 0.85, "psnr": 20.0}
        assessment = ffmpeg_utils._assess_quality(poor_metrics)
        
        self.assertEqual(assessment["ssim_grade"], "poor")
        self.assertEqual(assessment["psnr_grade"], "poor")
        self.assertEqual(assessment["overall"], "lossy")
        
    def test_quality_report_generation(self):
        """Test comprehensive quality report generation."""
        if not self.test_video_path:
            self.skipTest("No test video file available")
            
        # Create a simple processing chain
        processing_chain = [
            {
                "original": self.test_video_path,
                "processed": self.test_video_path,  # Same file for testing
                "operation": "identity_test"
            }
        ]
        
        report = ffmpeg_utils.generate_quality_report(processing_chain)
        
        self.assertTrue(report["success"], f"Report generation failed: {report.get('error')}")
        self.assertEqual(report["processing_steps"], 1)
        self.assertIn("step_analysis", report)
        self.assertIn("summary", report)
        self.assertIn("recommendations", report)
        
        # Summary should show lossless step
        summary = report["summary"]
        self.assertEqual(summary["lossless_steps"], 1)
        self.assertEqual(summary["lossy_steps"], 0)
        

class TestQualityEndpoints(unittest.TestCase):
    """Test quality metrics API endpoints."""
    
    def test_ffmpeg_filter_availability(self):
        """Test that required FFmpeg filters are available."""
        # This would normally test against a running server
        # For now, just test the filter detection logic
        
        # Test that we can check for filter availability
        import subprocess
        try:
            result = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, "FFmpeg should be available")
            
            # Check for required filters
            filters = result.stdout
            self.assertIn("ssim", filters, "SSIM filter should be available")
            self.assertIn("psnr", filters, "PSNR filter should be available")
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.skipTest(f"FFmpeg not available: {e}")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
