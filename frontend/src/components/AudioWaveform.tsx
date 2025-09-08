import React, { useEffect, useRef, useState, useCallback } from 'react';

interface AudioWaveformProps {
  videoId?: string;
  audioUrl?: string;
  currentTime?: number;
  duration?: number;
  height?: number;
  width?: number;
  color?: string;
  progressColor?: string;
  backgroundColor?: string;
  onTimeClick?: (time: number) => void;
  samples?: number;
  className?: string;
}

interface WaveformData {
  success: boolean;
  waveform: number[];
  samples: number;
  duration: number;
  sample_rate: number;
  channels: number;
  synthetic?: boolean;
  note?: string;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({
  videoId,
  audioUrl,
  currentTime = 0,
  duration = 0,
  height = 60,
  width = 800,
  color = '#3b82f6',
  progressColor = '#ef4444',
  backgroundColor = '#f3f4f6',
  onTimeClick,
  samples = 1000,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [waveformData, setWaveformData] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actualDuration, setActualDuration] = useState(duration);
  const [isSynthetic, setIsSynthetic] = useState(false);

  // Fetch waveform data from API
  const fetchWaveformData = useCallback(async () => {
    if (!videoId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/videos/${videoId}/waveform?samples=${samples}`);
      const data: WaveformData = await response.json();
      
      if (data.success) {
        setWaveformData(data.waveform);
        setActualDuration(data.duration);
        setIsSynthetic(data.synthetic || false);
        
        if (data.synthetic && data.note) {
          console.log(`Waveform note: ${data.note}`);
        }
      } else {
        setError('Failed to load waveform data');
      }
    } catch (err) {
      setError('Error fetching waveform data');
      console.error('Waveform fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [videoId, samples]);

  // Generate waveform from audio URL (Web Audio API approach)
  const generateWaveformFromAudio = useCallback(async () => {
    if (!audioUrl) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      const channelData = audioBuffer.getChannelData(0);
      const blockSize = Math.floor(channelData.length / samples);
      const waveform = [];
      
      for (let i = 0; i < samples; i++) {
        let sum = 0;
        for (let j = 0; j < blockSize; j++) {
          sum += Math.abs(channelData[i * blockSize + j]);
        }
        waveform.push(sum / blockSize);
      }
      
      setWaveformData(waveform);
      setActualDuration(audioBuffer.duration);
      setIsSynthetic(false);
    } catch (err) {
      setError('Error processing audio file');
      console.error('Audio processing error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [audioUrl, samples]);

  // Load waveform data
  useEffect(() => {
    if (videoId) {
      fetchWaveformData();
    } else if (audioUrl) {
      generateWaveformFromAudio();
    }
  }, [videoId, audioUrl, fetchWaveformData, generateWaveformFromAudio]);

  // Draw waveform on canvas
  useEffect(() => {
    if (!canvasRef.current || waveformData.length === 0) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas dimensions
    canvas.width = width;
    canvas.height = height;

    const centerY = height / 2;
    const progress = actualDuration > 0 ? currentTime / actualDuration : 0;
    const progressX = width * progress;

    // Clear canvas
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, width, height);

    // Draw waveform bars
    const barWidth = width / waveformData.length;
    
    waveformData.forEach((amplitude, index) => {
      const x = index * barWidth;
      const barHeight = amplitude * centerY * 0.9; // 90% of max height
      
      // Choose color based on progress
      ctx.fillStyle = x < progressX ? progressColor : color;
      
      // Draw symmetric bars (top and bottom)
      ctx.fillRect(x, centerY - barHeight, Math.max(barWidth - 1, 1), barHeight);
      ctx.fillRect(x, centerY, Math.max(barWidth - 1, 1), barHeight);
    });

    // Draw progress line
    if (progressX > 0) {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.shadowColor = 'rgba(0,0,0,0.5)';
      ctx.shadowBlur = 2;
      ctx.beginPath();
      ctx.moveTo(progressX, 0);
      ctx.lineTo(progressX, height);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
    
    // Draw synthetic indicator
    if (isSynthetic) {
      ctx.fillStyle = 'rgba(0,0,0,0.7)';
      ctx.font = '12px Arial';
      ctx.fillText('Synthetic Audio', 10, height - 10);
    }
    
  }, [waveformData, currentTime, actualDuration, height, width, color, progressColor, backgroundColor, isSynthetic]);

  // Handle canvas click
  const handleCanvasClick = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onTimeClick || !canvasRef.current || actualDuration <= 0) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const clickProgress = x / width;
    const clickTime = clickProgress * actualDuration;
    
    onTimeClick(Math.max(0, Math.min(clickTime, actualDuration)));
  }, [onTimeClick, width, actualDuration]);

  if (error) {
    return (
      <div 
        className={`audio-waveform-error ${className}`}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          backgroundColor: '#fee2e2',
          border: '1px solid #fecaca',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#dc2626',
          fontSize: '14px'
        }}
      >
        {error}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div 
        className={`audio-waveform-loading ${className}`}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          backgroundColor: '#f3f4f6',
          border: '1px solid #e5e7eb',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#6b7280',
          fontSize: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div 
            style={{
              width: '16px',
              height: '16px',
              border: '2px solid #e5e7eb',
              borderTop: '2px solid #3b82f6',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}
          />
          Generating waveform...
        </div>
      </div>
    );
  }

  return (
    <div className={`audio-waveform ${className}`}>
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          border: '1px solid #e5e7eb',
          borderRadius: '4px',
          cursor: onTimeClick ? 'pointer' : 'default',
          display: 'block'
        }}
      />
      
      {/* Waveform info */}
      <div style={{
        fontSize: '12px',
        color: '#6b7280',
        marginTop: '4px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span>
          {waveformData.length} samples • {actualDuration.toFixed(2)}s
          {isSynthetic && ' • Synthetic'}
        </span>
        <span>
          {currentTime.toFixed(2)}s / {actualDuration.toFixed(2)}s
        </span>
      </div>
      
      {/* Add CSS animation */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default AudioWaveform;
