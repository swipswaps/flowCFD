// Timeline snapping utilities for professional video editing behavior

export const SNAP_THRESHOLD = 15; // pixels - increased for better magnetic feel
export const PIXELS_PER_SECOND = 50;

export interface SnapPoint {
  time: number;
  type: 'clip_start' | 'clip_end' | 'keyframe' | 'playhead' | 'grid';
  metadata?: {
    clipId?: string;
    trackId?: number;
    isKeyframe?: boolean;
  };
}

export interface SnapResult {
  snapped: boolean;
  snapTime: number;
  originalTime: number;
  snapPoint?: SnapPoint;
  snapDistance: number;
}

export interface TimelineClip {
  id: string;
  track_id: number;
  start_time: number;
  end_time: number;
  timeline_position: number;
}

export interface Track {
  id: number;
  clips: TimelineClip[];
  enabled: boolean;
  locked: boolean;
}

/**
 * Find all potential snap points in the timeline
 */
export function findSnapPoints(
  tracks: Track[], 
  excludeClipId?: string,
  playheadTime?: number,
  keyframes?: number[],
  gridInterval?: number
): SnapPoint[] {
  const snapPoints: SnapPoint[] = [];

  // Add clip-based snap points
  tracks.forEach(track => {
    if (!track.enabled) return;
    
    track.clips.forEach(clip => {
      if (clip.id === excludeClipId) return;
      
      // Clip start
      snapPoints.push({
        time: clip.timeline_position,
        type: 'clip_start',
        metadata: { clipId: clip.id, trackId: clip.track_id }
      });
      
      // Clip end
      snapPoints.push({
        time: clip.timeline_position + (clip.end_time - clip.start_time),
        type: 'clip_end',
        metadata: { clipId: clip.id, trackId: clip.track_id }
      });
    });
  });

  // Add playhead snap point
  if (playheadTime !== undefined) {
    snapPoints.push({
      time: playheadTime,
      type: 'playhead'
    });
  }

  // Add keyframe snap points
  if (keyframes) {
    keyframes.forEach(keyframeTime => {
      snapPoints.push({
        time: keyframeTime,
        type: 'keyframe',
        metadata: { isKeyframe: true }
      });
    });
  }

  // Add grid snap points (if enabled)
  if (gridInterval && gridInterval > 0) {
    const maxTime = Math.max(
      ...tracks.flatMap(track => 
        track.clips.map(clip => clip.timeline_position + (clip.end_time - clip.start_time))
      ),
      playheadTime || 0,
      ...(keyframes || [])
    );
    
    for (let time = 0; time <= maxTime + gridInterval; time += gridInterval) {
      snapPoints.push({
        time,
        type: 'grid'
      });
    }
  }

  return snapPoints.sort((a, b) => a.time - b.time);
}

/**
 * Calculate snap behavior for a given position
 */
export function calculateSnap(
  targetTime: number,
  snapPoints: SnapPoint[],
  enabledSnapTypes: string[] = ['clip_start', 'clip_end', 'keyframe', 'playhead']
): SnapResult {
  const targetPixel = targetTime * PIXELS_PER_SECOND;
  
  let bestSnap: SnapResult = {
    snapped: false,
    snapTime: targetTime,
    originalTime: targetTime,
    snapDistance: Infinity
  };

  // Find the closest snap point within threshold
  for (const snapPoint of snapPoints) {
    if (!enabledSnapTypes.includes(snapPoint.type)) continue;
    
    const snapPixel = snapPoint.time * PIXELS_PER_SECOND;
    const distance = Math.abs(targetPixel - snapPixel);
    
    if (distance <= SNAP_THRESHOLD && distance < bestSnap.snapDistance) {
      bestSnap = {
        snapped: true,
        snapTime: snapPoint.time,
        originalTime: targetTime,
        snapPoint,
        snapDistance: distance
      };
    }
  }

  return bestSnap;
}

/**
 * Calculate magnetic snapping for clip movement
 */
