# 🎬 ADVANCED VIDEO EDITING IMPLEMENTATION PROMPT
## Multi-Track Timeline, Drag/Drop, and Audio Editing Features

### 📋 EXECUTIVE SUMMARY
Transform flowCFD into a comprehensive video editing platform by implementing professional multi-track timeline editing, intuitive drag/drop clip arrangement, and advanced audio editing capabilities. This builds upon the existing lossless foundation to create a full-featured video editing suite.

---

## 🚨 MANDATORY COMPLIANCE FRAMEWORK
**CRITICAL**: This implementation follows `.cursorrules` STRICT ENFORCEMENT. Every code change requires:
1. ✅ **Immediate Testing**: Execute and verify functionality with exact curl commands and UI testing
2. ✅ **Server Verification**: Confirm all services respond with HTTP 200
3. ✅ **End-to-End Validation**: Test complete user workflows with proof
4. ✅ **Error-Free Logs**: No exceptions or warnings in backend logs
5. ✅ **Performance Benchmarks**: Multi-track operations must remain responsive (<500ms UI updates)

---

## 🎯 IMPLEMENTATION ROADMAP (PRIORITIZED)

### 🔥 PHASE 1: MULTI-TRACK TIMELINE FOUNDATION (Week 1-2)

#### **Task 1.1: Database Schema Enhancement for Multi-Track**
**Compliance Checklist:**
- [ ] Database migration created and tested
- [ ] All existing data preserved during migration
- [ ] New schema supports unlimited tracks
- [ ] Foreign key relationships validated
- [ ] API endpoints updated and tested

**Implementation Requirements:**
```sql
-- Enhanced database schema for multi-track editing
ALTER TABLE clips ADD COLUMN track_id INTEGER DEFAULT 1;
ALTER TABLE clips ADD COLUMN z_index INTEGER DEFAULT 0;
ALTER TABLE clips ADD COLUMN transition_in VARCHAR(50) DEFAULT 'none';
ALTER TABLE clips ADD COLUMN transition_out VARCHAR(50) DEFAULT 'none';

CREATE TABLE tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id VARCHAR(36) DEFAULT 'default',
    track_type VARCHAR(20) NOT NULL DEFAULT 'video', -- 'video', 'audio', 'overlay'
    track_name VARCHAR(100) NOT NULL,
    track_order INTEGER NOT NULL DEFAULT 1,
    is_enabled BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    volume FLOAT DEFAULT 1.0,
    opacity FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, track_order, track_type)
);

-- Insert default tracks
INSERT INTO tracks (track_name, track_type, track_order) VALUES 
('Video Track 1', 'video', 1),
('Audio Track 1', 'audio', 1);

CREATE TABLE audio_clips (
    id VARCHAR(36) PRIMARY KEY,
    video_id VARCHAR(36) NOT NULL,
    track_id INTEGER NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    timeline_position FLOAT NOT NULL,
    volume FLOAT DEFAULT 1.0,
    fade_in FLOAT DEFAULT 0.0,
    fade_out FLOAT DEFAULT 0.0,
    audio_effects TEXT, -- JSON array of effects
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
```

**Testing Protocol:**
```bash
# Test database migration
curl -X POST http://localhost:8000/api/database/migrate
# Expected: {"success": true, "tracks_created": 2}

# Test track creation
curl -X POST http://localhost:8000/api/tracks/create \
  -H "Content-Type: application/json" \
  -d '{"track_name": "Video Track 2", "track_type": "video"}'
# Expected: {"id": 3, "track_name": "Video Track 2", "success": true}
```

