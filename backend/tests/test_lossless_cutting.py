"""
Unit tests for lossless video editing functions.
Following .cursorrules compliance protocol.
"""
import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ffmpeg_utils import (
    get_keyframes, 
    validate_lossless_compatibility, 
    find_nearest_keyframe,
    extract_clip_lossless,
    _extract_with_stream_copy,
    _extract_with_quality_encoding
)


class TestLosslessCutting(unittest.TestCase):
    """Test suite for lossless video editing functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
        self.test_output_path = os.path.join(self.temp_dir, "test_output.mp4")
        # Create a dummy file for testing
        with open(self.test_video_path, 'w') as f:
            f.write("dummy video content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_keyframe_detection_accuracy(self):
        """Verify keyframe detection matches FFprobe output exactly."""
        mock_output = "0.000000\n2.002000\n4.004000\n6.006000\n"
        
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_run.return_value = mock_result
            
            keyframes = get_keyframes(self.test_video_path)
            
            expected_keyframes = [0.0, 2.002, 4.004, 6.006]
            self.assertEqual(keyframes, expected_keyframes)
            
            # Verify correct FFprobe command was called
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("ffprobe", args)
            self.assertIn("-skip_frame", args)
            self.assertIn("nokey", args)
    
    def test_keyframe_detection_error_handling(self):
        """Test keyframe detection handles errors gracefully."""
        # Test non-existent file
        keyframes = get_keyframes("/nonexistent/file.mp4")
        self.assertEqual(keyframes, [])
        
        # Test FFprobe failure - should fall back to synthetic keyframes
        with patch('subprocess.run') as mock_run, \
             patch('ffmpeg_utils.ffprobe_duration') as mock_duration:
            
            # Mock all subprocess calls to fail
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error message"
            mock_result.stdout = ""
            mock_run.return_value = mock_result
            
            # Mock duration for synthetic keyframes
            mock_duration.return_value = 5.0
            
            keyframes = get_keyframes(self.test_video_path)
            # Should get synthetic keyframes: [0.0, 2.0, 4.0]
            self.assertEqual(len(keyframes), 3)
            self.assertEqual(keyframes[0], 0.0)
            self.assertEqual(keyframes[1], 2.0)
            self.assertEqual(keyframes[2], 4.0)

    def test_lossless_extraction_basic(self):
        """Test basic lossless extraction functionality."""
        # Test with keyframe detection disabled (current state)
        result = extract_clip_lossless(
            src=self.test_video_path,
            start=1.0,
            end=3.0,
            out_path=self.test_output_path,
            force_keyframe=False,
            smart_cut=False
        )
        
        # Should succeed with basic extraction method
        self.assertTrue(result["success"])
        self.assertIn(result["method_used"], ["re_encoded", "fallback_encoded"])
        self.assertFalse(result["quality_preserved"])
        self.assertFalse(result["keyframe_aligned"])
        self.assertGreater(result["processing_time"], 0)
        self.assertGreater(result["file_size"], 0)
        
        # Verify output file exists
        self.assertTrue(os.path.exists(self.test_output_path))

    def test_lossless_extraction_with_keyframes(self):
        """Test lossless extraction with keyframe alignment."""
        # Mock keyframes for testing
        with patch('ffmpeg_utils.get_keyframes') as mock_keyframes:
            mock_keyframes.return_value = [0.0, 2.0, 4.0, 6.0]
            
            result = extract_clip_lossless(
                src=self.test_video_path,
                start=2.0,  # Aligned with keyframe
                end=4.0,    # Aligned with keyframe
                out_path=self.test_output_path,
                force_keyframe=True,
                smart_cut=False
            )
            
            # Should use stream copy for keyframe-aligned cuts
            self.assertTrue(result["success"])
            self.assertEqual(result["method_used"], "stream_copy")
            self.assertTrue(result["quality_preserved"])
            self.assertTrue(result["keyframe_aligned"])

    def test_find_nearest_keyframe(self):
        """Test keyframe finding algorithm."""
        keyframes = [0.0, 2.0, 4.0, 6.0, 8.0]
        
        # Test prefer_before=True
        self.assertEqual(find_nearest_keyframe(1.5, keyframes, prefer_before=True), 0.0)
        self.assertEqual(find_nearest_keyframe(2.0, keyframes, prefer_before=True), 2.0)
        self.assertEqual(find_nearest_keyframe(3.0, keyframes, prefer_before=True), 2.0)
        
        # Test prefer_before=False
        self.assertEqual(find_nearest_keyframe(1.5, keyframes, prefer_before=False), 2.0)
        self.assertEqual(find_nearest_keyframe(3.0, keyframes, prefer_before=False), 4.0)
        self.assertEqual(find_nearest_keyframe(9.0, keyframes, prefer_before=False), 8.0)
        
        # Test empty keyframes
        self.assertIsNone(find_nearest_keyframe(1.0, [], prefer_before=True))

    def test_stream_copy_extraction(self):
        """Test stream copy extraction method."""
        success = _extract_with_stream_copy(
            src=self.test_video_path,
            start=1.0,
            duration=2.0,
            out_path=self.test_output_path
        )
        
        # Should succeed for most videos
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.test_output_path))
        
        # Verify file is not empty
        self.assertGreater(os.path.getsize(self.test_output_path), 0)

    def test_quality_encoding_extraction(self):
        """Test high-quality encoding extraction method."""
        success = _extract_with_quality_encoding(
            src=self.test_video_path,
            start=1.0,
            duration=2.0,
            out_path=self.test_output_path
        )
        
        # Should succeed with re-encoding
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.test_output_path))
        self.assertGreater(os.path.getsize(self.test_output_path), 0)

    def test_smart_cut_functionality(self):
        """Test smart cut implementation for non-keyframe cuts."""
        # Mock keyframes for testing
        keyframes = [0.0, 2.0, 4.0, 6.0, 8.0]
        
        # Test smart cut with non-aligned timestamps
        with patch('ffmpeg_utils._extract_with_smart_cut') as mock_smart_cut:
            mock_smart_cut.return_value = True
            
            result = extract_clip_lossless(
                src=self.test_video_path,
                start=1.5,  # Not aligned with keyframe
                end=3.5,    # Not aligned with keyframe
                out_path=self.test_output_path,
                force_keyframe=False,
                smart_cut=True
            )
            
            # Should attempt smart cut for non-aligned cuts
            mock_smart_cut.assert_called_once()
            
    def test_smart_cut_precision(self):
        """Test smart cut precision and timing calculations."""
        keyframes = [0.0, 2.0, 4.0, 6.0, 8.0]
        
        # Test timing calculations
        start = 1.5
        end = 3.5
        
        pre_keyframe = find_nearest_keyframe(start, keyframes, prefer_before=True)
        post_keyframe = find_nearest_keyframe(end, keyframes, prefer_before=False)
        
        self.assertEqual(pre_keyframe, 0.0)  # Nearest before 1.5
        self.assertEqual(post_keyframe, 4.0)  # Nearest after 3.5
        
        # Calculate offsets as smart cut would
        pre_cut_offset = start - pre_keyframe
        post_cut_offset = end - pre_keyframe
        
        self.assertEqual(pre_cut_offset, 1.5)
        self.assertEqual(post_cut_offset, 3.5)
        self.assertGreater(post_cut_offset, pre_cut_offset)
    
    def test_lossless_compatibility_validation(self):
        """Test lossless compatibility validation."""
        mock_ffprobe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "has_b_frames": 0
                },
                {
                    "codec_type": "audio", 
                    "codec_name": "aac"
                }
            ],
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
            }
        }
        
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(mock_ffprobe_output).replace("'", '"')
            mock_run.return_value = mock_result
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = mock_ffprobe_output
                
                result = validate_lossless_compatibility(self.test_video_path)
                
                self.assertTrue(result["compatible"])
                self.assertEqual(result["video_codec"], "h264")
                self.assertEqual(result["audio_codec"], "aac")
                self.assertFalse(result["has_b_frames"])
    
    def test_find_nearest_keyframe_before(self):
        """Test finding nearest keyframe before timestamp."""
        keyframes = [0.0, 2.002, 4.004, 6.006, 8.008]
        
        # Test exact match
        result = find_nearest_keyframe(4.004, keyframes, prefer_before=True)
        self.assertEqual(result, 4.004)
        
        # Test between keyframes
        result = find_nearest_keyframe(3.5, keyframes, prefer_before=True)
        self.assertEqual(result, 2.002)
        
        # Test before first keyframe
        result = find_nearest_keyframe(-1.0, keyframes, prefer_before=True)
        self.assertEqual(result, 0.0)
    
    def test_find_nearest_keyframe_after(self):
        """Test finding nearest keyframe after timestamp."""
        keyframes = [0.0, 2.002, 4.004, 6.006, 8.008]
        
        # Test between keyframes
        result = find_nearest_keyframe(3.5, keyframes, prefer_before=False)
        self.assertEqual(result, 4.004)
        
        # Test after last keyframe
        result = find_nearest_keyframe(10.0, keyframes, prefer_before=False)
        self.assertEqual(result, 8.008)
    
    def test_find_nearest_keyframe_empty_list(self):
        """Test keyframe finding with empty keyframe list."""
        result = find_nearest_keyframe(5.0, [], prefer_before=True)
        self.assertEqual(result, 5.0)


if __name__ == '__main__':
    unittest.main()
