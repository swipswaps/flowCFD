import React, { useState, useCallback, useEffect, useRef } from 'react';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { 
  useTimelineSnapping, 
  PIXELS_PER_SECOND,
  SnapPoint,
  generateSnapIndicators 
} from '../utils/timelineSnapping';
import AudioWaveform from './AudioWaveform';

// Constants for timeline layout
const TRACK_HEIGHT = 80;
const TRACK_HEADER_WIDTH = 150;

interface TimelineClip {
  id: string;
  track_id: number;
  start_time: number;
  end_time: number;
  timeline_position: number;
  z_index: number;
  video: {
    id?: string;
    filename: string;
    duration?: number;
  };
}

interface Track {
  id: number;
  name: string;
  type: 'video' | 'audio' | 'overlay';
  order: number;
  enabled: boolean;
  locked: boolean;
  volume: number;
  opacity: number;
  clips: TimelineClip[];
}

interface DraggableClipProps {
  clip: TimelineClip;
  onMove: (clipId: string, newTrackId: number, newPosition: number) => void;
}

const DraggableClip: React.FC<DraggableClipProps> = ({ clip, onMove }) => {
  const [{ isDragging }, drag] = useDrag({
    type: 'clip',
    item: { 
      id: clip.id, 
      trackId: clip.track_id, 
      position: clip.timeline_position,
      duration: clip.end_time - clip.start_time
    },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const clipDuration = clip.end_time - clip.start_time;
  const clipWidth = Math.max(clipDuration * PIXELS_PER_SECOND, 60); // Minimum 60px width
  const clipLeft = clip.timeline_position * PIXELS_PER_SECOND;

  return (
    <div
      ref={drag}
      className={`timeline-clip ${isDragging ? 'dragging' : ''}`}
      style={{
        left: clipLeft,
        width: clipWidth,
        opacity: isDragging ? 0.5 : 1,
        position: 'absolute',
        height: '60px',
        backgroundColor: '#3b82f6',
        borderRadius: '4px',
        border: '2px solid #1e40af',
        cursor: 'move',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        color: 'white',
        fontSize: '12px',
        fontWeight: '500',
        boxShadow: isDragging ? '0 4px 8px rgba(0,0,0,0.3)' : '0 2px 4px rgba(0,0,0,0.1)',
        transition: isDragging ? 'none' : 'box-shadow 0.2s ease',
        zIndex: isDragging ? 1000 : clip.z_index,
        overflow: 'hidden',
      }}
      title={`${clip.video.filename} (${clipDuration.toFixed(2)}s)`}
    >
      <div style={{ 
        flex: 1, 
        overflow: 'hidden', 
        textOverflow: 'ellipsis', 
        whiteSpace: 'nowrap' 
      }}>
        {clip.video.filename}
      </div>
      <div style={{ 
        fontSize: '10px', 
        opacity: 0.8, 
        marginLeft: '4px' 
      }}>
        {clipDuration.toFixed(1)}s
      </div>
    </div>
  );
};

interface DroppableTrackProps {
  track: Track;
  onDrop: (clipId: string, trackId: number, position: number) => void;
  onToggleTrack: (trackId: number, property: 'enabled' | 'locked') => void;
}

const DroppableTrack: React.FC<DroppableTrackProps> = ({ track, onDrop, onToggleTrack }) => {
  const [{ isOver, canDrop }, drop] = useDrop({
    accept: 'clip',
    drop: (item: any, monitor) => {
      const dropOffset = monitor.getClientOffset();
      const targetElement = (drop as any).current;
      
      if (dropOffset && targetElement) {
        const rect = targetElement.getBoundingClientRect();
        const relativeX = dropOffset.x - rect.left - TRACK_HEADER_WIDTH;
        const newPosition = Math.max(0, relativeX / PIXELS_PER_SECOND);
        onDrop(item.id, track.id, newPosition);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  });

  const isActive = isOver && canDrop;

  return (
    <div
      ref={drop}
      className={`timeline-track ${isActive ? 'drop-target' : ''} ${track.locked ? 'locked' : ''}`}
      style={{
        position: 'relative',
        height: `${TRACK_HEIGHT}px`,
        backgroundColor: isActive ? '#f0f9ff' : track.enabled ? '#ffffff' : '#f9fafb',
        border: `1px solid ${isActive ? '#3b82f6' : '#e5e7eb'}`,
        borderLeft: `4px solid ${track.type === 'video' ? '#3b82f6' : track.type === 'audio' ? '#10b981' : '#f59e0b'}`,
        marginBottom: '2px',
        borderRadius: '4px',
        opacity: track.enabled ? 1 : 0.6,
        transition: 'all 0.2s ease',
      }}
    >
      {/* Track Header */}
      <div 
        className="track-header" 
        style={{
          position: 'absolute',
          left: 0,
          width: `${TRACK_HEADER_WIDTH}px`,
          height: '100%',
          backgroundColor: '#f9fafb',
          borderRight: '1px solid #e5e7eb',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 12px',
          fontSize: '14px',
          fontWeight: '500',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ 
            flex: 1, 
            overflow: 'hidden', 
            textOverflow: 'ellipsis',
            color: track.enabled ? '#374151' : '#9ca3af'
          }}>
            {track.name}
          </span>
          <div style={{ display: 'flex', gap: '2px' }}>
            <button 
              onClick={() => onToggleTrack(track.id, 'enabled')}
              style={{ 
                padding: '2px 4px', 
                fontSize: '10px', 
                border: 'none',
                borderRadius: '2px',
                backgroundColor: track.enabled ? '#10b981' : '#6b7280',
                color: 'white',
                cursor: 'pointer'
              }}
              title={track.enabled ? 'Disable track' : 'Enable track'}
            >
              {track.enabled ? '👁' : '🙈'}
            </button>
            <button 
              onClick={() => onToggleTrack(track.id, 'locked')}
              style={{ 
                padding: '2px 4px', 
                fontSize: '10px', 
                border: 'none',
                borderRadius: '2px',
                backgroundColor: track.locked ? '#ef4444' : '#6b7280',
                color: 'white',
                cursor: 'pointer'
              }}
              title={track.locked ? 'Unlock track' : 'Lock track'}
            >
              {track.locked ? '🔒' : '🔓'}
            </button>
          </div>
        </div>
        <div style={{ 
          fontSize: '10px', 
          color: '#6b7280', 
          marginTop: '2px',
          display: 'flex',
          justifyContent: 'space-between'
        }}>
          <span>{track.type}</span>
          <span>{track.clips.length} clips</span>
        </div>
      </div>
      
      {/* Track Timeline Area */}
      <div 
        className="track-timeline" 
        style={{
          marginLeft: `${TRACK_HEADER_WIDTH}px`,
          position: 'relative',
          height: '100%',
          minWidth: '800px',
          backgroundColor: isActive ? '#dbeafe' : 'transparent',
          borderRadius: '0 4px 4px 0',
        }}
      >
        {/* Drop indicator */}
        {isActive && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#3b82f6',
            fontSize: '14px',
            fontWeight: '600',
            pointerEvents: 'none',
          }}>
            Drop clip here
          </div>
        )}
        
        {/* Render audio waveform for audio tracks */}
        {track.type === 'audio' && track.clips.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            right: '10px',
            height: '40px',
            zIndex: 1
          }}>
            <AudioWaveform
              videoId={track.clips[0]?.video?.id || ''}
              height={40}
              width={800}
              color="#10b981"
              progressColor="#059669"
              backgroundColor="rgba(16, 185, 129, 0.1)"
              samples={200}
            />
          </div>
        )}
        
        {/* Render clips for this track */}
        {track.clips.map((clip) => (
          <DraggableClip
            key={clip.id}
            clip={clip}
            onMove={() => {}} // Handled by drop
          />
        ))}
      </div>
    </div>
  );
};