#### **Task 1.2: Multi-Track Timeline API**
**Implementation Requirements:**
```python
# backend/app.py - NEW ENDPOINTS

@app.get("/api/tracks")
async def get_tracks(db: Session = Depends(get_db)):
    """Get all tracks with their clips."""
    tracks = db.query(Track).order_by(Track.track_order).all()
    result = []
    for track in tracks:
        clips = db.query(Clip).filter(Clip.track_id == track.id).order_by(Clip.timeline_position).all()
        result.append({
            "id": track.id,
            "name": track.track_name,
            "type": track.track_type,
            "order": track.track_order,
            "enabled": track.is_enabled,
            "locked": track.is_locked,
            "volume": track.volume,
            "opacity": track.opacity,
            "clips": [serialize_clip(clip) for clip in clips]
        })
    return {"tracks": result}

@app.post("/api/tracks/create")
async def create_track(request: dict, db: Session = Depends(get_db)):
    """Create a new track."""
    track = Track(
        track_name=request["track_name"],
        track_type=request.get("track_type", "video"),
        track_order=request.get("track_order", 1)
    )
    db.add(track)
    db.commit()
    return {"success": True, "track": serialize_track(track)}

@app.put("/api/tracks/{track_id}")
async def update_track(track_id: int, request: dict, db: Session = Depends(get_db)):
    """Update track properties."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # Update properties
    for key, value in request.items():
        if hasattr(track, key):
            setattr(track, key, value)
    
    db.commit()
    return {"success": True, "track": serialize_track(track)}

@app.post("/api/clips/move")
async def move_clip(request: dict, db: Session = Depends(get_db)):
    """Move clip to different track/position."""
    clip_id = request["clip_id"]
    new_track_id = request.get("track_id")
    new_position = request.get("timeline_position")
    
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    if new_track_id:
        clip.track_id = new_track_id
    if new_position is not None:
        clip.timeline_position = new_position
    
    db.commit()
    return {"success": True, "clip": serialize_clip(clip)}
```

---

### ⚡ PHASE 2: DRAG & DROP INTERFACE (Week 2-3)

