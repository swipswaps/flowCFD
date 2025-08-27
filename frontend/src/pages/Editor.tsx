import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  uploadVideo, VideoOut,
  markClip, listClips, ClipOut,
  buildProject, startExport, getExportStatus, openExportWebSocket
} from "../api/client";

export default function Editor() {
  const qc = useQueryClient();
  const [video, setVideo] = React.useState<VideoOut | null>(null);
  const [clips, setClips] = React.useState<ClipOut[]>([]);
  const [exportId, setExportId] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<{progress:number; status:string; download_url?:string|null}>({progress:0,status:"idle"});

  const upload = useMutation({
    mutationFn: uploadVideo,
    onSuccess: (v) => setVideo(v)
  });

  const refreshClips = React.useCallback(async () => {
    if (!video) return;
    const data = await listClips(video.id);
    setClips(data);
  }, [video]);

  React.useEffect(() => { void refreshClips(); }, [refreshClips]);

  const handleMark = async () => {
    if (!video) return;
    // Demo: mark a hardcoded 2s clip at 0..2 (replace with player currentTime IN/OUT)
    await markClip({ video_id: video.id, start_time: 0, end_time: 2, order_index: clips.length });
    await refreshClips();
  };

  const handleBuild = async () => {
    if (!video) return;
    await buildProject(video.id);
    alert("Project built (.osp)");
  };

  const handleExport = async () => {
    if (!video) return;
    const exp = await startExport(video.id);
    setExportId(exp.id);
    setStatus({progress: exp.progress, status: exp.status, download_url: exp.download_url});
    // WebSocket progress (fallback: poll)
    const ws = openExportWebSocket(exp.id, (s) => setStatus({progress: s.progress, status: s.status, download_url: s.download_url}));
    // also poll every 3s in case WS drops
    const timer = setInterval(async () => {
      const s = await getExportStatus(exp.id);
      setStatus({progress: s.progress, status: s.status, download_url: s.download_url});
      if (s.status === "completed" || s.status === "error") clearInterval(timer);
    }, 3000);
    // cleanup
    return () => { try { ws.close(); } catch {} clearInterval(timer); };
  };

  return (
    <div style={{ padding: 24, fontFamily: "ui-sans-serif, system-ui" }}>
      <h1>CapCut-Lite (MVP)</h1>

      <section style={{ marginTop: 16 }}>
        <h2>1) Upload</h2>
        <input type="file" accept="video/*" onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload.mutate(f);
        }} />
        {video && <div>Uploaded: <b>{video.filename}</b> (duration: {video.duration?.toFixed(2)}s)</div>}
      </section>

      <section style={{ marginTop: 16 }}>
        <h2>2) Mark Clips</h2>
        <button onClick={handleMark} disabled={!video}>Mark Demo Clip (0s–2s)</button>
        <ul>
          {clips.map((c) => (
            <li key={c.id}>#{c.order_index} {c.start_time.toFixed(3)} → {c.end_time.toFixed(3)} (id: {c.id})</li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 16 }}>
        <h2>3) Build Project</h2>
        <button onClick={handleBuild} disabled={!video || clips.length === 0}>Build .osp</button>
      </section>

      <section style={{ marginTop: 16 }}>
        <h2>4) Export</h2>
        <button onClick={handleExport} disabled={!video}>Start Export</button>
        <div style={{ marginTop: 8 }}>
          Status: {status.status} — {status.progress}%
        </div>
        {status.download_url && status.status === "completed" && (
          <div><a href={status.download_url} download>Download MP4</a></div>
        )}
      </section>
    </div>
  );
}
