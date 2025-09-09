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
  onRemove?: (clipId: string) => void;
  onTrim?: (clipId: string, newStart: number, newEnd: number) => void;
}

const DraggableClip: React.FC<DraggableClipProps> = ({ clip, onMove, onRemove, onTrim }) => {
  const [{ isDragging }, drag] = useDrag({
    type: 'clip',
    item: () => {
      console.log(`🚀 DRAG BEGIN: Starting drag for clip ${clip.id}`);
      return { 
        id: clip.id, 
        trackId: clip.track_id, 
        position: clip.timeline_position,
        duration: clip.end_time - clip.start_time
      };
    },
    end: (item, monitor) => {
      console.log(`🏁 DRAG END: Finished drag for clip ${clip.id}, dropped: ${monitor.didDrop()}`);
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
      onClick={() => console.log(`🖱️ CLICK: Clip ${clip.id} clicked`)}
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
        whiteSpace: 'nowrap',
        pointerEvents: 'none'  // Don't block drag events
      }}>
        {clip.video.filename}
      </div>
      <div style={{ 
        fontSize: '10px', 
        opacity: 0.8, 
        marginLeft: '4px',
        pointerEvents: 'none'  // Don't block drag events
      }}>
        {clipDuration.toFixed(1)}s
      </div>
      
      {/* Clip Controls */}
      <div style={{
        position: 'absolute',
        top: '2px',
        right: '2px',
        display: 'flex',
        gap: '2px',
        opacity: 0.9,
        pointerEvents: 'auto'  // Buttons should be clickable
      }}>
        {onTrim && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              const newEnd = Math.max(clip.start_time + 0.5, clip.end_time - 0.5);
              onTrim(clip.id, clip.start_time, newEnd);
            }}
            style={{
              width: '16px',
              height: '16px',
              border: 'none',
              borderRadius: '2px',
              backgroundColor: '#f59e0b',
              color: 'white',
              cursor: 'pointer',
              fontSize: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Trim clip"
          >
            ✂️
          </button>
        )}
        {onRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove(clip.id);
            }}
            style={{
              width: '16px',
              height: '16px',
              border: 'none',
              borderRadius: '2px',
              backgroundColor: '#ef4444',
              color: 'white',
              cursor: 'pointer',
              fontSize: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Remove clip"
          >
            ❌
          </button>
        )}
      </div>
    </div>
  );
};

interface DroppableTrackProps {
  track: Track;
  onDrop: (clipId: string, trackId: number, position: number) => void;
  onToggleTrack: (trackId: number, property: 'enabled' | 'locked') => void;
  onRemoveClip: (clipId: string) => void;
  onTrimClip: (clipId: string, newStart: number, newEnd: number) => void;
}