interface MultiTrackTimelineProps {
  className?: string;
}

export const MultiTrackTimeline: React.FC<MultiTrackTimelineProps> = ({ className }) => {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [playheadTime, setPlayheadTime] = useState(0);
  const [keyframes, setKeyframes] = useState<number[]>([]);
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [gridSnapEnabled, setGridSnapEnabled] = useState(false);
  const [activeSnapIndicators, setActiveSnapIndicators] = useState<SnapPoint[]>([]);
  const timelineRef = useRef<HTMLDivElement>(null);

  // Fetch tracks data
  const fetchTracks = useCallback(async () => {
    try {
      const response = await fetch('/api/tracks');
      const data = await response.json();
      setTracks(data.tracks || []);
    } catch (error) {
      console.error('Error fetching tracks:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTracks();
  }, [fetchTracks]);

  // Initialize snapping behavior
  const {
    snapClipPosition,
    snapToNearestPoint,
    getSnapIndicators
  } = useTimelineSnapping(
    tracks,
    playheadTime,
    keyframes,
    gridSnapEnabled ? 1.0 : undefined, // 1-second grid
    ['clip_start', 'clip_end', 'keyframe', 'playhead']
  );

  // Handle clip movement with snapping
  const handleClipMove = useCallback(async (clipId: string, newTrackId: number, rawPosition: number) => {
    try {
      // Find the clip being moved
      const movedClip = tracks
        .flatMap(t => t.clips)
        .find(c => c.id === clipId);
      
      if (!movedClip) return;

      // Calculate snapped position if snapping is enabled
      let finalPosition = rawPosition;
      let snapIndicators: SnapPoint[] = [];
      
      if (snapEnabled) {
        const snapResult = snapClipPosition(movedClip, rawPosition);
        finalPosition = snapResult.finalPosition;
        snapIndicators = snapResult.snapIndicators;
        
        // Update snap indicators for visual feedback
        setActiveSnapIndicators(snapIndicators);
        
        // Clear snap indicators after a short delay
        setTimeout(() => setActiveSnapIndicators([]), 1000);
      }

      // Optimistic update
      setTracks(prevTracks => {
        const updatedTracks = prevTracks.map(track => ({
          ...track,
          clips: track.clips.filter(clip => clip.id !== clipId)
        }));
        
        const targetTrack = updatedTracks.find(t => t.id === newTrackId);
        if (targetTrack) {
          targetTrack.clips.push({
            ...movedClip,
            track_id: newTrackId,
            timeline_position: finalPosition
          });
        }
        
        return updatedTracks;
      });

      // Sync with backend
      const response = await fetch('/api/clips/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clip_id: clipId,
          track_id: newTrackId,
          timeline_position: finalPosition
        })
      });

      if (!response.ok) {
        // Revert on error
        fetchTracks();
        throw new Error('Failed to move clip');
      }

      console.log(`Moved clip ${clipId} to track ${newTrackId} at position ${finalPosition}${snapEnabled ? ' (snapped)' : ''}`);
    } catch (error) {
      console.error('Error moving clip:', error);
      // Revert to server state on error
      fetchTracks();
    }
  }, [tracks, snapEnabled, snapClipPosition, fetchTracks]);

  // Handle track property toggles
  const handleToggleTrack = useCallback(async (trackId: number, property: 'enabled' | 'locked') => {
    try {
      const track = tracks.find(t => t.id === trackId);
      if (!track) return;

      const newValue = property === 'enabled' ? !track.enabled : !track.locked;
      const updateKey = property === 'enabled' ? 'is_enabled' : 'is_locked';

      // Optimistic update
      setTracks(prevTracks => 
        prevTracks.map(t => 
          t.id === trackId 
            ? { ...t, [property]: newValue }
            : t
        )
      );

      // Sync with backend
      const response = await fetch(`/api/tracks/${trackId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [updateKey]: newValue })
      });

      if (!response.ok) {
        fetchTracks(); // Revert on error
        throw new Error(`Failed to update track ${property}`);
      }

      console.log(`Updated track ${trackId} ${property} to ${newValue}`);
    } catch (error) {
      console.error('Error updating track:', error);
      fetchTracks();
    }
  }, [tracks, fetchTracks]);

  // Create new track
  const handleCreateTrack = useCallback(async (trackType: 'video' | 'audio') => {
    try {
      const response = await fetch('/api/tracks/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          track_name: `${trackType === 'video' ? 'Video' : 'Audio'} Track ${tracks.filter(t => t.type === trackType).length + 1}`,
          track_type: trackType
        })
      });

      if (response.ok) {
        fetchTracks(); // Refresh tracks
        console.log(`Created new ${trackType} track`);
      }
    } catch (error) {
      console.error('Error creating track:', error);
    }
  }, [tracks, fetchTracks]);

  if (isLoading) {
    return (
      <div style={{ 
        padding: '2rem', 
        textAlign: 'center', 
        color: '#6b7280' 
      }}>
        Loading timeline...
      </div>
    );
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className={`multi-track-timeline ${className || ''}`}>
        <div 
          className="timeline-header" 
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px',
            borderBottom: '1px solid #e5e7eb',
            backgroundColor: '#f9fafb',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#374151' }}>
            🎬 Multi-Track Timeline
          </h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {/* Snap Controls */}
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center', marginRight: '12px' }}>
              <button 
                onClick={() => setSnapEnabled(!snapEnabled)}
                style={{
                  padding: '4px 8px',
                  backgroundColor: snapEnabled ? '#10b981' : '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s ease'
                }}
                title={snapEnabled ? 'Disable snapping' : 'Enable snapping'}
              >
                🧲 {snapEnabled ? 'ON' : 'OFF'}
              </button>
              <button 
                onClick={() => setGridSnapEnabled(!gridSnapEnabled)}
                style={{
                  padding: '4px 8px',
                  backgroundColor: gridSnapEnabled ? '#3b82f6' : '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s ease'
                }}
                title={gridSnapEnabled ? 'Disable grid snap' : 'Enable grid snap'}
              >
                📏 {gridSnapEnabled ? 'ON' : 'OFF'}
              </button>
            </div>
            
            {/* Track Creation */}
            <button 
              onClick={() => handleCreateTrack('video')}
              style={{
                padding: '6px 12px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              ➕ Video Track
            </button>
            <button 
              onClick={() => handleCreateTrack('audio')}
              style={{
                padding: '6px 12px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              ➕ Audio Track
            </button>
          </div>
        </div>
        
        <div 
          ref={timelineRef}
          className="tracks-container" 
          style={{ 
            padding: '8px',
            backgroundColor: '#fafafa',
            minHeight: '400px',
            overflow: 'auto',
            position: 'relative'
          }}
        >
          {/* Snap Indicators */}
          {activeSnapIndicators.map((indicator, index) => {
            const pixelPosition = indicator.time * PIXELS_PER_SECOND + TRACK_HEADER_WIDTH;
            
            let color = '#6b7280';
            let opacity = 0.6;
            
            switch (indicator.type) {
              case 'clip_start':
              case 'clip_end':
                color = '#3b82f6';
                opacity = 0.8;
                break;
              case 'keyframe':
                color = '#10b981';
                opacity = 0.9;
                break;
              case 'playhead':
                color = '#ef4444';
                opacity = 0.9;
                break;
            }
            
            return (
              <div
                key={`snap-${index}`}
                style={{
                  position: 'absolute',
                  left: `${pixelPosition}px`,
                  top: 0,
                  width: '3px',
                  height: '100%',
                  backgroundColor: color,
                  opacity,
                  pointerEvents: 'none',
                  zIndex: 1000,
                  boxShadow: '0 0 4px rgba(0,0,0,0.3)',
                  transition: 'opacity 0.3s ease'
                }}
              />
            );
          })}
          
          {tracks.length === 0 ? (
            <div style={{ 
              textAlign: 'center', 
              padding: '3rem', 
              color: '#6b7280' 
            }}>
              No tracks found. Create a track to get started.
            </div>
          ) : (
            tracks.map((track) => (
              <DroppableTrack
                key={track.id}
                track={track}
                onDrop={handleClipMove}
                onToggleTrack={handleToggleTrack}
              />
            ))
          )}
        </div>
      </div>
    </DndProvider>
  );
};