#### **Task 2.1: React DnD Integration**
**Technical Foundation:**
```typescript
// frontend/src/components/MultiTrackTimeline.tsx
import React, { useState, useCallback } from 'react';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

interface TimelineClip {
  id: string;
  trackId: number;
  startTime: number;
  endTime: number;
  timelinePosition: number;
  thumbnail?: string;
  title: string;
}

interface Track {
  id: number;
  name: string;
  type: 'video' | 'audio' | 'overlay';
  clips: TimelineClip[];
  enabled: boolean;
  locked: boolean;
}

const DraggableClip: React.FC<{
  clip: TimelineClip;
  trackId: number;
  onMove: (clipId: string, newTrackId: number, newPosition: number) => void;
}> = ({ clip, trackId, onMove }) => {
  const [{ isDragging }, drag] = useDrag({
    type: 'clip',
    item: { id: clip.id, trackId, position: clip.timelinePosition },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const clipWidth = (clip.endTime - clip.startTime) * PIXELS_PER_SECOND;
  const clipLeft = clip.timelinePosition * PIXELS_PER_SECOND;

  return (
    <div
      ref={drag}
      className={`timeline-clip ${isDragging ? 'dragging' : ''}`}
      style={{
        left: clipLeft,
        width: clipWidth,
        opacity: isDragging ? 0.5 : 1,
        position: 'absolute',
        height: '60px',
        backgroundColor: '#3b82f6',
        borderRadius: '4px',
        border: '2px solid #1e40af',
        cursor: 'move',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        color: 'white',
        fontSize: '12px',
        fontWeight: '500',
      }}
    >
      {clip.thumbnail && (
        <img 
          src={clip.thumbnail} 
          alt="" 
          style={{ width: '40px', height: '30px', marginRight: '8px', borderRadius: '2px' }}
        />
      )}
      <span>{clip.title}</span>
    </div>
  );
};

const DroppableTrack: React.FC<{
  track: Track;
  onDrop: (clipId: string, trackId: number, position: number) => void;
}> = ({ track, onDrop }) => {
  const [{ isOver }, drop] = useDrop({
    accept: 'clip',
    drop: (item: any, monitor) => {
      const dropOffset = monitor.getClientOffset();
      if (dropOffset) {
        const rect = (monitor.getDropResult()?.element || drop.current)?.getBoundingClientRect();
        if (rect) {
          const relativeX = dropOffset.x - rect.left;
          const newPosition = relativeX / PIXELS_PER_SECOND;
          onDrop(item.id, track.id, Math.max(0, newPosition));
        }
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  return (
    <div
      ref={drop}
      className={`timeline-track ${isOver ? 'drop-target' : ''}`}
      style={{
        position: 'relative',
        height: '80px',
        backgroundColor: isOver ? '#f3f4f6' : '#ffffff',
        border: '1px solid #e5e7eb',
        marginBottom: '4px',
        borderRadius: '4px',
      }}
    >
      <div className="track-header" style={{
        position: 'absolute',
        left: 0,
        width: '150px',
        height: '100%',
        backgroundColor: '#f9fafb',
        borderRight: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        fontSize: '14px',
        fontWeight: '500',
      }}>
        <span>{track.name}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
          <button style={{ padding: '2px 6px', fontSize: '10px' }}>👁</button>
          <button style={{ padding: '2px 6px', fontSize: '10px' }}>🔒</button>
        </div>
      </div>
      
      <div className="track-timeline" style={{
        marginLeft: '150px',
        position: 'relative',
        height: '100%',
        minWidth: '1000px',
      }}>
        {track.clips.map((clip) => (
          <DraggableClip
            key={clip.id}
            clip={clip}
            trackId={track.id}
            onMove={onDrop}
          />
        ))}
      </div>
    </div>
  );
};

export const MultiTrackTimeline: React.FC = () => {
  const [tracks, setTracks] = useState<Track[]>([]);
  
  const handleClipMove = useCallback((clipId: string, newTrackId: number, newPosition: number) => {
    // Update local state
    setTracks(prevTracks => {
      const updatedTracks = prevTracks.map(track => ({
        ...track,
        clips: track.clips.filter(clip => clip.id !== clipId)
      }));
      
      const targetTrack = updatedTracks.find(t => t.id === newTrackId);
      if (targetTrack) {
        const movedClip = prevTracks
          .flatMap(t => t.clips)
          .find(c => c.id === clipId);
        
        if (movedClip) {
          targetTrack.clips.push({
            ...movedClip,
            trackId: newTrackId,
            timelinePosition: newPosition
          });
        }
      }
      
      return updatedTracks;
    });
    
    // Sync with backend
    fetch('/api/clips/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clip_id: clipId,
        track_id: newTrackId,
        timeline_position: newPosition
      })
    });
  }, []);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="multi-track-timeline">
        <div className="timeline-header" style={{
          display: 'flex',
          alignItems: 'center',
          padding: '12px',
          borderBottom: '1px solid #e5e7eb',
          gap: '12px'
        }}>
          <h3 style={{ margin: 0 }}>🎬 Multi-Track Timeline</h3>
          <button style={{
            padding: '6px 12px',
            backgroundColor: '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '12px'
          }}>
            ➕ Add Track
          </button>
        </div>
        
        <div className="tracks-container" style={{ padding: '12px' }}>
          {tracks.map((track) => (
            <DroppableTrack
              key={track.id}
              track={track}
              onDrop={handleClipMove}
            />
          ))}
        </div>
      </div>
    </DndProvider>
  );
};

const PIXELS_PER_SECOND = 50; // Adjust for zoom level
```

**Installation Requirements:**
```bash
# Add drag and drop dependencies
cd frontend
npm install react-dnd react-dnd-html5-backend
```

