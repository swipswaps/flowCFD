import React, { useState, useEffect } from 'react';
import AudioWaveform from './AudioWaveform';

export const AudioWaveformDemo: React.FC = () => {
  const [videos, setVideos] = useState<any[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string>('');
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Fetch available videos
  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const response = await fetch('/api/videos');
        const data = await response.json();
        setVideos(data);
        if (data.length > 0) {
          setSelectedVideoId(data[0].id);
        }
      } catch (error) {
        console.error('Error fetching videos:', error);
      }
    };

    fetchVideos();
  }, []);

  // Simulate playback progress
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTime(prev => {
        const selectedVideo = videos.find(v => v.id === selectedVideoId);
        const duration = selectedVideo?.duration || 10;
        
        if (prev >= duration) {
          setIsPlaying(false);
          return 0;
        }
        return prev + 0.1;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, selectedVideoId, videos]);

  const selectedVideo = videos.find(v => v.id === selectedVideoId);
  const duration = selectedVideo?.duration || 0;

  const handleTimeClick = (time: number) => {
    setCurrentTime(time);
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
    if (currentTime >= duration) {
      setCurrentTime(0);
    }
  };

  const resetTime = () => {
    setCurrentTime(0);
    setIsPlaying(false);
  };

  if (videos.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Loading videos...</p>
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '2rem', 
      backgroundColor: '#f9fafb',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
    }}>
      <h3 style={{ 
        margin: '0 0 1.5rem 0', 
        color: '#374151',
        fontSize: '1.5rem',
        fontWeight: '600'
      }}>
        🎵 Audio Waveform Visualization
      </h3>
      
      {/* Video Selection */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ 
          display: 'block', 
          marginBottom: '0.5rem',
          fontWeight: '500',
          color: '#374151'
        }}>
          Select Video:
        </label>
        <select
          value={selectedVideoId}
          onChange={(e) => {
            setSelectedVideoId(e.target.value);
            setCurrentTime(0);
            setIsPlaying(false);
          }}
          style={{
            padding: '0.5rem',
            borderRadius: '4px',
            border: '1px solid #444',
            backgroundColor: '#2a2a2a',
            color: '#eee',
            minWidth: '300px'
          }}
        >
          {videos.map((video) => (
            <option key={video.id} value={video.id}>
              {video.filename} ({video.duration?.toFixed(1)}s)
            </option>
          ))}
        </select>
      </div>

      {/* Playback Controls */}
      <div style={{ 
        marginBottom: '1.5rem',
        display: 'flex',
        gap: '1rem',
        alignItems: 'center'
      }}>
        <button
          onClick={togglePlayback}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: isPlaying ? '#ef4444' : '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          {isPlaying ? '⏸️ Pause' : '▶️ Play'}
        </button>
        
        <button
          onClick={resetTime}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          ⏹️ Stop
        </button>
        
        <span style={{ color: '#374151' }}>
          {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
        </span>
      </div>

      {/* Waveform Visualization */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ 
          margin: '0 0 1rem 0',
          color: '#374151',
          fontSize: '1.1rem',
          fontWeight: '500'
        }}>
          Standard Waveform (Blue):
        </h4>
        <AudioWaveform
          videoId={selectedVideoId}
          currentTime={currentTime}
          duration={duration}
          height={80}
          width={800}
          color="#3b82f6"
          progressColor="#ef4444"
          backgroundColor="#f3f4f6"
          onTimeClick={handleTimeClick}
          samples={400}
        />
      </div>

      {/* High-Detail Waveform */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ 
          margin: '0 0 1rem 0',
          color: '#374151',
          fontSize: '1.1rem',
          fontWeight: '500'
        }}>
          High-Detail Waveform (Green):
        </h4>
        <AudioWaveform
          videoId={selectedVideoId}
          currentTime={currentTime}
          duration={duration}
          height={60}
          width={800}
          color="#10b981"
          progressColor="#f59e0b"
          backgroundColor="#ecfdf5"
          onTimeClick={handleTimeClick}
          samples={1000}
        />
      </div>

      {/* Compact Waveform */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ 
          margin: '0 0 1rem 0',
          color: '#374151',
          fontSize: '1.1rem',
          fontWeight: '500'
        }}>
          Compact Waveform (Purple):
        </h4>
        <AudioWaveform
          videoId={selectedVideoId}
          currentTime={currentTime}
          duration={duration}
          height={40}
          width={800}
          color="#8b5cf6"
          progressColor="#ec4899"
          backgroundColor="#faf5ff"
          onTimeClick={handleTimeClick}
          samples={200}
        />
      </div>

      {/* Usage Information */}
      <div style={{
        marginTop: '2rem',
        padding: '1rem',
        backgroundColor: '#e0f2fe',
        borderRadius: '4px',
        border: '1px solid #0284c7'
      }}>
        <h4 style={{ 
          margin: '0 0 0.5rem 0',
          color: '#0c4a6e',
          fontSize: '1rem',
          fontWeight: '500'
        }}>
          🎯 How to Use Audio Waveforms:
        </h4>
        <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#0c4a6e' }}>
          <li><strong>Click</strong> on any waveform to jump to that time position</li>
          <li><strong>Play/Pause</strong> to see the progress indicator move</li>
          <li><strong>Different sample rates</strong> show varying levels of detail</li>
          <li><strong>Synthetic waveforms</strong> are generated for videos without audio</li>
          <li><strong>Color customization</strong> allows for track-specific styling</li>
        </ul>
      </div>
    </div>
  );
};

export default AudioWaveformDemo;
