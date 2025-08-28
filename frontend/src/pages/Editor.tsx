import React, { useRef, useState, useCallback, useEffect, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useHotkeys } from "react-hotkeys-hook";
import {
  uploadVideo, VideoOut,
  markClip, listClips, ClipOut,
  buildProject, startExport, getExportStatus, openExportWebSocket
} from "../api/client";
import VideoPlayer from "../components/VideoPlayer";

// --- Utility Functions ---

// Snaps a time in seconds to the nearest frame, assuming a 29.97 FPS rate.
const snapToFrame = (time: number, fps = 29.97): number => {
  const frameDuration = 1 / fps;
  const frameNumber = Math.round(time / frameDuration);
  return frameNumber * frameDuration;
};

const formatTime = (time: number) => {
  const date = new Date(0);
  date.setSeconds(time);
  return date.toISOString().substr(11, 12);
};

// --- Main Component ---

export default function Editor() {
  const [video, setVideo] = useState<VideoOut | null>(null);
  const [clips, setClips] = useState<ClipOut[]>([]);
  const [status, setStatus] = useState({ progress: 0, status: "idle", download_url: null as string | null | undefined, error_message: null as string | null | undefined });
  const [inPoint, setInPoint] = useState<number>(0);
  const [outPoint, setOutPoint] = useState<number>(0);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  
  const playerRef = useRef<any>(null);
  const qc = useQueryClient();

  // --- Mutations ---

  const upload = useMutation({
    mutationFn: uploadVideo,
    onSuccess: (v) => {
      setVideo(v);
      setVideoUrl(`/uploads/${v.path.split('/').pop()}`);
    },
  });

  const refreshClips = useCallback(async () => {
    if (!video) return;
    try {
      const data = await listClips(video.id);
      setClips(data);
    } catch (error) {
      console.error("Failed to refresh clips:", error);
    }
  }, [video]);

  useEffect(() => { void refreshClips(); }, [refreshClips]);

  const addClipMutation = useMutation({
    mutationFn: (newClip: { video_id: string; start_time: number; end_time: number; order_index: number; }) => markClip(newClip),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clips', video?.id] });
      refreshClips();
    },
  });

  const buildMutation = useMutation({
    mutationFn: (videoId: string) => buildProject(videoId),
  });

  const exportMutation = useMutation({
    mutationFn: (videoId: string) => startExport(videoId),
    onSuccess: (exp) => {
      setStatus({ ...exp, error_message: null });
      const ws = openExportWebSocket(exp.id, (s) => setStatus({ ...s, error_message: s.error_message }));
      const timer = setInterval(async () => {
        const s = await getExportStatus(exp.id);
        setStatus({ ...s, error_message: s.error_message });
        if (s.status === "completed" || s.status === "error") clearInterval(timer);
      }, 3000);
      return () => { ws.close(); clearInterval(timer); };
    },
  });

  // --- Handlers ---

  const handleSetInPoint = () => {
    if (!playerRef.current) return;
    const currentTime = playerRef.current.currentTime();
    setInPoint(snapToFrame(currentTime));
  };

  const handleSetOutPoint = () => {
    if (!playerRef.current) return;
    const currentTime = playerRef.current.currentTime();
    setOutPoint(snapToFrame(currentTime));
  };

  const handleMarkClip = () => {
    if (!video || outPoint <= inPoint) return;
    addClipMutation.mutate({ video_id: video.id, start_time: inPoint, end_time: outPoint, order_index: clips.length });
  };
  
  const handleBuild = () => video && buildMutation.mutate(video.id);
  const handleExport = () => video && exportMutation.mutate(video.id);

  // --- Hotkeys ---

  useHotkeys('space, k', () => playerRef.current?.paused() ? playerRef.current?.play() : playerRef.current?.pause(), { preventDefault: true });
  useHotkeys('j', () => playerRef.current && (playerRef.current.currentTime(playerRef.current.currentTime() - 5)));
  useHotkeys('l', () => playerRef.current && (playerRef.current.currentTime(playerRef.current.currentTime() + 5)));
  useHotkeys('i', handleSetInPoint);
  useHotkeys('o', handleSetOutPoint);

  // --- Player Setup ---
  const handlePlayerReady = useCallback((player: any) => {
    playerRef.current = player;
  }, []);

  const videoJsOptions = useMemo(() => ({
    autoplay: false,
    controls: true,
    responsive: true,
    fluid: true,
  }), []);

  return (
    <div className="container mx-auto p-4">
      <header className="text-center my-6"><h1 className="text-4xl font-bold">CapCut-Lite Editor</h1></header>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <div className="w-full bg-black rounded-lg">
            <VideoPlayer 
              options={videoJsOptions} 
              onReady={handlePlayerReady} 
              src={videoUrl ? { src: videoUrl, type: 'video/mp4' } : undefined}
            />
          </div>
          <div className="bg-slate-800 p-4 my-4 rounded-lg">
            <h3 className="text-lg font-semibold mb-3">Clip Controls</h3>
            <div className="flex items-center gap-4">
              <button onClick={handleSetInPoint} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-md font-semibold">Mark IN (I)</button>
              <div className="font-mono bg-slate-700 px-4 py-2 rounded-md text-lg">{formatTime(inPoint)}</div>
              <button onClick={handleSetOutPoint} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-md font-semibold">Mark OUT (O)</button>
              <div className="font-mono bg-slate-700 px-4 py-2 rounded-md text-lg">{formatTime(outPoint)}</div>
              <button onClick={handleMarkClip} disabled={!video || outPoint <= inPoint || addClipMutation.isPending} className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
                {addClipMutation.isPending ? 'Adding...' : 'Add Clip'}
              </button>
            </div>
            {addClipMutation.isError && <div className="mt-2 text-red-400">Error: {addClipMutation.error.message}</div>}
          </div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg">
          <h2 className="text-2xl font-semibold mb-4">Project</h2>
          <section>
            <h3 className="text-lg font-semibold mb-2">1. Upload Video</h3>
            <input type="file" accept="video/*" disabled={upload.isPending} className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); }} />
            {upload.isPending && <div className="mt-2 text-slate-400 animate-pulse">Uploading...</div>}
            {upload.isError && <div className="mt-2 text-red-400 font-semibold" data-testid="upload-error">Error: {upload.error.message}</div>}
            {upload.isSuccess && video && <div className="mt-2 text-green-400" data-testid="upload-success"><b>{video.filename}</b> ({video.duration?.toFixed(2)}s)</div>}
          </section>
          <section className="mt-6">
            <h3 className="text-lg font-semibold mb-2">2. Clips</h3>
            <ul className="h-48 overflow-y-auto pr-2">
              {clips.length === 0 && <li className="text-slate-400">No clips added yet.</li>}
              {clips.map((c) => <li key={c.id} className="font-mono bg-slate-700 p-2 rounded-md mb-2">#{c.order_index} {formatTime(c.start_time)} → {formatTime(c.end_time)}</li>)}
            </ul>
          </section>
          <section className="mt-6">
            <h3 className="text-lg font-semibold mb-2">3. Build & Export</h3>
            <button onClick={handleBuild} disabled={!video || clips.length === 0 || buildMutation.isPending} className="w-full bg-indigo-600 hover:bg-indigo-700 py-2 rounded-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
              {buildMutation.isPending ? 'Building...' : 'Build Project (.osp)'}
            </button>
            {buildMutation.isSuccess && <div className="mt-2 text-green-400">Project built successfully!</div>}
            {buildMutation.isError && <div className="mt-2 text-red-400">Build failed: {buildMutation.error.message}</div>}
            
            <button onClick={handleExport} disabled={!buildMutation.isSuccess || exportMutation.isPending} className="w-full bg-purple-600 hover:bg-purple-700 py-2 rounded-md mt-2 font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
              {exportMutation.isPending ? `Exporting ${status.progress}%...` : 'Start Export'}
            </button>
            <div className="mt-2">
              {exportMutation.isPending && <div className="w-full bg-slate-700 rounded-full h-2.5"><div className="bg-purple-500 h-2.5 rounded-full" style={{ width: `${status.progress}%` }}></div></div>}
              {status.status === 'completed' && <a href={status.download_url!} download className="block w-full text-center bg-green-600 hover:bg-green-700 py-2 rounded-md mt-2 font-semibold">Download MP4</a>}
              {status.status === 'error' && <div className="mt-2 text-red-400">Export failed: {status.error_message}</div>}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
