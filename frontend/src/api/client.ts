export type VideoOut = {
  id: string;
  filename: string;
  path: string;
  duration?: number | null;
  thumbnail_url?: string | null;
};

export type ClipOut = {
  id: string;
  video_id: string;
  start_time: number;
  end_time: number;
  order_index: number;
};

export type ExportOut = {
  id: string;
  video_id: string;
  status: "queued" | "processing" | "completed" | "error";
  progress: number;
  download_url?: string | null;
};

export async function uploadVideo(file: File): Promise<VideoOut> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/videos/upload", { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getVideo(id: string): Promise<VideoOut> {
  const res = await fetch(`/api/videos/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function markClip(input: {
  video_id: string;
  start_time: number;
  end_time: number;
  order_index?: number;
}): Promise<ClipOut> {
  const res = await fetch(`/api/clips/mark`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_index: 0, ...input })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listClips(video_id: string): Promise<ClipOut[]> {
  const res = await fetch(`/api/clips/${video_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateClip(clip_id: string, input: {
  video_id: string;
  start_time: number;
  end_time: number;
  order_index?: number;
}): Promise<ClipOut> {
  const res = await fetch(`/api/clips/${clip_id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_index: 0, ...input })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteClip(clip_id: string): Promise<{ ok: boolean }> {
  const res = await fetch(`/api/clips/${clip_id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function buildProject(video_id: string): Promise<{ video_id: string; osp: string }> {
  const fd = new FormData();
  fd.append("video_id", video_id);
  const res = await fetch(`/api/projects/build`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startExport(video_id: string): Promise<ExportOut> {
  const res = await fetch(`/api/exports/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_id })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type ExportStatus = {
  id: string;
  status: "queued" | "processing" | "completed" | "error";
  progress: number;
  download_url?: string | null;
  error_message?: string | null;
};

export async function getExportStatus(export_id: string): Promise<ExportStatus> {
  const res = await fetch(`/api/exports/${export_id}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function openExportWebSocket(export_id: string, onMessage: (s: ExportStatus) => void): WebSocket {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/exports/${export_id}`);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch {}
  };
  // simple keepalive
  ws.onopen = () => setInterval(() => ws.readyState === 1 && ws.send("ping"), 15000);
  return ws;
}
