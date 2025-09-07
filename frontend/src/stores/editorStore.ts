import { create } from "zustand";
import { persist } from "zustand/middleware";

interface EditorState {
  playerCurrentTime: number;
  playerDuration: number;
  isPlaying: boolean;
  markedIn: number | null;
  markedOut: number | null;
  selectedClipId: string | null;
  activeVideoId: string | null;
  clipStartTime: number | null;
  clipEndTime: number | null;
  isClipMode: boolean;

  setPlayerCurrentTime: (time: number) => void;
  setPlayerDuration: (duration: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setMarkedIn: (time: number | null) => void;
  setMarkedOut: (time: number | null) => void;
  setSelectedClipId: (id: string | null) => void;
  setActiveVideoId: (id: string | null) => void;
  setClipMode: (start: number | null, end: number | null) => void;
  clearClipMode: () => void;
  clearMarks: () => void;
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set) => ({
      playerCurrentTime: 0,
      playerDuration: 0,
      isPlaying: false,
      markedIn: null,
      markedOut: null,
      selectedClipId: null,
      activeVideoId: null,
      clipStartTime: null,
      clipEndTime: null,
      isClipMode: false,

      setPlayerCurrentTime: (time) => set({ playerCurrentTime: time }),
      setPlayerDuration: (duration) => set({ playerDuration: duration }),
      setIsPlaying: (playing) => set({ isPlaying: playing }),
      setMarkedIn: (time) => set({ markedIn: time }),
      setMarkedOut: (time) => set({ markedOut: time }),
      setSelectedClipId: (id) => set({ selectedClipId: id }),
      setActiveVideoId: (id) => set({ activeVideoId: id }),
      setClipMode: (start, end) => set({ clipStartTime: start, clipEndTime: end, isClipMode: true }),
      clearClipMode: () => set({ clipStartTime: null, clipEndTime: null, isClipMode: false }),
      clearMarks: () => set({ markedIn: null, markedOut: null }),
    }),
    {
      name: "editor-store", // localStorage key
      partialize: (state) => ({
        activeVideoId: state.activeVideoId,
        markedIn: state.markedIn,
        markedOut: state.markedOut,
        selectedClipId: state.selectedClipId,
        playerDuration: state.playerDuration,
      }),
    }
  )
);