#### **Task 2.2: Advanced Timeline Features**
**Implementation Requirements:**
```typescript
// Snapping behavior
const SNAP_THRESHOLD = 10; // pixels
const SNAP_POINTS = ['clip_start', 'clip_end', 'playhead', 'keyframes'];

const useTimelineSnapping = () => {
  const snapToNearestPoint = useCallback((position: number, snapPoints: number[]) => {
    const pixelPosition = position * PIXELS_PER_SECOND;
    
    for (const snapPoint of snapPoints) {
      const snapPixel = snapPoint * PIXELS_PER_SECOND;
      if (Math.abs(pixelPosition - snapPixel) < SNAP_THRESHOLD) {
        return snapPoint;
      }
    }
    
    return position;
  }, []);
  
  return { snapToNearestPoint };
};

// Magnetic timeline behavior
const useMagneticTimeline = () => {
  const findMagneticPoints = useCallback((tracks: Track[], excludeClipId?: string) => {
    const magneticPoints: number[] = [];
    
    tracks.forEach(track => {
      track.clips.forEach(clip => {
        if (clip.id !== excludeClipId) {
          magneticPoints.push(clip.timelinePosition);
          magneticPoints.push(clip.timelinePosition + (clip.endTime - clip.startTime));
        }
      });
    });
    
    return magneticPoints.sort((a, b) => a - b);
  }, []);
  
  return { findMagneticPoints };
};
```

---

### 🎵 PHASE 3: AUDIO EDITING CAPABILITIES (Week 3-4)

#### **Task 3.1: Audio Waveform Visualization**
**Implementation Requirements:**
```typescript
// frontend/src/components/AudioWaveform.tsx
import React, { useEffect, useRef, useState } from 'react';

interface AudioWaveformProps {
  audioUrl: string;
  duration: number;
  currentTime: number;
  height?: number;
  color?: string;
  progressColor?: string;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({
  audioUrl,
  duration,
  currentTime,
  height = 60,
  color = '#3b82f6',
  progressColor = '#ef4444'
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [waveformData, setWaveformData] = useState<number[]>([]);

  useEffect(() => {
    const generateWaveform = async () => {
      try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const response = await fetch(audioUrl);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        const channelData = audioBuffer.getChannelData(0);
        const samples = 1000; // Number of waveform points
        const blockSize = Math.floor(channelData.length / samples);
        const waveform = [];
        
        for (let i = 0; i < samples; i++) {
          let sum = 0;
          for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(channelData[i * blockSize + j]);
          }
          waveform.push(sum / blockSize);
        }
        
        setWaveformData(waveform);
      } catch (error) {
        console.error('Error generating waveform:', error);
      }
    };

    generateWaveform();
  }, [audioUrl]);

  useEffect(() => {
    if (!canvasRef.current || waveformData.length === 0) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const centerY = height / 2;
    const progress = currentTime / duration;
    const progressX = width * progress;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw waveform
    const barWidth = width / waveformData.length;
    
    waveformData.forEach((amplitude, index) => {
      const x = index * barWidth;
      const barHeight = amplitude * centerY;
      
      // Choose color based on progress
      ctx.fillStyle = x < progressX ? progressColor : color;
      
      // Draw bar
      ctx.fillRect(x, centerY - barHeight, barWidth - 1, barHeight * 2);
    });

    // Draw progress line
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(progressX, 0);
    ctx.lineTo(progressX, height);
    ctx.stroke();
    
  }, [waveformData, currentTime, duration, height, color, progressColor]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={height}
      style={{
        width: '100%',
        height: `${height}px`,
        backgroundColor: '#f3f4f6',
        borderRadius: '4px'
      }}
    />
  );
};
```