const DroppableTrack: React.FC<DroppableTrackProps> = ({ track, onDrop, onToggleTrack, onRemoveClip, onTrimClip }) => {
  const dropRef = useRef<HTMLDivElement>(null);
  const [{ isOver, canDrop }, drop] = useDrop({
    accept: 'clip',
    drop: (item: any, monitor) => {
      console.log(`📍 DROP: Received drop on track ${track.id} with item`, item);
      const dropOffset = monitor.getClientOffset();
      
      if (dropOffset) {
        // Use the dropRef to get the target element
        const targetElement = dropRef.current;
        if (targetElement) {
          const rect = targetElement.getBoundingClientRect();
          const relativeX = dropOffset.x - rect.left - TRACK_HEADER_WIDTH;
          const newPosition = Math.max(0, relativeX / PIXELS_PER_SECOND);
          console.log(`📍 DROP: Calculated position ${newPosition} for track ${track.id} at x=${dropOffset.x}`);
          onDrop(item.id, track.id, newPosition);
        } else {
          console.log(`❌ DROP: No target element ref`);
        }
      } else {
        console.log(`❌ DROP: No drop offset from monitor`);
      }
    },
    hover: (item: any, monitor) => {
      if (!monitor.isOver({ shallow: true })) return;
      
      const hoverOffset = monitor.getClientOffset();
      if (hoverOffset && dropRef.current) {
        const rect = dropRef.current.getBoundingClientRect();
        const relativeX = hoverOffset.x - rect.left - TRACK_HEADER_WIDTH;
        const hoverPosition = Math.max(0, relativeX / PIXELS_PER_SECOND);
        
        // Show real-time position feedback during hover
        console.log(`🔍 HOVER: Over track ${track.id} at position ${hoverPosition.toFixed(2)}s`);
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
      ref={(el) => {
        drop(el);
        if (dropRef.current !== el) {
          (dropRef as any).current = el;
        }
      }}
      className={`timeline-track ${isActive ? 'drop-target' : ''} ${track.locked ? 'locked' : ''}`}
      style={{
        position: 'relative',
        height: `${TRACK_HEIGHT}px`,
        backgroundColor: isActive ? '#f0f9ff' : track.enabled ? '#ffffff' : '#f9fafb',
        borderTop: `1px solid ${isActive ? '#3b82f6' : '#e5e7eb'}`,
        borderRight: `1px solid ${isActive ? '#3b82f6' : '#e5e7eb'}`,
        borderBottom: `1px solid ${isActive ? '#3b82f6' : '#e5e7eb'}`,
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
            zIndex: 0,  // Below clips
            pointerEvents: 'none'  // Don't interfere with clip interactions
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
            onRemove={onRemoveClip}
            onTrim={onTrimClip}
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
    console.log(`🎬 DRAG: Moving clip ${clipId} to track ${newTrackId} at position ${rawPosition}`);
    try {
      // Find the clip being moved
      const movedClip = tracks
        .flatMap(t => t.clips)
        .find(c => c.id === clipId);
      
      if (!movedClip) {
        console.error(`❌ DRAG: Clip ${clipId} not found in tracks`);
        return;
      }

      // Calculate snapped position with enhanced magnetic behavior
      let finalPosition = rawPosition;
      let snapIndicators: SnapPoint[] = [];
      
      if (snapEnabled) {
        const snapResult = snapClipPosition(movedClip, rawPosition);
        finalPosition = snapResult.finalPosition;
        snapIndicators = snapResult.snapIndicators;
        
        // Enhanced snapping feedback
        const didSnap = snapResult.startSnap.snapped || snapResult.endSnap.snapped;
        if (didSnap) {
          console.log(`🧲 SNAP: Clip ${clipId} snapped from ${rawPosition.toFixed(2)}s to ${finalPosition.toFixed(2)}s`);
        }
        
        // Update snap indicators for visual feedback
        setActiveSnapIndicators(snapIndicators);
        
        // Clear snap indicators after a short delay
        setTimeout(() => setActiveSnapIndicators([]), 1500);
      }
      
      // Ensure no negative positions
      finalPosition = Math.max(0, finalPosition);
      
      // Round to frame boundaries for smoother editing (assuming 30fps)
      const frameTime = 1/30;
      finalPosition = Math.round(finalPosition / frameTime) * frameTime;

      // Collision detection with proper adjacent clip support
      const targetTrack = tracks.find(t => t.id === newTrackId);
      if (targetTrack) {
        const clipDuration = movedClip.end_time - movedClip.start_time;
        const clipEndPosition = finalPosition + clipDuration;
        
        // Check for actual overlaps (not just adjacency) with other clips on the target track
        const otherClips = targetTrack.clips.filter(c => c.id !== clipId);
        
        // Define a small tolerance for adjacency detection (clips can touch)
        const ADJACENCY_TOLERANCE = 0.01; // 10ms tolerance
        
        for (const otherClip of otherClips) {
          const otherStart = otherClip.timeline_position;
          const otherEnd = otherClip.timeline_position + (otherClip.end_time - otherClip.start_time);
          
          // Check for TRUE overlaps (not adjacency)
          // Allow clips to be adjacent (touching) by using tolerance
          const wouldOverlapStart = finalPosition < (otherEnd - ADJACENCY_TOLERANCE);
          const wouldOverlapEnd = clipEndPosition > (otherStart + ADJACENCY_TOLERANCE);
          
          if (wouldOverlapStart && wouldOverlapEnd) {
            // True collision detected - slide to avoid overlap
            // Check if we're trying to snap to this clip's edges (adjacent placement)
            const isClipStartSnappingToOtherEnd = Math.abs(finalPosition - otherEnd) < 0.1;
            const isClipEndSnappingToOtherStart = Math.abs(clipEndPosition - otherStart) < 0.1;
            
            // Only allow snapping if it results in ADJACENT (not overlapping) placement
            const wouldBeAdjacent = isClipStartSnappingToOtherEnd || isClipEndSnappingToOtherStart;
            
            if (wouldBeAdjacent) {
              console.log(`🧲 ALLOW SNAP: Clip ${clipId} snapping to adjacent position at ${finalPosition.toFixed(2)}s`);
              continue; // Don't treat adjacent snapping as collision
            }
            
            // Otherwise, handle true collision by sliding
            if (finalPosition < otherStart) {
              // Moving clip starts before other clip - snap to just before it
              finalPosition = Math.max(0, otherStart - clipDuration);
              console.log(`🔄 SLIDE: Clip ${clipId} slid to ${finalPosition.toFixed(2)}s to avoid collision`);
            } else {
              // Moving clip starts after other clip start - snap to just after it
              finalPosition = otherEnd;
              console.log(`🔄 SLIDE: Clip ${clipId} slid to ${finalPosition.toFixed(2)}s to avoid collision`);
            }
            break; // Only handle one collision at a time
          }
        }
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
      console.log(`🌐 API: Sending move request for clip ${clipId} to track ${newTrackId} at ${finalPosition}`);
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
        console.error(`❌ API: Move failed with status ${response.status}`);
        fetchTracks();
        throw new Error('Failed to move clip');
      }
      
      const result = await response.json();
      console.log(`✅ API: Move successful`, result);

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

  // Handle clip removal
  const handleRemoveClip = useCallback(async (clipId: string) => {
    try {
      const response = await fetch(`/api/clips/${clipId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to remove clip');
      }
      
      // Update local state
      setTracks(prevTracks => 
        prevTracks.map(track => ({
          ...track,
          clips: track.clips.filter(clip => clip.id !== clipId)
        }))
      );
      
      console.log(`Removed clip ${clipId}`);
    } catch (error) {
      console.error('Error removing clip:', error);
    }
  }, []);

  // Handle clip trimming
  const handleTrimClip = useCallback(async (clipId: string, newStart: number, newEnd: number) => {
    try {
      const response = await fetch(`/api/clips/${clipId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_time: newStart,
          end_time: newEnd
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to trim clip');
      }
      
      // Update local state
      setTracks(prevTracks => 
        prevTracks.map(track => ({
          ...track,
          clips: track.clips.map(clip => 
            clip.id === clipId 
              ? { ...clip, start_time: newStart, end_time: newEnd }
              : clip
          )
        }))
      );
      
      console.log(`Trimmed clip ${clipId} to ${newStart}-${newEnd}`);
    } catch (error) {
      console.error('Error trimming clip:', error);
    }
  }, []);

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
                onRemoveClip={handleRemoveClip}
                onTrimClip={handleTrimClip}
              />
            ))
          )}
        </div>
      </div>
    </DndProvider>
  );
};