export function calculateMagneticSnap(
  draggedClip: TimelineClip,
  newPosition: number,
  tracks: Track[],
  playheadTime?: number,
  keyframes?: number[]
): {
  startSnap: SnapResult;
  endSnap: SnapResult;
  finalPosition: number;
  snapIndicators: SnapPoint[];
} {
  const clipDuration = draggedClip.end_time - draggedClip.start_time;
  const snapPoints = findSnapPoints(tracks, draggedClip.id, playheadTime, keyframes);
  
  // Calculate snapping for clip start and end
  const startSnap = calculateSnap(newPosition, snapPoints);
  const endSnap = calculateSnap(newPosition + clipDuration, snapPoints);
  
  // Choose the best snap (closest), with preference for clip adjacency
  let finalPosition = newPosition;
  let activeSnapIndicators: SnapPoint[] = [];
  
  if (startSnap.snapped && endSnap.snapped) {
    // Both ends can snap - prioritize clip start/end over other snap types
    const startIsClip = startSnap.snapPoint?.type === 'clip_start' || startSnap.snapPoint?.type === 'clip_end';
    const endIsClip = endSnap.snapPoint?.type === 'clip_start' || endSnap.snapPoint?.type === 'clip_end';
    
    if (startIsClip && !endIsClip) {
      // Prefer clip-to-clip snapping for start
      finalPosition = startSnap.snapTime;
      if (startSnap.snapPoint) activeSnapIndicators.push(startSnap.snapPoint);
    } else if (endIsClip && !startIsClip) {
      // Prefer clip-to-clip snapping for end
      finalPosition = endSnap.snapTime - clipDuration;
      if (endSnap.snapPoint) activeSnapIndicators.push(endSnap.snapPoint);
    } else {
      // Both are clips or both are not clips - choose the closer one
      if (startSnap.snapDistance <= endSnap.snapDistance) {
        finalPosition = startSnap.snapTime;
        if (startSnap.snapPoint) activeSnapIndicators.push(startSnap.snapPoint);
      } else {
        finalPosition = endSnap.snapTime - clipDuration;
        if (endSnap.snapPoint) activeSnapIndicators.push(endSnap.snapPoint);
      }
    }
  } else if (startSnap.snapped) {
    finalPosition = startSnap.snapTime;
    if (startSnap.snapPoint) activeSnapIndicators.push(startSnap.snapPoint);
  } else if (endSnap.snapped) {
    finalPosition = endSnap.snapTime - clipDuration;
    if (endSnap.snapPoint) activeSnapIndicators.push(endSnap.snapPoint);
  }

  // Ensure position is not negative
  finalPosition = Math.max(0, finalPosition);

  return {
    startSnap,
    endSnap,
    finalPosition,
    snapIndicators: activeSnapIndicators
  };
}

/**
 * Generate visual snap indicators for the timeline
 */
export function generateSnapIndicators(
  snapPoints: SnapPoint[],
  visibleTimeRange: { start: number; end: number },
  trackHeight: number,
  totalTracks: number
): React.CSSProperties[] {
  return snapPoints
    .filter(point => 
      point.time >= visibleTimeRange.start && 
      point.time <= visibleTimeRange.end
    )
    .map(point => {
      const pixelPosition = point.time * PIXELS_PER_SECOND;
      
      // Color coding based on snap type
      let color = '#6b7280'; // Default gray
      let opacity = 0.6;
      
      switch (point.type) {
        case 'clip_start':
        case 'clip_end':
          color = '#3b82f6'; // Blue
          opacity = 0.7;
          break;
        case 'keyframe':
          color = '#10b981'; // Green
          opacity = 0.8;
          break;
        case 'playhead':
          color = '#ef4444'; // Red
          opacity = 0.9;
          break;
        case 'grid':
          color = '#9ca3af'; // Light gray
          opacity = 0.4;
          break;
      }

      return {
        position: 'absolute' as const,
        left: `${pixelPosition}px`,
        top: 0,
        width: '2px',
        height: `${trackHeight * totalTracks}px`,
        backgroundColor: color,
        opacity,
        pointerEvents: 'none' as const,
        zIndex: 100,
        transition: 'opacity 0.2s ease',
      };
    });
}

/**
 * Hook for timeline snapping behavior
 */
export function useTimelineSnapping(
  tracks: Track[],
  playheadTime?: number,
  keyframes?: number[],
  gridInterval?: number,
  enabledSnapTypes: string[] = ['clip_start', 'clip_end', 'keyframe', 'playhead']
) {
  const snapPoints = findSnapPoints(tracks, undefined, playheadTime, keyframes, gridInterval);
  
  const snapClipPosition = (
    clip: TimelineClip,
    newPosition: number
  ) => {
    return calculateMagneticSnap(clip, newPosition, tracks, playheadTime, keyframes);
  };

  const snapToNearestPoint = (targetTime: number, excludeClipId?: string) => {
    const relevantSnapPoints = findSnapPoints(tracks, excludeClipId, playheadTime, keyframes, gridInterval);
    return calculateSnap(targetTime, relevantSnapPoints, enabledSnapTypes);
  };

  const getSnapIndicators = (visibleTimeRange: { start: number; end: number }, trackHeight: number) => {
    return generateSnapIndicators(snapPoints, visibleTimeRange, trackHeight, tracks.length);
  };

  return {
    snapPoints,
    snapClipPosition,
    snapToNearestPoint,
    getSnapIndicators
  };
}
