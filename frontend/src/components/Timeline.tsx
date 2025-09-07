import React, { useState, useRef, useEffect, useCallback } from "react";
import toast from "react-hot-toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ClipOut, deleteClip, updateClip, reorderClips, VideoOut } from "../api/client";
import { useEditorStore } from "../stores/editorStore";
import { formatTime } from "../utils/time";

interface TimelineProps {
  clips: ClipOut[];
  videoDuration: number;
  activeVideo: VideoOut | null; // Pass activeVideo to get thumbnail_url
}

// Define the expected strip height and frame interval from backend generation
// These should ideally come from backend metadata, but for now, match backend's ffmpeg_utils
const THUMBNAIL_STRIP_HEIGHT = 80; // pixels
const THUMBNAIL_FRAME_INTERVAL = 5; // seconds

export default function Timeline({ clips, videoDuration, activeVideo }: TimelineProps) {
  const qc = useQueryClient();
  const { playerCurrentTime, setPlayerCurrentTime, selectedClipId, setSelectedClipId, setIsPlaying } = useEditorStore();
  const timelineRef = useRef<HTMLDivElement>(null);
  
  const [timelineClips, setTimelineClips] = useState(clips);
  const [hoveredClipId, setHoveredClipId] = useState<string | null>(null);

  useEffect(() => {
    setTimelineClips(clips);
  }, [clips]);

  const calculateTotalTimelineDuration = useCallback(() => {
    return timelineClips.reduce((sum, clip) => sum + (clip.end_time - clip.start_time), 0);
  }, [timelineClips]);

  const handleDeleteClip = useMutation({
    mutationFn: deleteClip,
    onSuccess: (_, clipId) => {
      toast.success("Clip deleted successfully.");
      if (activeVideo) {
        qc.invalidateQueries({ queryKey: ["clips", activeVideo.id] });
      }
      setSelectedClipId(null);
    },
    onError: (error) => {
      toast.error(`Error deleting clip: ${error.message}`);
    },
  });

  const handleUpdateClip = useMutation({
    mutationFn: ({ clip_id, input }: { clip_id: string, input: { video_id: string, start_time: number, end_time: number, order_index: number } }) => updateClip(clip_id, input),
    onSuccess: () => {
      toast.success("Clip updated successfully.");
      if (activeVideo) {
        qc.invalidateQueries({ queryKey: ["clips", activeVideo.id] });
      }
    },
    onError: (error) => {
      toast.error(`Error updating clip: ${error.message}`);
    },
  });

  const handleReorderClips = useMutation({
    mutationFn: ({ video_id, clip_ids }: { video_id: string, clip_ids: string[] }) => reorderClips(video_id, clip_ids),
    onSuccess: () => {
      toast.success("Clips reordered successfully.");
      if (activeVideo) {
        qc.invalidateQueries({ queryKey: ["clips", activeVideo.id] });
      }
    },
    onError: (error) => {
      toast.error(`Error reordering clips: ${error.message}`);
    },
  });

  const handleMoveClip = useCallback((clipId: string, direction: 'up' | 'down') => {
    if (!activeVideo) return;
    const currentOrder = timelineClips.findIndex(c => c.id === clipId);
    if (currentOrder === -1) return;

    let newOrder = currentOrder;
    if (direction === 'up' && currentOrder > 0) {
      newOrder = currentOrder - 1;
    } else if (direction === 'down' && currentOrder < timelineClips.length - 1) {
      newOrder = currentOrder + 1;
    } else {
      return;
    }

    const newTimelineClips = Array.from(timelineClips);
    const [movedClip] = newTimelineClips.splice(currentOrder, 1);
    newTimelineClips.splice(newOrder, 0, movedClip);

    setTimelineClips(newTimelineClips);

    const newClipIdsOrder = newTimelineClips.map(c => c.id);
    handleReorderClips.mutate({ video_id: activeVideo.id, clip_ids: newClipIdsOrder });

  }, [timelineClips, activeVideo, handleReorderClips]);

  const handleTrimClip = useCallback((clipId: string, type: 'start' | 'end', newValue: number) => {
    if (!activeVideo) return;
    const clipToUpdate = timelineClips.find(c => c.id === clipId);
    if (!clipToUpdate) return;

    let newStartTime = clipToUpdate.start_time;
    let newEndTime = clipToUpdate.end_time;

    if (type === 'start') {
      newStartTime = Math.max(0, Math.min(newValue, newEndTime - 0.1));
    } else {
      newEndTime = Math.min(activeVideo.duration || videoDuration, Math.max(newValue, newStartTime + 0.1));
    }

    if (newEndTime <= newStartTime) {
      toast.error("Clip duration must be positive.");
      return;
    }

    handleUpdateClip.mutate({
      clip_id: clipId,
      input: {
        video_id: activeVideo.id,
        start_time: newStartTime,
        end_time: newEndTime,
        order_index: clipToUpdate.order_index
      }
    });
  }, [timelineClips, activeVideo, videoDuration, handleUpdateClip]);


  const playheadPosition = useCallback(() => {
    let totalDurationBeforeCurrentTime = 0;
    for (const clip of timelineClips) {
      const clipDuration = clip.end_time - clip.start_time;
      if (playerCurrentTime >= clip.start_time && playerCurrentTime <= clip.end_time) {
        const timeInClip = playerCurrentTime - clip.start_time;
        const totalTimelineDuration = calculateTotalTimelineDuration();
        if (totalTimelineDuration === 0) return 0;
        return ((totalDurationBeforeCurrentTime + timeInClip) / totalTimelineDuration) * 100;
      }
      totalDurationBeforeCurrentTime += clipDuration;
    }
    return 0;
  }, [playerCurrentTime, timelineClips, calculateTotalTimelineDuration]);
  
  const totalTimelineDuration = calculateTotalTimelineDuration();

  const getThumbnailClipStyle = useCallback((clip: ClipOut, isHovered: boolean, isSelected: boolean) => {
    if (!activeVideo?.thumbnail_strip_url || !activeVideo.duration || activeVideo.duration === 0) {
      return {};
    }

    // Calculate the frame index for the clip's start time on the strip
    const frameIndex = Math.floor(clip.start_time / THUMBNAIL_FRAME_INTERVAL);
    
    // Calculate number of frames in the strip and frame width
    const totalFrames = Math.ceil(activeVideo.duration / THUMBNAIL_FRAME_INTERVAL);
    
    // The strip is scaled to fit the timeline height, so we need to calculate the actual frame width
    // based on the strip's aspect ratio and the timeline height
    const stripAspectRatio = totalFrames * (16 / 9); // Assume 16:9 frames
    const stripDisplayWidth = THUMBNAIL_STRIP_HEIGHT * stripAspectRatio;
    const frameWidth = stripDisplayWidth / totalFrames;
    
    // Calculate background-position-x to "scroll" the strip to the correct frame
    const backgroundPositionX = -(frameIndex * frameWidth);

    return {
      backgroundImage: `url(${activeVideo.thumbnail_strip_url})`,
      backgroundSize: 'auto 100%', // Scale height to fit, width auto (to maintain aspect ratio of the strip)
      backgroundPosition: `${backgroundPositionX}px center`, // Use pixels for precise positioning
      backgroundRepeat: 'no-repeat',
      filter: 'brightness(0.7)', // Slightly dim thumbnail to make text readable
      transition: 'transform 0.1s ease-out, filter 0.1s ease-out, z-index 0.1s', // Smooth transition for hover
      transform: isHovered ? 'scale(1.05)' : 'scale(1)', // 'Grow' effect on hover
      zIndex: isHovered ? 11 : (isSelected ? 5 : 1), // Bring hovered clip to front, selected secondary
      overflow: 'hidden', // Ensure background doesn't bleed outside clip boundary
    };
  }, [activeVideo, hoveredClipId, selectedClipId]);


  const handleClipClick = useCallback((clip: ClipOut) => {
    setSelectedClipId(clip.id);
    setPlayerCurrentTime(clip.start_time); // Seek video player to clip start
    setIsPlaying(true); // Start playing from clip start
  }, [setSelectedClipId, setPlayerCurrentTime, setIsPlaying]);


  return (
    <div style={{ marginTop: "24px", width: "100%", maxWidth: "800px", margin: "0 auto" }}>
      <h2>Timeline</h2>
      <div
        ref={timelineRef}
        style={{
          display: "flex",
          position: "relative",
          height: `${THUMBNAIL_STRIP_HEIGHT}px`, // Match timeline height to strip height
          border: "1px solid #555",
          borderRadius: "4px",
          backgroundColor: "#222",
          overflowX: "auto",
          marginBottom: "16px",
        }}
      >
        {activeVideo && totalTimelineDuration > 0 && (
          <div
            style={{
              position: "absolute",
              left: `${playheadPosition()}%`,
              top: 0,
              bottom: 0,
              width: "2px",
              background: "yellow",
              zIndex: 10,
            }}
          />
        )}
        {clips.length === 0 && (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", width: "100%", color: "#888" }}>
            No clips added yet. Mark IN/OUT points in the player and click "Add Clip to Timeline".
          </div>
        )}
        {timelineClips.map((clip, index) => {
          const clipAbsoluteDuration = clip.end_time - clip.start_time;
          const percentageOfTotal = totalTimelineDuration > 0 ? (clipAbsoluteDuration / totalTimelineDuration) * 100 : 0;
          const isSelected = selectedClipId === clip.id;
          const isHovered = hoveredClipId === clip.id;

          return (
            <div
              key={clip.id}
              onClick={() => handleClipClick(clip)}
              onMouseEnter={() => setHoveredClipId(clip.id)}
              onMouseLeave={() => setHoveredClipId(null)}
              style={{
                flexShrink: 0,
                width: `${percentageOfTotal}%`,
                height: "100%",
                backgroundColor: isSelected ? "rgba(76, 175, 80, 0.5)" : "rgba(0, 123, 255, 0.5)", // Transparent background to see thumbnail
                border: isSelected ? "2px solid yellow" : (isHovered ? "1px solid white" : "1px solid #1a1a1a"),
                boxSizing: "border-box",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                color: "white",
                fontSize: "12px",
                fontWeight: "bold",
                cursor: "pointer",
                position: "relative",
                ...getThumbnailClipStyle(clip, isHovered, isSelected)
              }}
              title={`Clip ${index + 1}: ${formatTime(clip.start_time)} - ${formatTime(clip.end_time)}`}
            >
              <div style={{ zIndex: 1, textShadow: '1px 1px 2px rgba(0,0,0,0.8)' }}>
                Clip {index + 1}
                <div style={{ fontSize: "10px", marginTop: "4px" }}>
                  {formatTime(clip.start_time)} - {formatTime(clip.end_time)}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {activeVideo && selectedClipId && (
        <div style={{ background: "#333", padding: "16px", borderRadius: "8px", marginTop: "16px" }}>
          <h3>Selected Clip: {`Clip ${timelineClips.findIndex(c => c.id === selectedClipId) + 1}`}</h3>
          {timelineClips.find(c => c.id === selectedClipId) && (
            <>
              <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                <button 
                  onClick={() => handleMoveClip(selectedClipId, 'up')} 
                  disabled={timelineClips.findIndex(c => c.id === selectedClipId) === 0}>
                  Move Up
                </button>
                <button 
                  onClick={() => handleMoveClip(selectedClipId, 'down')}
                  disabled={timelineClips.findIndex(c => c.id === selectedClipId) === timelineClips.length - 1}>
                  Move Down
                </button>
                <button onClick={() => handleDeleteClip.mutate(selectedClipId)}>Delete Clip</button>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <div>
                  <label htmlFor="trimStart">Start Time (s):</label>
                  <input
                    id="trimStart"
                    type="number"
                    step="0.01"
                    value={timelineClips.find(c => c.id === selectedClipId)?.start_time.toFixed(2) || '0.00'}
                    onChange={(e) => handleTrimClip(selectedClipId, 'start', parseFloat(e.target.value))}
                    style={{ width: "calc(100% - 10px)", padding: "5px" }}
                  />
                </div>
                <div>
                  <label htmlFor="trimEnd">End Time (s):</label>
                  <input
                    id="trimEnd"
                    type="number"
                    step="0.01"
                    value={timelineClips.find(c => c.id === selectedClipId)?.end_time.toFixed(2) || '0.00'}
                    onChange={(e) => handleTrimClip(selectedClipId, 'end', parseFloat(e.target.value))}
                    style={{ width: "calc(100% - 10px)", padding: "5px" }}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}