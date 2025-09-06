import React, { useCallback, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  uploadVideo, getVideo, VideoOut,
  markClip, listClips, ClipOut,
  buildProject, startExport, getExportStatus, openExportWebSocket,
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
    playerDuration,
    markedIn,
    markedOut,
    clearMarks,
    setIsPlaying
  } = useEditorStore();

  const { data: activeVideo, isLoading: isLoadingVideo } = useQuery<VideoOut>({
    queryKey: ["video", activeVideoId],
    queryFn: () => activeVideoId ? getVideo(activeVideoId) : Promise.reject("No active video"),
    enabled: !!activeVideoId,
  });

  const { data: clips = [], isLoading: isLoadingClips, refetch: refetchClips } = useQuery<ClipOut[]>({
    queryKey: ["clips", activeVideoId],
    queryFn: () => activeVideoId ? listClips(activeVideoId) : Promise.resolve([]),
    enabled: !!activeVideoId,
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
      setActiveVideoId(v.id);
      qc.invalidateQueries({ queryKey: ["video", v.id] });
      qc.invalidateQueries({ queryKey: ["clips", v.id] });
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
      refetchClips();
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

  const startExportMutation = useMutation({
    mutationFn: startExport,
    onMutate: () => {
      toast.loading("Starting export...");
    },
    onSuccess: (exp) => {
      toast.dismiss();
      toast.success("Export started!");
      setExportId(exp.id);
      setExportStatus({
        progress: exp.progress, 
        status: exp.status, 
        download_url: exp.download_url,
        estimated_time_remaining_seconds: undefined // Reset or set initial
      });
      
      const ws = openExportWebSocket(exp.id, (s) => setExportStatus({
        progress: s.progress, status: s.status, download_url: s.download_url, error_message: s.error_message,
        estimated_time_remaining_seconds: s.estimated_time_remaining_seconds
      }));

      const timer = setInterval(async () => {
        try {
          const s = await getExportStatus(exp.id);
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
    },
    onError: (error) => {
      toast.dismiss();
      toast.error(`Failed to start export: ${error.message}`);
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
      order_index: clips.length,
    });
  };

  const handleBuildProject = () => {
    if (!activeVideoId) {
      toast.error("Please upload a video first.");
      return;
    }
    if (clips.length === 0) {
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
    if (clips.length === 0) {
      toast.error("No clips defined. Add clips and build the project before exporting.");
      return;
    }
    startExportMutation.mutate({ video_id: activeVideoId });
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
      <h1>CapCut-Lite Editor</h1>

      <section className="editor-section">
        <h2>1) Upload Video</h2>
        <input type="file" accept="video/*" onChange={handleFileUpload} disabled={upload.isPending} />
        {upload.isPending && <p>Uploading...</p>}
        {activeVideo && (
          <div className="upload-info">
            {activeVideo.thumbnail_url && (
                <img src={activeVideo.thumbnail_url} alt="Video Thumbnail" />
            )}
            <div className="upload-info-meta">
                <p><b>{activeVideo.filename}</b></p>
                <p>Duration: {formatTime(activeVideo.duration || 0)}</p>
                <p className="video-id">ID: {activeVideo.id}</p>
            </div>
          </div>
        )}
      </section>

      <section className="editor-section">
        <h2>2) Video Player & Clip Marking</h2>
        <VideoPlayer videoUrl={activeVideo?.url || ""} videoDuration={activeVideo?.duration || 0} />
        <div className="marking-controls">
            <button 
                onClick={handleAddClip} 
                className="btn"
                disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || (activeVideo && markedOut > activeVideo.duration!) || addClip.isPending}
            >
                {addClip.isPending ? "Adding..." : "Add Clip to Timeline"}
            </button>
            <p className="marks-display">
              Current Marks: IN: {markedIn !== null ? formatTime(markedIn) : "--:--:--"} | OUT: {markedOut !== null ? formatTime(markedOut) : "--:--:--"}
            </p>
        </div>
      </section>

      <section className="editor-section">
        <Timeline clips={clips} videoDuration={activeVideo?.duration || 0} activeVideo={activeVideo} />
      </section>

      <section className="editor-section">
        <h2>3) Build Project & Export</h2>
        <div className="export-controls">
            <button
                onClick={handleBuildProject}
                className="btn"
                disabled={!activeVideoId || clips.length === 0 || buildProjectMutation.isPending}
            >
                {buildProjectMutation.isPending ? "Building..." : "Build .osp Project"}
            </button>
            <button
                onClick={handleStartExport}
                className="btn"
                disabled={!activeVideoId || clips.length === 0 || startExportMutation.isPending}
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