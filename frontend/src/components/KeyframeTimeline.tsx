import React, { useMemo } from 'react';

interface KeyframeTimelineProps {
  keyframes: number[];
  duration: number;
  currentTime: number;
  markedIn?: number | null;
  markedOut?: number | null;
  onSeek?: (time: number) => void;
  onSnapToKeyframe?: (time: number) => void;
  className?: string;
}

const KeyframeTimeline: React.FC<KeyframeTimelineProps> = ({
  keyframes,
  duration,
  currentTime,
  markedIn,
  markedOut,
  onSeek,
  onSnapToKeyframe,
  className = ''
}) => {
  const timelineWidth = 400; // Fixed width for consistent layout
  
  const keyframePositions = useMemo(() => {
    if (duration <= 0) return [];
    return keyframes.map(time => ({
      time,
      position: (time / duration) * timelineWidth
    }));
  }, [keyframes, duration, timelineWidth]);

  const currentPosition = duration > 0 ? (currentTime / duration) * timelineWidth : 0;
  const markedInPosition = markedIn !== null && markedIn !== undefined && duration > 0 
    ? (markedIn / duration) * timelineWidth : null;
  const markedOutPosition = markedOut !== null && markedOut !== undefined && duration > 0 
    ? (markedOut / duration) * timelineWidth : null;

  const handleTimelineClick = (event: React.MouseEvent) => {
    if (!onSeek || duration <= 0) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickTime = (clickX / timelineWidth) * duration;
    
    onSeek(Math.max(0, Math.min(duration, clickTime)));
  };

  const handleKeyframeClick = (keyframeTime: number, event: React.MouseEvent) => {
    event.stopPropagation();
    if (onSnapToKeyframe) {
      onSnapToKeyframe(keyframeTime);
    } else if (onSeek) {
      onSeek(keyframeTime);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`keyframe-timeline ${className}`} style={{
      width: `${timelineWidth}px`,
      margin: '0 auto'
    }}>
      {/* Timeline header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: '#6b7280',
        marginBottom: '4px'
      }}>
        <span>Keyframes: {keyframes.length}</span>
        <span>Duration: {formatTime(duration)}</span>
      </div>

      {/* Main timeline */}
      <div
        onClick={handleTimelineClick}
        style={{
          position: 'relative',
          width: '100%',
          height: '32px',
          backgroundColor: '#374151',
          borderRadius: '4px',
          cursor: 'pointer',
          border: '1px solid #4b5563'
        }}
      >
        {/* Selection range */}
        {markedInPosition !== null && markedOutPosition !== null && (
          <div style={{
            position: 'absolute',
            left: `${Math.min(markedInPosition, markedOutPosition)}px`,
            width: `${Math.abs(markedOutPosition - markedInPosition)}px`,
            height: '100%',
            backgroundColor: 'rgba(59, 130, 246, 0.3)',
            borderRadius: '4px'
          }} />
        )}

        {/* Keyframe indicators */}
        {keyframePositions.map(({ time, position }, index) => (
          <div
            key={index}
            onClick={(e) => handleKeyframeClick(time, e)}
            style={{
              position: 'absolute',
              left: `${position}px`,
              top: '2px',
              width: '2px',
              height: '28px',
              backgroundColor: '#10b981',
              cursor: 'pointer',
              borderRadius: '1px',
              transform: 'translateX(-1px)'
            }}
            title={`Keyframe at ${formatTime(time)}`}
          />
        ))}

        {/* IN marker */}
        {markedInPosition !== null && (
          <div style={{
            position: 'absolute',
            left: `${markedInPosition}px`,
            top: '0px',
            width: '3px',
            height: '100%',
            backgroundColor: '#22c55e',
            transform: 'translateX(-1.5px)',
            zIndex: 2
          }}>
            <div style={{
              position: 'absolute',
              top: '-6px',
              left: '-3px',
              width: '0',
              height: '0',
              borderLeft: '3px solid transparent',
              borderRight: '3px solid transparent',
              borderBottom: '6px solid #22c55e'
            }} />
          </div>
        )}

        {/* OUT marker */}
        {markedOutPosition !== null && (
          <div style={{
            position: 'absolute',
            left: `${markedOutPosition}px`,
            top: '0px',
            width: '3px',
            height: '100%',
            backgroundColor: '#ef4444',
            transform: 'translateX(-1.5px)',
            zIndex: 2
          }}>
            <div style={{
              position: 'absolute',
              bottom: '-6px',
              left: '-3px',
              width: '0',
              height: '0',
              borderLeft: '3px solid transparent',
              borderRight: '3px solid transparent',
              borderTop: '6px solid #ef4444'
            }} />
          </div>
        )}

        {/* Current time indicator */}
        <div style={{
          position: 'absolute',
          left: `${currentPosition}px`,
          top: '0px',
          width: '2px',
          height: '100%',
          backgroundColor: '#f59e0b',
          transform: 'translateX(-1px)',
          zIndex: 3
        }}>
          <div style={{
            position: 'absolute',
            top: '-8px',
            left: '-4px',
            width: '10px',
            height: '8px',
            backgroundColor: '#f59e0b',
            borderRadius: '2px'
          }} />
        </div>
      </div>

      {/* Current time display */}
      <div style={{
        textAlign: 'center',
        fontSize: '0.75rem',
        color: '#9ca3af',
        marginTop: '4px'
      }}>
        Current: {formatTime(currentTime)}
        {markedIn !== null && markedOut !== null && (
          <span> | Range: {formatTime(markedIn || 0)} → {formatTime(markedOut || 0)}</span>
        )}
      </div>

      {/* Snap to keyframe button */}
      {onSnapToKeyframe && keyframes.length > 0 && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          marginTop: '8px'
        }}>
          <button
            onClick={() => {
              // Find nearest keyframe to current time
              const nearest = keyframes.reduce((prev, curr) => 
                Math.abs(curr - currentTime) < Math.abs(prev - currentTime) ? curr : prev
              );
              onSnapToKeyframe(nearest);
            }}
            style={{
              padding: '4px 8px',
              fontSize: '0.75rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            📍 Snap to Keyframe
          </button>
        </div>
      )}
    </div>
  );
};

export default KeyframeTimeline;