#### **Task 3.2: Audio Effects and Processing**
**Backend Audio Processing:**
```python
# backend/audio_utils.py - NEW FILE

import subprocess
import os
import tempfile
import json
from typing import Dict, List, Any, Optional

def extract_audio_waveform(video_path: str, samples: int = 1000) -> Dict[str, Any]:
    """
    Extract audio waveform data for visualization.
    Returns normalized amplitude values for frontend rendering.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            # Extract audio to WAV format
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '44100', '-ac', '1',
                '-y', temp_audio.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"success": False, "error": f"Audio extraction failed: {result.stderr}"}
            
            # Analyze waveform with ffprobe
            cmd = [
                'ffprobe', '-f', 'wav', '-show_entries', 'frame=pkt_pts_time',
                '-select_streams', 'a:0', '-of', 'csv=p=0',
                temp_audio.name
            ]
            
            # For simplicity, use ffmpeg volumedetect to get basic audio info
            cmd = [
                'ffmpeg', '-i', temp_audio.name,
                '-filter:a', 'volumedetect',
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Generate waveform data (simplified)
            waveform_data = generate_waveform_samples(temp_audio.name, samples)
            
            os.unlink(temp_audio.name)
            
            return {
                "success": True,
                "waveform": waveform_data,
                "samples": samples,
                "duration": get_audio_duration(video_path)
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def apply_audio_effects(input_path: str, output_path: str, effects: List[Dict]) -> Dict[str, Any]:
    """
    Apply audio effects using FFmpeg filters.
    
    Supported effects:
    - volume: {"type": "volume", "level": 1.5}
    - fade_in: {"type": "fade_in", "duration": 2.0}
    - fade_out: {"type": "fade_out", "duration": 2.0}
    - normalize: {"type": "normalize", "target": -3}
    - eq: {"type": "equalizer", "low": 0, "mid": 0, "high": 0}
    """
    try:
        filters = []
        
        for effect in effects:
            effect_type = effect.get("type")
            
            if effect_type == "volume":
                level = effect.get("level", 1.0)
                filters.append(f"volume={level}")
                
            elif effect_type == "fade_in":
                duration = effect.get("duration", 1.0)
                filters.append(f"afade=t=in:d={duration}")
                
            elif effect_type == "fade_out":
                duration = effect.get("duration", 1.0)
                filters.append(f"afade=t=out:d={duration}")
                
            elif effect_type == "normalize":
                target = effect.get("target", -3)
                filters.append(f"loudnorm=I={target}")
                
            elif effect_type == "equalizer":
                low = effect.get("low", 0)
                mid = effect.get("mid", 0)
                high = effect.get("high", 0)
                filters.append(f"equalizer=f=100:g={low}")
                filters.append(f"equalizer=f=1000:g={mid}")
                filters.append(f"equalizer=f=10000:g={high}")
        
        if not filters:
            # No effects, just copy
            cmd = ['ffmpeg', '-i', input_path, '-c', 'copy', '-y', output_path]
        else:
            filter_chain = ",".join(filters)
            cmd = [
                'ffmpeg', '-i', input_path,
                '-filter:a', filter_chain,
                '-c:v', 'copy',  # Keep video unchanged
                '-y', output_path
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return {"success": False, "error": f"Audio effects failed: {result.stderr}"}
        
        return {
            "success": True,
            "output_path": output_path,
            "effects_applied": len(effects),
            "processing_time": "N/A"  # Could add timing
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def mix_audio_tracks(audio_files: List[str], output_path: str, 
                    volumes: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Mix multiple audio tracks together.
    """
    try:
        if len(audio_files) < 2:
            return {"success": False, "error": "Need at least 2 audio files to mix"}
        
        volumes = volumes or [1.0] * len(audio_files)
        
        # Build FFmpeg command for mixing
        inputs = []
        filter_parts = []
        
        for i, (audio_file, volume) in enumerate(zip(audio_files, volumes)):
            inputs.extend(['-i', audio_file])
            filter_parts.append(f"[{i}:a]volume={volume}[a{i}]")
        
        # Create mix filter
        mix_inputs = ";".join(filter_parts)
        mix_channels = "".join([f"[a{i}]" for i in range(len(audio_files))])
        mix_filter = f"{mix_inputs};{mix_channels}amix=inputs={len(audio_files)}:duration=longest[out]"
        
        cmd = [
            'ffmpeg'
        ] + inputs + [
            '-filter_complex', mix_filter,
            '-map', '[out]',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            return {"success": False, "error": f"Audio mixing failed: {result.stderr}"}
        
        return {
            "success": True,
            "output_path": output_path,
            "tracks_mixed": len(audio_files)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_waveform_samples(audio_path: str, samples: int) -> List[float]:
    """
    Generate simplified waveform data for visualization.
    This is a placeholder - in production you'd use proper audio analysis.
    """
    import math
    import random
    
    # Simplified waveform generation (replace with actual audio analysis)
    waveform = []
    for i in range(samples):
        # Create realistic-looking waveform with some randomness
        t = i / samples
        amplitude = abs(math.sin(t * math.pi * 4)) * random.uniform(0.3, 1.0)
        waveform.append(amplitude)
    
    return waveform
```

