import React, { useCallback, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  uploadVideo, getVideo, VideoOut,
  markClip, listClips, ClipOut,
  buildProject,
  getTimelineClips, getVideos, ClipWithVideoOut, // NEW: Multi-video timeline
  clearTimeline, // NEW: Clear timeline function
  getVideoKeyframes, extractClipLossless, smartCutClip, // NEW: Lossless features
  KeyframeData, LosslessExtractionResult // NEW: Type imports
} from "../api/client";
import { useEditorStore } from "../stores/editorStore";
import VideoPlayer from "../components/VideoPlayer";
import Timeline from "../components/Timeline";
import { MultiTrackTimeline } from '../components/MultiTrackTimeline';
import { AudioWaveformDemo } from '../components/AudioWaveformDemo';
import { AudioEffectsPanel } from '../components/AudioEffectsPanel';
import { AudioProcessingHistory } from '../components/AudioProcessingHistory';
import LosslessIndicator from "../components/LosslessIndicator";
import KeyframeTimeline from "../components/KeyframeTimeline";
import { formatTime } from "../utils/time";
import "./Editor.css"; // NEW: Import the stylesheet

export default function Editor() {
  const qc = useQueryClient();
  
  const {
    activeVideoId,
    setActiveVideoId,
    playerCurrentTime,
    setPlayerCurrentTime,
    playerDuration,
    markedIn,
    markedOut,
    setMarkedIn,
    setMarkedOut,
    clearMarks,
    isPlaying,
    setIsPlaying,
    clipStartTime,
    clipEndTime,
    isClipMode,
    setClipMode,
    clearClipMode
  } = useEditorStore();

  const { data: activeVideo, isLoading: isLoadingVideo } = useQuery<VideoOut>({
    queryKey: ["video", activeVideoId],
    queryFn: () => activeVideoId ? getVideo(activeVideoId) : Promise.reject("No active video"),
    enabled: !!activeVideoId,
  });

  // NEW: Global timeline clips (from all videos)
  const { data: timelineClips = [], isLoading: isLoadingClips, refetch: refetchTimelineClips } = useQuery<ClipWithVideoOut[]>({
    queryKey: ["timeline-clips"],
    queryFn: getTimelineClips,
  });

  // NEW: Keyframe data for lossless editing
  const { data: keyframeData } = useQuery<KeyframeData>({
    queryKey: ["video", activeVideoId, "keyframes"],
    queryFn: () => getVideoKeyframes(activeVideoId!),
    enabled: !!activeVideoId,
  });

  // NEW: All available videos
  const { data: videos = [], refetch: refetchVideos } = useQuery<VideoOut[]>({
    queryKey: ["videos"],
    queryFn: getVideos,
  });


  // --- Mutations ---
  const upload = useMutation({
    mutationFn: uploadVideo,
    onMutate: () => {
      toast.loading("Uploading video...");
    },
    onSuccess: (v) => {
      toast.dismiss();
      toast.success(`Video "${v.filename}" uploaded.`);
      // Set uploaded video as active (users expect this behavior)
      setActiveVideoId(v.id);
      qc.invalidateQueries({ queryKey: ["videos"] });
      qc.invalidateQueries({ queryKey: ["video", v.id] });
      clearMarks();
      setIsPlaying(false);
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Upload failed: ${error.message}`);
    }
  });

  const addClip = useMutation({
    mutationFn: markClip,
    onMutate: () => {
      toast.loading("Adding clip...");
    },
    onSuccess: () => {
      toast.dismiss();
      toast.success("Clip added successfully.");
      refetchTimelineClips(); // NEW: Refresh global timeline clips
      clearMarks();
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Failed to add clip: ${error.message}`);
    },
    onSettled: () => {
      // Always dismiss loading toast regardless of success/error
      toast.dismiss();
    }
  });

  const buildProjectMutation = useMutation({
    mutationFn: buildProject,
    onMutate: () => {
      toast.loading("Building timeline video...");
    },
    onSuccess: (data) => {
      toast.dismiss();
      toast.success(`Timeline video built successfully! ${data.clips_count} clips concatenated.`);
      
      // Create download link and trigger download
      const downloadLink = document.createElement('a');
      downloadLink.href = data.download_url;
      downloadLink.download = data.output_file;
      downloadLink.style.display = 'none';
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      
      console.log("Built video:", data);
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Video build failed: ${error.message}`);
    }
  });


  const clearTimelineMutation = useMutation({
    mutationFn: clearTimeline,
    onMutate: () => {
      toast.loading("Clearing timeline...");
    },
    onSuccess: (result) => {
      toast.dismiss();
      toast.success(result.message);
      qc.invalidateQueries({ queryKey: ["timeline-clips"] });
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Failed to clear timeline: ${error.message}`);
    }
  });

  // NEW: Lossless extraction mutations
  const losslessExtractMutation = useMutation<LosslessExtractionResult, Error, { video_id: string; start: number; end: number; }>({
    mutationFn: extractClipLossless,
    onMutate: () => {
      toast.loading("Extracting with lossless priority...");
    },
    onSuccess: (result) => {
      toast.dismiss();
      toast.success(`Lossless extraction successful! Method: ${result.method_used}`);
      if (result.download_url) {
        // Auto-download the file
        const a = document.createElement('a');
        a.href = result.download_url;
        a.download = result.filename || 'lossless_extract.mp4';
        a.click();
      }
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Lossless extraction failed: ${error.message}`);
    },
    onSettled: () => {
      toast.dismiss();
    }
  });

  const smartCutMutation = useMutation<LosslessExtractionResult, Error, { video_id: string; start: number; end: number; }>({
    mutationFn: smartCutClip,
    onMutate: () => {
      toast.loading("Performing smart cut...");
    },
    onSuccess: (result) => {
      toast.dismiss();
      toast.success(`Smart cut successful! Quality preserved: ${result.quality_preserved ? 'Yes' : 'No'}`);
      if (result.download_url) {
        // Auto-download the file
        const a = document.createElement('a');
        a.href = result.download_url;
        a.download = result.filename || 'smart_cut.mp4';
        a.click();
      }
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Smart cut failed: ${error.message}`);
    },
    onSettled: () => {
      toast.dismiss();
    }
  });


  // --- Event Handlers ---
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      upload.mutate(f);
    }
  };

  const handleAddClip = () => {
    if (!activeVideoId || markedIn === null || markedOut === null) {
      toast.error("Please select a video and mark both IN and OUT points.");
      return;
    }
    if (markedOut <= markedIn) {
      toast.error("OUT point must be greater than IN point.");
      return;
    }
    if (activeVideo && markedOut > activeVideo.duration!) {
      toast.error(`OUT point (${formatTime(markedOut)}) exceeds video duration (${formatTime(activeVideo.duration!)}).`);
      return;
    }
    addClip.mutate({
      video_id: activeVideoId,
      start_time: markedIn,
      end_time: markedOut,
      order_index: timelineClips.length,
    });
  };

  // Handle clip playback from timeline - loads clip segment only
  const handleClipPlay = useCallback((clip: ClipWithVideoOut) => {
    // Switch to the clip's video
    setActiveVideoId(clip.video.id);
    
    // Enable clip mode with clip boundaries
    setClipMode(clip.start_time, clip.end_time);
    
    // Start playing the clip
    setIsPlaying(true);
    
    console.log(`Playing clip from ${clip.video.filename}: ${clip.start_time}s - ${clip.end_time}s`);
  }, [setActiveVideoId, setClipMode, setIsPlaying]);

  const handleBuildProject = () => {
    if (!activeVideoId) {
      toast.error("Please upload a video first.");
      return;
    }
    if (timelineClips.length === 0) {
      toast.error("No clips defined. Add clips to the timeline before building the project.");
      return;
    }
    buildProjectMutation.mutate(activeVideoId);
  };


  return (
    <div className="editor-container">
      <section className="editor-section">
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
          <span>📁 Upload Video</span>
        <input type="file" accept="video/*" onChange={handleFileUpload} disabled={upload.isPending} />
          {upload.isPending && <span>Uploading...</span>}
        </div>
        {isLoadingVideo ? (
          <div>Loading video...</div>
        ) : activeVideo ? (
          <VideoPlayer 
            videoUrl={activeVideo.url ?? ""} 
            videoDuration={activeVideo.duration ?? 0}
            clipStartTime={isClipMode ? clipStartTime ?? undefined : undefined}
            clipEndTime={isClipMode ? clipEndTime ?? undefined : undefined}
          />
        ) : (
          <div className="no-video-message">
            <p>👈 Select a video from the library above to start editing</p>
          </div>
        )}
        
        {isClipMode && (
          <div className="clip-preview-banner" style={{ 
            background: "linear-gradient(135deg, #3b82f6, #1d4ed8)", 
            color: "white", 
            padding: "0.75rem 1rem", 
            borderRadius: "0.75rem", 
            marginBottom: "1rem",
            boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
            border: "1px solid rgba(255, 255, 255, 0.2)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "1.1rem", fontWeight: "600" }}>🎬 Previewing Clip</span>
                <span style={{ 
                  backgroundColor: "rgba(255, 255, 255, 0.2)", 
                  padding: "0.25rem 0.5rem", 
                  borderRadius: "0.25rem",
                  fontSize: "0.85rem"
                }}>
                  {formatTime(clipStartTime ?? 0)} → {formatTime(clipEndTime ?? 0)} 
                  ({formatTime((clipEndTime ?? 0) - (clipStartTime ?? 0))} long)
                </span>
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button 
                  onClick={clearClipMode}
                  className="btn"
                  style={{ 
                    backgroundColor: "rgba(255, 255, 255, 0.9)", 
                    color: "#1d4ed8",
                    border: "none",
                    padding: "0.5rem 1rem",
                    fontSize: "0.9rem",
                    fontWeight: "500"
                  }}
                >
                  📺 Play Full Video
                </button>
              </div>
            </div>
            <div style={{ fontSize: "0.9rem", opacity: "0.9" }}>
              💡 Video playback is limited to this clip. Click "Play Full Video" to see the entire video.
            </div>
          </div>
        )}


        {/* 🎬 Multi-Track Timeline - Integrated Interface */}
        <div className="timeline-integrated-header" style={{ 
          marginTop: "1rem",
          border: "1px solid #444",
          borderRadius: "8px",
          backgroundColor: "#2a2a2a"
        }}>
          {/* Timeline Title Section */}
          <div className="timeline-title-section" style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "0.75rem 1rem",
            borderBottom: "1px solid #444",
            backgroundColor: "#1e1e1e"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#eee" }}>🎬 Multi-Track Timeline</h3>
              <span className="timeline-info" style={{ fontSize: "0.9rem", color: "#888" }}>
                {timelineClips.length} clips | {activeVideo?.filename || 'No video selected'}
              </span>
            </div>
          </div>

          {/* Timeline Controls Rows */}
          <div className="timeline-controls-row" style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
            padding: "1rem"
          }}>
            {/* Row 1: Playback & Marking Controls */}
            <div className="marking-controls" style={{
              display: "flex",
              gap: "0.5rem",
              flexWrap: "wrap",
              alignItems: "center"
            }}>
              <button 
                onClick={() => setIsPlaying(!isPlaying)}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap",
                  backgroundColor: isPlaying ? "#ef4444" : "#10b981",
                  color: "white"
                }}
                disabled={!activeVideo}
              >
                {isPlaying ? "⏸️ Pause" : "▶️ Play"}
              </button>
              <button 
                onClick={() => {
                  const newTime = Math.max(0, playerCurrentTime - 5);
                  setPlayerCurrentTime(newTime);
                }}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap" 
                }}
                disabled={!activeVideo}
              >
                ⏪ -5s
              </button>
              <button 
                onClick={() => {
                  if (activeVideo) {
                    const newTime = Math.min(activeVideo.duration || 0, playerCurrentTime + 5);
                    setPlayerCurrentTime(newTime);
                  }
                }}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap" 
                }}
                disabled={!activeVideo}
              >
                ⏩ +5s
              </button>
              <button 
                onClick={() => setMarkedIn(playerCurrentTime)}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap" 
                }}
                disabled={!activeVideo}
              >
                📍 Mark IN ({markedIn !== null ? formatTime(markedIn) : "--:--"})
              </button>
              <button 
                onClick={() => setMarkedOut(playerCurrentTime)}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap" 
                }}
                disabled={!activeVideo}
              >
                📍 Mark OUT ({markedOut !== null ? formatTime(markedOut) : "--:--"})
              </button>
              <button 
                onClick={clearMarks}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap" 
                }}
                disabled={!activeVideo}
              >
                🗑️ Clear Marks
              </button>
            <button 
                onClick={handleAddClip} 
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#007bff",
                  color: "white"
                }}
                disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || (activeVideo && markedOut > activeVideo.duration!) || addClip.isPending}
            >
                {addClip.isPending ? "Adding..." : "➕ Add to Timeline"}
            </button>
        </div>

            {/* Row 2: Processing & Building */}
            <div className="processing-controls" style={{
              display: "flex",
              gap: "0.5rem",
              flexWrap: "wrap",
              alignItems: "center"
            }}>
              <button 
                onClick={() => {
                  if (activeVideoId && markedIn !== null && markedOut !== null) {
                    losslessExtractMutation.mutate({ 
                      video_id: activeVideoId, 
                      start: markedIn, 
                      end: markedOut 
                    });
                  }
                }}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#10b981", 
                  color: "white"
                }}
                disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || losslessExtractMutation.isPending}
                title="Extract with maximum quality preservation"
              >
                {losslessExtractMutation.isPending ? "⏳ Extracting..." : "🎯 Lossless Extract"}
              </button>
              <button 
                onClick={() => {
                  if (activeVideoId && markedIn !== null && markedOut !== null) {
                    smartCutMutation.mutate({ 
                      video_id: activeVideoId, 
                      start: markedIn, 
                      end: markedOut 
                    });
                  }
                }}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#f59e0b", 
                  color: "white"
                }}
                disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || smartCutMutation.isPending}
                title="Frame-accurate cutting with minimal quality loss"
              >
                {smartCutMutation.isPending ? "⏳ Cutting..." : "✂️ Smart Cut"}
              </button>
            <button
                onClick={() => {
                  fetch('/api/projects/build', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ quality_target: 'balanced' })
                  })
                  .then(response => response.json())
                  .then(data => {
                    if (data.success) {
                      toast.success(`Build complete: ${data.processing_time.toFixed(1)}s`);
                      const a = document.createElement('a');
                      a.href = data.download_url;
                      a.download = data.output_file;
                      a.click();
                    } else {
                      toast.error('Build failed');
                    }
                  })
                  .catch(error => {
                    toast.error(`Build error: ${error.message}`);
                  });
                }}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#007bff",
                  color: "white"
                }}
                disabled={timelineClips.length === 0}
              >
                🔧 Build Timeline
            </button>
            <button
                onClick={() => {
                  fetch('/api/timeline/build-lossless', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ quality_target: 'lossless' })
                  })
                  .then(response => response.json())
                  .then(data => {
                    if (data.success) {
                      toast.success(`✅ Lossless build: ${data.method_used} | ${data.processing_time.toFixed(1)}s`);
                      const a = document.createElement('a');
                      a.href = data.download_url;
                      a.download = data.output_file;
                      a.click();
                    } else {
                      toast.error('Lossless build failed');
                    }
                  })
                  .catch(error => {
                    toast.error(`Build error: ${error.message}`);
                  });
                }}
                className="btn"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#8b5cf6",
                  color: "white"
                }}
                disabled={timelineClips.length === 0}
              >
                🌟 Lossless Build
              </button>
              <button 
                onClick={() => clearTimelineMutation.mutate()}
                className="btn btn-danger"
                style={{ 
                  padding: "0.375rem 0.75rem", 
                  fontSize: "0.875rem", 
                  whiteSpace: "nowrap"
                }}
                disabled={clearTimelineMutation.isPending || (timelineClips?.length || 0) === 0}
              >
                Clear Timeline
              </button>
              {/* Keyframe Controls - Integrated */}
              {keyframeData && (
                <button 
                  onClick={() => {
                    // Find nearest keyframe to current time
                    const nearest = keyframeData.keyframes.reduce((prev, curr) => 
                      Math.abs(curr - playerCurrentTime) < Math.abs(prev - playerCurrentTime) ? curr : prev
                    );
                    setPlayerCurrentTime(nearest);
                  }}
                  className="btn"
                  style={{
                    padding: "0.375rem 0.75rem",
                    fontSize: "0.875rem",
                    whiteSpace: "nowrap",
                    backgroundColor: "#10b981",
                    color: "white"
                  }}
                  disabled={!activeVideo}
                  title={`${keyframeData.keyframes.length} keyframes detected`}
                >
                  📍 Snap to Keyframe
            </button>
              )}
            </div>
        </div>
          <div style={{ padding: "1rem" }}>
            <MultiTrackTimeline />
            {timelineClips.length > 0 && (
              <div style={{ marginTop: "1rem" }}>
                <Timeline 
                  clips={timelineClips} 
                  videoDuration={activeVideo?.duration || 0} 
                  activeVideo={activeVideo ?? null}
                  isGlobalTimeline={true}
                  onClipPlay={handleClipPlay}
              />
            </div>
            )}
          </div>
        </div>
      </section>

      <section className="editor-section">
          <AudioWaveformDemo />
        </section>

        <section className="editor-section">
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
            <AudioEffectsPanel 
              videoId={activeVideo?.id}
              onProcessingComplete={(result) => {
                // Add to processing history
                if ((window as any).addAudioProcessingToHistory) {
                  (window as any).addAudioProcessingToHistory(result);
                }
                console.log('Audio processing completed:', result);
              }}
            />
            <AudioProcessingHistory />
          </div>
      </section>

    </div>
  );
}