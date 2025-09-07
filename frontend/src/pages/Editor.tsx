import React, { useCallback, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  uploadVideo, getVideo, VideoOut,
  markClip, listClips, ClipOut,
  buildProject, startExport, getExportStatus, openExportWebSocket,
  getLatestActiveExport, // NEW
  getTimelineClips, getVideos, ClipWithVideoOut, // NEW: Multi-video timeline
  clearTimeline // NEW: Clear timeline function
} from "../api/client";
import { useEditorStore } from "../stores/editorStore";
import VideoPlayer from "../components/VideoPlayer";
import Timeline from "../components/Timeline";
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

  // NEW: All available videos
  const { data: videos = [], refetch: refetchVideos } = useQuery<VideoOut[]>({
    queryKey: ["videos"],
    queryFn: getVideos,
  });

  const [exportId, setExportId] = React.useState<string | null>(null);
  const [exportStatus, setExportStatus] = React.useState<{progress:number; status:string; download_url?:string|null; error_message?:string|null; estimated_time_remaining_seconds?:number|null}>({progress:0,status:"idle"});

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
      setExportId(null);
      setExportStatus({progress:0, status:"idle"});
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
    }
  });

  const buildProjectMutation = useMutation({
    mutationFn: buildProject,
    onMutate: () => {
      toast.loading("Building project...");
    },
    onSuccess: () => {
      toast.dismiss();
      toast.success("Project built (.osp) successfully!");
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Project build failed: ${error.message}`);
    }
  });

  // NEW: Effect to check for and resume monitoring an active export on video load
  useEffect(() => {
    if (activeVideoId && !exportId) { // Only check if no export is currently being monitored
      // Reset status for new video
      setExportStatus({progress: 0, status: "idle"});

      (async () => {
        try {
          const activeExportResponse = await getLatestActiveExport(activeVideoId);
          if (activeExportResponse && (activeExportResponse.status === "queued" || activeExportResponse.status === "processing")) {
            toast.success("Resumed monitoring an in-progress export.");
            setExportId(activeExportResponse.id);
            monitorExport(activeExportResponse.id);
          }
        } catch (error) {
          console.error("Error checking for active exports:", error);
          // Don't show toast for initial check failures to avoid spam
        }
      })();
    }
  }, [activeVideoId, exportId]);

  // NEW: Extracted monitoring logic to be reusable
  const monitorExport = (currentExportId: string) => {
    const ws = openExportWebSocket(currentExportId, (s) => setExportStatus({
      progress: s.progress, status: s.status, download_url: s.download_url, error_message: s.error_message,
      estimated_time_remaining_seconds: s.estimated_time_remaining_seconds
    }));

    const timer = setInterval(async () => {
      try {
        const s = await getExportStatus(currentExportId);
        setExportStatus({
          progress: s.progress, status: s.status, download_url: s.download_url, error_message: s.error_message,
          estimated_time_remaining_seconds: s.estimated_time_remaining_seconds
        });
        if (s.status === "completed" || s.status === "error") {
          clearInterval(timer);
          ws.close();
          if (s.status === "completed") toast.success("Export completed!");
          else if (s.status === "error") toast.error(`Export failed: ${s.error_message || "Unknown error"}`);
        }
      } catch (e) {
        console.error("Polling error:", e);
        clearInterval(timer);
        ws.close();
        toast.error("Export polling failed. Check server logs.");
      }
    }, 3000);

    return () => { try { ws.close(); } catch {} clearInterval(timer); };
  };

  // --- Mutations (showing startExportMutation with new logic) ---
  const startExportMutation = useMutation({
    mutationFn: startExport,
    onMutate: () => {
      toast.loading("Starting export...");
    },
    onSuccess: (exp) => {
      toast.dismiss();
      toast.success("Export started!");
      setExportId(exp.id);
      monitorExport(exp.id); // Use the reusable monitoring function
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Failed to start export: ${error.message}`);
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

  const handleStartExport = () => {
    if (!activeVideoId) {
      toast.error("Please upload a video first.");
      return;
    }
    if (timelineClips.length === 0) {
      toast.error("No clips defined. Add clips and build the project before exporting.");
      return;
    }
    startExportMutation.mutate(activeVideoId);
  };


  // NEW: Helper for dynamic class names on the progress bar
  const progressBarClasses = `progress-bar-fill status-${exportStatus.status}`;

  const formatEta = (seconds: number | null | undefined): string => {
    if (seconds === null || seconds === undefined || isNaN(seconds) || seconds < 0) {
      return "N/A";
    }
    if (seconds < 60) return `${Math.ceil(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.ceil(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className="editor-container">
      <h1>🎬 Video Timeline Editor</h1>

      <section className="editor-section">
        <h2>📁 Upload Video</h2>
        <input type="file" accept="video/*" onChange={handleFileUpload} disabled={upload.isPending} />
        {upload.isPending && <p>Uploading...</p>}
        
        {activeVideo && (
          <div className="active-video-info">
            <h3>Current Video:</h3>
            <div className="upload-info">
              <div className="upload-info-meta">
                  <p><b>{activeVideo.filename}</b></p>
                  <p>Duration: {formatTime(activeVideo.duration || 0)}</p>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="editor-section">
        <h2>🎬 Video Player & Clip Marking</h2>
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
          <div className="clip-mode-indicator" style={{ 
            backgroundColor: "#2563eb", 
            color: "white", 
            padding: "0.5rem", 
            borderRadius: "0.5rem", 
            marginBottom: "1rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>🎬 Clip Mode: {formatTime(clipStartTime ?? 0)} - {formatTime(clipEndTime ?? 0)}</span>
            <button 
              onClick={clearClipMode}
              className="btn"
              style={{ backgroundColor: "white", color: "#2563eb" }}
            >
              ↩️ Exit Clip Mode
            </button>
          </div>
        )}
        
        {activeVideo && (
          <div className="marking-controls">
              <button 
                  onClick={() => setMarkedIn(playerCurrentTime)}
                  className="btn"
                  disabled={!activeVideo}
              >
                  📍 Mark IN ({markedIn !== null ? formatTime(markedIn) : "--:--"})
              </button>
              <button 
                  onClick={() => setMarkedOut(playerCurrentTime)}
                  className="btn"
                  disabled={!activeVideo}
              >
                  📍 Mark OUT ({markedOut !== null ? formatTime(markedOut) : "--:--"})
              </button>
              <button 
                  onClick={handleAddClip} 
                  className="btn"
                  disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || (activeVideo && markedOut > activeVideo.duration!) || addClip.isPending}
              >
                  {addClip.isPending ? "Adding..." : "➕ Add to Timeline"}
              </button>
              <div className="marks-display">
                Current: {formatTime(playerCurrentTime)} | 
                Range: {markedIn !== null ? formatTime(markedIn) : "--:--"} to {markedOut !== null ? formatTime(markedOut) : "--:--"}
              </div>
          </div>
        )}
      </section>

      <section className="editor-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2>🎬 Timeline ({timelineClips?.length || 0} clips)</h2>
          <button 
            className="btn btn-danger"
            onClick={() => clearTimelineMutation.mutate()}
            disabled={clearTimelineMutation.isPending || (timelineClips?.length || 0) === 0}
          >
            {clearTimelineMutation.isPending ? "Clearing..." : "Clear Timeline"}
          </button>
        </div>
        <Timeline 
          clips={timelineClips} 
          videoDuration={activeVideo?.duration || 0} 
          activeVideo={activeVideo ?? null}
          isGlobalTimeline={true}
          onClipPlay={handleClipPlay}
        />
      </section>

      <section className="editor-section">
        <h2>🚀 Export Project</h2>
        <div className="export-controls">
            <button
                onClick={handleBuildProject}
                className="btn"
                disabled={!activeVideoId || timelineClips.length === 0 || buildProjectMutation.isPending}
            >
                {buildProjectMutation.isPending ? "Building..." : "Build .osp Project"}
            </button>
            <button
                onClick={handleStartExport}
                className="btn"
                disabled={!activeVideoId || timelineClips.length === 0 || startExportMutation.isPending}
            >
                {startExportMutation.isPending ? "Starting Export..." : "Start Export"}
            </button>
        </div>
        
        {exportId && (
          <div className="export-status-container">
            <h3>Export Status: {exportStatus.status}</h3>
            <div className="progress-bar-container">
              <div
                className={progressBarClasses}
                style={{ width: `${exportStatus.progress}%` }}
              />
            </div>
            <p>Progress: {exportStatus.progress}%</p>
            {exportStatus.status === "processing" && exportStatus.estimated_time_remaining_seconds !== null && (
              <p className="eta-display">ETA: {formatEta(exportStatus.estimated_time_remaining_seconds)}</p>
            )}
            {exportStatus.error_message && (
              <p className="error-message">Error: {exportStatus.error_message}</p>
            )}
            {exportStatus.download_url && exportStatus.status === "completed" && (
              <p className="download-link-container">
                <a href={exportStatus.download_url} download className="download-link">
                  Download Final MP4
                </a>
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}