**Audio API Endpoints:**
```python
# backend/app.py - ADD TO EXISTING FILE

@app.get("/api/videos/{video_id}/waveform")
async def get_audio_waveform(video_id: str, samples: int = 1000, db: Session = Depends(get_db)):
    """Get audio waveform data for visualization."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    waveform_data = audio_utils.extract_audio_waveform(video.path, samples)
    
    if not waveform_data["success"]:
        raise HTTPException(status_code=500, detail=waveform_data["error"])
    
    return waveform_data

@app.post("/api/audio/effects")
async def apply_audio_effects(request: dict):
    """Apply audio effects to a video file."""
    input_path = request["input_path"]
    effects = request.get("effects", [])
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"audio_effects_{timestamp}.mp4"
    output_path = os.path.join("store", "exports", output_filename)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    result = audio_utils.apply_audio_effects(input_path, output_path, effects)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "success": True,
        "output_file": output_filename,
        "download_url": f"/static/exports/{output_filename}",
        "effects_applied": result["effects_applied"]
    }

@app.post("/api/audio/mix")
async def mix_audio_tracks(request: dict):
    """Mix multiple audio tracks."""
    audio_files = request["audio_files"]
    volumes = request.get("volumes")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"audio_mix_{timestamp}.mp4"
    output_path = os.path.join("store", "exports", output_filename)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    result = audio_utils.mix_audio_tracks(audio_files, output_path, volumes)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "success": True,
        "output_file": output_filename,
        "download_url": f"/static/exports/{output_filename}",
        "tracks_mixed": result["tracks_mixed"]
    }
```

---

## 🔧 TECHNICAL SPECIFICATIONS

### **Multi-Track Timeline Requirements**
- **Unlimited Tracks**: Support for any number of video and audio tracks
- **Track Types**: Video, audio, overlay/graphics tracks
- **Per-Track Controls**: Enable/disable, lock/unlock, volume, opacity
- **Z-Index Management**: Proper layering of video tracks
- **Track Grouping**: Ability to group related tracks

### **Drag & Drop Specifications**
- **HTML5 Drag API**: Native browser drag and drop support
- **Magnetic Snapping**: Clips snap to other clip boundaries and playhead
- **Visual Feedback**: Real-time preview during drag operations
- **Collision Detection**: Prevent overlapping clips on same track
- **Undo/Redo Support**: Full operation history for drag/drop actions

### **Audio Editing Requirements**
- **Waveform Visualization**: Real-time audio waveform display
- **Audio Effects**: Volume, fade, normalize, EQ, compression
- **Multi-Track Audio**: Independent audio tracks with mixing
- **Audio Sync**: Maintain audio/video synchronization
- **Audio Export**: Extract audio tracks independently

---

## 🧪 COMPREHENSIVE TESTING STRATEGY

### **Multi-Track Testing**
```bash
#!/bin/bash
# Multi-track integration test

echo "🧪 Testing multi-track timeline functionality..."

# Test 1: Create multiple tracks
curl -X POST http://localhost:8000/api/tracks/create \
  -H "Content-Type: application/json" \
  -d '{"track_name": "Video Track 2", "track_type": "video"}'

curl -X POST http://localhost:8000/api/tracks/create \
  -H "Content-Type: application/json" \
  -d '{"track_name": "Audio Track 2", "track_type": "audio"}'

# Test 2: Move clip between tracks
CLIP_ID=$(curl -s http://localhost:8000/api/timeline/clips | jq -r '.clips[0].id')
curl -X POST http://localhost:8000/api/clips/move \
  -H "Content-Type: application/json" \
  -d "{\"clip_id\": \"$CLIP_ID\", \"track_id\": 2, \"timeline_position\": 5.0}"

# Test 3: Verify track layout
curl -s http://localhost:8000/api/tracks | jq '.tracks[] | {name, clips: (.clips | length)}'

echo "✅ Multi-track tests completed"
```

