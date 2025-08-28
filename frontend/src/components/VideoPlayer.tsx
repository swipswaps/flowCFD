import React, { useEffect, useRef } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

interface VideoPlayerProps {
  options: any;
  src?: { src: string; type: string; };
  onReady: (player: any) => void;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({ options, src, onReady }) => {
  const videoNode = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<any>(null);

  useEffect(() => {
    // Only initialize the player if the video node exists and there's a source
    if (videoNode.current && !playerRef.current && src) {
      playerRef.current = videojs(videoNode.current, options, () => {
        onReady(playerRef.current);
      });
    }

    // If the source changes, update it
    if (playerRef.current && src) {
      playerRef.current.src(src);
    }
  }, [options, src, onReady]);

  // Dispose on unmount
  useEffect(() => {
    const player = playerRef.current;
    return () => {
      if (player && !player.isDisposed()) {
        player.dispose();
        playerRef.current = null;
      }
    };
  }, []);

  // Don't render the video element until there's a source to play
  if (!src) {
    return (
      <div className="flex items-center justify-center bg-black aspect-video">
        <p className="text-slate-400">Upload a video to begin</p>
      </div>
    );
  }

  return (
    <div data-vjs-player>
      <video ref={videoNode} className="video-js vjs-big-play-centered" />
    </div>
  );
};

export default VideoPlayer;
