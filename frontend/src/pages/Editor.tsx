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
  const [exportStatus, setExportStatus] = React.useState<{progress:number; status:string; download_url?:string|null; error_message?:string|null}>({progress:0,status:"idle"});

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
      setExportStatus({progress: exp.progress, status: exp.status, download_url: exp.download_url});
      
      const ws = openExportWebSocket(exp.id, (s) => setExportStatus({
        progress: s.progress, status: s.status, download_url: s.download_url, error_message: s.error_message
      }));

      const timer = setInterval(async () => {
        try {
          const s = await getExportStatus(exp.id);
          setExportStatus({
            progress: s.progress, status: s.status, download_url: s.download_url, error_message: s.error_message
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


  // Basic Styling
  const sectionStyle: React.CSSProperties = {
    marginTop: "24px",
    padding: "16px",
    border: "1px solid #444",
    borderRadius: "8px",
    backgroundColor: "#2a2a2a",
    color: "#eee",
  };

  const buttonStyle: React.CSSProperties = {
    padding: "8px 16px",
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "16px",
    marginRight: "8px",
    transition: "background-color 0.2s",
  };

  const disabledButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: "#555",
    cursor: "not-allowed",
  };

  return (
    <div style={{ padding: "24px", fontFamily: "ui-sans-serif, system-ui", backgroundColor: "#1e1e1e", minHeight: "100vh" }}>
      <h1 style={{ color: "#eee", textAlign: "center", marginBottom: "32px" }}>CapCut-Lite Editor</h1>

      <section style={sectionStyle}>
        <h2 style={{ color: "#eee", marginBottom: "16px" }}>1) Upload Video</h2>
        <input type="file" accept="video/*" onChange={handleFileUpload} disabled={upload.isPending} />
        {upload.isPending && <p>Uploading...</p>}
        {activeVideo && (
          <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "16px" }}>
            {activeVideo.thumbnail_url && (
                <img src={activeVideo.thumbnail_url} alt="Video Thumbnail" style={{ width: "100px", height: "auto", borderRadius: "4px" }} />
            )}
            <div>
                <p><b>{activeVideo.filename}</b></p>
                <p>Duration: {formatTime(activeVideo.duration || 0)}</p>
                <p style={{ fontSize: "12px", color: "#bbb" }}>ID: {activeVideo.id}</p>
            </div>
          </div>
        )}
      </section>

      {/* Section 2: Video Player & Clip Marking - Always render */}
      <section style={sectionStyle}>
        <h2 style={{ color: "#eee", marginBottom: "16px" }}>2) Video Player & Clip Marking</h2>
        {/* Pass activeVideo.url, which will be "" if no video is uploaded */}
        <VideoPlayer videoUrl={activeVideo?.url || ""} videoDuration={activeVideo?.duration || 0} />
        <div style={{ marginTop: "16px", textAlign: "center" }}>
            <button 
                onClick={handleAddClip} 
                style={(!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || (activeVideo && markedOut > activeVideo.duration!) || addClip.isPending) ? disabledButtonStyle : buttonStyle}
                disabled={!activeVideoId || markedIn === null || markedOut === null || markedOut <= markedIn || (activeVideo && markedOut > activeVideo.duration!) || addClip.isPending}
            >
                {addClip.isPending ? "Adding..." : "Add Clip to Timeline"}
            </button>
            <p style={{ marginTop: "8px", color: "#bbb" }}>
              Current Marks: IN: {markedIn !== null ? formatTime(markedIn) : "--:--:--"} | OUT: {markedOut !== null ? formatTime(markedOut) : "--:--:--"}
            </p>
        </div>
      </section>

      {/* Section: Timeline - Always render */}
      <section style={sectionStyle}>
        {/* Pass activeVideo for disabled states in Timeline component if needed */}
        <Timeline clips={clips} videoDuration={activeVideo?.duration || 0} activeVideo={activeVideo} />
      </section>

      {/* Section 3: Build Project & Export - Always render */}
      <section style={sectionStyle}>
        <h2 style={{ color: "#eee", marginBottom: "16px" }}>3) Build Project & Export</h2>
        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <button
                onClick={handleBuildProject}
                style={(!activeVideoId || clips.length === 0 || buildProjectMutation.isPending) ? disabledButtonStyle : buttonStyle}
                disabled={!activeVideoId || clips.length === 0 || buildProjectMutation.isPending}
            >
                {buildProjectMutation.isPending ? "Building..." : "Build .osp Project"}
            </button>
            <button
                onClick={handleStartExport}
                style={(!activeVideoId || clips.length === 0 || startExportMutation.isPending) ? disabledButtonStyle : buttonStyle}
                disabled={!activeVideoId || clips.length === 0 || startExportMutation.isPending}
            >
                {startExportMutation.isPending ? "Starting Export..." : "Start Export"}
            </button>
        </div>
        
        {exportId && (
          <div style={{ marginTop: "24px", padding: "12px", border: "1px dashed #666", borderRadius: "4px", backgroundColor: "#333" }}>
            <h3 style={{ color: "#eee", marginBottom: "8px" }}>Export Status: {exportStatus.status}</h3>
            <div style={{ width: "100%", height: "10px", backgroundColor: "#555", borderRadius: "5px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${exportStatus.progress}%`,
                  height: "100%",
                  backgroundColor: exportStatus.status === "completed" ? "#4CAF50" : (exportStatus.status === "error" ? "#f44336" : "#007bff"),
                  transition: "width 0.3s ease-in-out",
                }}
              />
            </div>
            <p style={{ marginTop: "8px" }}>Progress: {exportStatus.progress}%</p>
            {exportStatus.error_message && (
              <p style={{ color: "#f44336", marginTop: "8px" }}>Error: {exportStatus.error_message}</p>
            )}
            {exportStatus.download_url && exportStatus.status === "completed" && (
              <p style={{ marginTop: "16px" }}>
                <a href={exportStatus.download_url} download style={{ color: "#4CAF50", textDecoration: "none", fontWeight: "bold" }}>
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