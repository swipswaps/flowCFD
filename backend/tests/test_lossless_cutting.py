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

from ffmpeg_utils import get_keyframes, validate_lossless_compatibility, find_nearest_keyframe


class TestLosslessCutting(unittest.TestCase):
    """Test suite for lossless video editing functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
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
