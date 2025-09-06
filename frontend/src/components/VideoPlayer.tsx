import React, { useRef, useEffect, useCallback } from "react";
import ReactPlayer from "react-player/lazy";
import toast from "react-hot-toast";
import { useEditorStore } from "../stores/editorStore";
import { formatTime } from "../utils/time";

interface VideoPlayerProps {
  videoUrl: string;
  videoDuration: number;
}

export default function VideoPlayer({ videoUrl, videoDuration }: VideoPlayerProps) {
  const playerRef = useRef<ReactPlayer>(null);
  const {
    playerCurrentTime,
    setPlayerCurrentTime,
    setPlayerDuration,
    isPlaying,
    setIsPlaying,
    markedIn,
    setMarkedIn,
    markedOut,
    setMarkedOut,
    clearMarks,
  } = useEditorStore();

  useEffect(() => {
    console.log("VideoPlayer: videoUrl received:", videoUrl);
  }, [videoUrl]);

  const handleProgress = useCallback((state: { playedSeconds: number }) => {
    setPlayerCurrentTime(state.playedSeconds);
  }, [setPlayerCurrentTime]);

  const handleDuration = useCallback((duration: number) => {
    setPlayerDuration(duration);
  }, [setPlayerDuration]);

  const handleSeek = useCallback((time: number) => {
    if (playerRef.current) {
      playerRef.current.seekTo(time, 'seconds');
      setPlayerCurrentTime(time);
    }
  }, [setPlayerCurrentTime]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!videoUrl) return; // Only enable shortcuts if a video is loaded
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return; // Don't trigger shortcuts if typing in an input field
    }

    const currentTime = playerRef.current?.getCurrentTime() || 0;
    
    switch (e.key) {
      case ' ': // Spacebar for play/pause
        e.preventDefault(); // Prevent page scrolling
        setIsPlaying(!isPlaying);
        break;
      case 'i': // Mark In
      case 'I':
        setMarkedIn(currentTime);
        toast.success(`IN marked at ${formatTime(currentTime)}`);
        break;
      case 'o': // Mark Out
      case 'O':
        if (markedIn !== null && currentTime <= markedIn) {
          toast.error("OUT point must be after IN point.");
          return;
        }
        setMarkedOut(currentTime);
        toast.success(`OUT marked at ${formatTime(currentTime)}`);
        break;
      case 'j': // Seek backward 5 seconds
      case 'J':
        handleSeek(Math.max(0, currentTime - 5));
        break;
      case 'l': // Seek forward 5 seconds
      case 'L':
        handleSeek(Math.min(videoDuration, currentTime + 5));
        break;
      case 'k': // Clear marks
      case 'K':
        clearMarks();
        toast("IN/OUT marks cleared.");
        break;
      default:
        break;
    }
  }, [videoUrl, isPlaying, setIsPlaying, setMarkedIn, setMarkedOut, markedIn, handleSeek, videoDuration, clearMarks]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <div style={{ width: "100%", maxWidth: "800px", margin: "0 auto" }}>
      <div style={{ position: "relative", paddingTop: "56.25%" }}>
        {videoUrl ? (
          <ReactPlayer
            ref={playerRef}
            url={videoUrl}
            playing={isPlaying}
            controls={true}
            width="100%"
            height="100%"
            style={{ position: "absolute", top: 0, left: 0 }}
            onProgress={handleProgress}
            onDuration={handleDuration}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            progressInterval={100}
            config={{
              file: {
                attributes: {
                  controlsList: 'nofullscreen',
                  type: 'video/mp4' // Explicitly set the MIME type here
                }
              }
            }}
            onError={(e) => console.error("ReactPlayer Error:", e)}
          />
        ) : (
          <div style={{ 
            position: "absolute", top: 0, left: 0, width: "100%", height: "100%",
            backgroundColor: "#444", display: "flex", justifyContent: "center", alignItems: "center",
            color: "#eee", fontSize: "1.2em", border: "1px dashed #777", borderRadius: "8px"
          }}>
            Upload a video file above to begin editing.
          </div>
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px", padding: "8px 0" }}>
        <span>Current: {formatTime(playerCurrentTime)} / Duration: {formatTime(videoDuration)}</span>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={() => setIsPlaying(!isPlaying)} disabled={!videoUrl}>
            {isPlaying ? "Pause" : "Play"}
          </button>
          <button onClick={() => handleSeek(Math.max(0, playerCurrentTime - 5))} disabled={!videoUrl}>-5s</button>
          <button onClick={() => handleSeek(Math.min(videoDuration, playerCurrentTime + 5))} disabled={!videoUrl}>+5s</button>
          <button onClick={() => { setMarkedIn(playerCurrentTime); toast.success(`IN marked at ${formatTime(playerCurrentTime)}`); }} disabled={!videoUrl}>
            Mark IN (I)
          </button>
          <button onClick={() => { 
            if (markedIn !== null && playerCurrentTime <= markedIn) {
              toast.error("OUT point must be after IN point.");
              return;
            }
            setMarkedOut(playerCurrentTime); 
            toast.success(`OUT marked at ${formatTime(playerCurrentTime)}`); 
          }} disabled={!videoUrl}>
            Mark OUT (O)
          </button>
          <button onClick={clearMarks} disabled={!videoUrl}>Clear Marks (K)</button>
        </div>
      </div>

      <div style={{ width: "100%", height: "10px", background: "#333", position: "relative", borderRadius: "5px", overflow: "hidden" }}>
        {videoUrl && videoDuration > 0 && (
          <>
            {markedIn !== null && (
              <div
                style={{
                  position: "absolute",
                  left: `${(markedIn / videoDuration) * 100}%`,
                  width: "2px",
                  height: "100%",
                  background: "blue",
                  zIndex: 2,
                }}
                title={`IN: ${formatTime(markedIn)}`}
              />
            )}
            {markedOut !== null && (
              <div
                style={{
                  position: "absolute",
                  left: `${(markedOut / videoDuration) * 100}%`,
                  width: "2px",
                  height: "100%",
                  background: "red",
                  zIndex: 2,
                }}
                title={`OUT: ${formatTime(markedOut)}`}
              />
            )}
            {markedIn !== null && markedOut !== null && markedIn < markedOut && (
              <div
                style={{
                  position: "absolute",
                  left: `${(markedIn / videoDuration) * 100}%`,
                  width: `${((markedOut - markedIn) / videoDuration) * 100}%`,
                  height: "100%",
                  background: "rgba(0, 255, 0, 0.3)",
                  zIndex: 1,
                }}
              />
            )}
            <div
              style={{
                position: "absolute",
                left: 0,
                width: `${(playerCurrentTime / videoDuration) * 100}%`,
                height: "100%",
                background: "white",
                zIndex: 0,
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}