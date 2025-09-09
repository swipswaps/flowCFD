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


        {/* Essential Timeline Controls */}
        <div style={{ 
          display: "flex", 
          gap: "0.5rem", 
          padding: "1rem",
          flexWrap: "wrap",
          alignItems: "center",
          backgroundColor: "#2a2a2a",
          borderRadius: "8px",
          marginTop: "1rem"
        }}>
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className="btn"
            style={{ 
              padding: "0.5rem 1rem", 
              backgroundColor: isPlaying ? "#ef4444" : "#10b981",
              color: "white",
              border: "none",
              borderRadius: "4px"
            }}
            disabled={!activeVideo}
          >
            {isPlaying ? "⏸️ Pause" : "▶️ Play"}
          </button>
          
          <button 
            onClick={() => setMarkedIn(playerCurrentTime)}
            className="btn"
            style={{ 
              padding: "0.5rem 1rem", 
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "4px"
            }}
            disabled={!activeVideo}
          >
            📍 Mark IN ({markedIn !== null ? formatTime(markedIn) : "--:--"})
          </button>
          
          <button 
            onClick={() => setMarkedOut(playerCurrentTime)}
            className="btn"
            style={{ 
              padding: "0.5rem 1rem", 
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "4px"
            }}
            disabled={!activeVideo}
          >
            📍 Mark OUT ({markedOut !== null ? formatTime(markedOut) : "--:--"})
          </button>
          
          <button 
            onClick={clearMarks}
            className="btn"
            style={{ 
              padding: "0.5rem 1rem", 
              backgroundColor: "#6b7280",
              color: "white",
              border: "none",
              borderRadius: "4px"
            }}
            disabled={!activeVideo}
          >
            🗑️ Clear Marks
          </button>
          
          <button 
            onClick={handleAddClip} 
            className="btn"
            style={{ 
              padding: "0.5rem 1rem", 
              backgroundColor: "#10b981",
              color: "white",
              border: "none",
              borderRadius: "4px",
              fontWeight: "bold"
            }}
            disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || (activeVideo && markedOut > activeVideo.duration!) || addClip.isPending}
          >
            {addClip.isPending ? "Adding..." : "➕ Add to Timeline"}
          </button>
        </div>

        {/* Multi-Track Timeline */}
        <MultiTrackTimeline />
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