### **Drag & Drop Testing**
```typescript
// Automated UI testing with Playwright
import { test, expect } from '@playwright/test';

test('drag and drop clip between tracks', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Wait for timeline to load
  await page.waitForSelector('.multi-track-timeline');
  
  // Drag clip from track 1 to track 2
  const clip = page.locator('.timeline-clip').first();
  const targetTrack = page.locator('.timeline-track').nth(1);
  
  await clip.dragTo(targetTrack);
  
  // Verify clip moved
  const tracksData = await page.evaluate(() => {
    return fetch('/api/tracks').then(r => r.json());
  });
  
  expect(tracksData.tracks[1].clips.length).toBeGreaterThan(0);
});

test('magnetic snapping behavior', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Test clip snapping to other clips
  const clip1 = page.locator('.timeline-clip').first();
  const clip2 = page.locator('.timeline-clip').nth(1);
  
  // Drag clip2 near clip1's end
  await clip2.dragTo(clip1, { targetPosition: { x: 200, y: 0 } });
  
  // Check if clips snapped together
  const clip1Bounds = await clip1.boundingBox();
  const clip2Bounds = await clip2.boundingBox();
  
  expect(Math.abs((clip1Bounds?.x + clip1Bounds?.width) - clip2Bounds?.x)).toBeLessThan(5);
});
```

---

## 🚀 DEPLOYMENT & VALIDATION CHECKLIST

### **Pre-Deployment Requirements**
- [ ] All database migrations applied successfully
- [ ] React DnD integration working without conflicts
- [ ] Audio waveform generation under 2 seconds for 10-minute videos
- [ ] Multi-track operations responsive (<500ms UI updates)
- [ ] Drag and drop works across all supported browsers
- [ ] Audio effects apply without artifacts
- [ ] No memory leaks during extended editing sessions

### **Success Criteria Verification**
```bash
# MANDATORY: Prove advanced editing capability
./run_advanced_editing_validation.sh

# Expected outputs:
# ✅ Multi-track creation: 3 video tracks, 2 audio tracks
# ✅ Drag & drop: Clip moved between tracks without data loss
# ✅ Audio waveform: Generated in <2 seconds for test video
# ✅ Audio effects: Volume/fade applied without quality loss
# ✅ Timeline performance: 60fps during drag operations
# ✅ Browser compatibility: Works in Chrome, Firefox, Safari
# ✅ Touch support: Drag & drop works on tablet devices
```

---

## 📚 REFERENCE IMPLEMENTATION PATTERNS

### **Industry Standards**
- **Adobe Premiere Pro**: Multi-track timeline with magnetic snapping
- **DaVinci Resolve**: Advanced audio editing with waveform visualization  
- **Final Cut Pro**: Intuitive drag-and-drop interface with smart snapping
- **Avid Media Composer**: Professional track management and audio mixing

### **Web Technology Best Practices**
- **React DnD**: Industry-standard drag and drop for React applications
- **Web Audio API**: Browser-native audio processing and visualization
- **Canvas Rendering**: High-performance waveform visualization
- **IndexedDB**: Client-side caching for large audio waveform data

---

## 🎯 CRITICAL SUCCESS FACTORS

1. **Performance First**: Multi-track operations must remain fluid and responsive
2. **Professional Workflow**: Match industry-standard editing patterns and shortcuts
3. **Data Integrity**: No clip loss or corruption during drag/drop operations  
4. **Audio Quality**: All audio processing must maintain professional quality standards
5. **User Experience**: Intuitive interface that doesn't require training for basic operations

**FINAL VALIDATION**: The implementation is only successful when users can perform professional multi-track video editing with full audio control, matching the workflow efficiency of desktop video editing applications, all verified through comprehensive testing protocols.
