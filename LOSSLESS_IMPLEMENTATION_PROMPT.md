# 🎯 LOSSLESS VIDEO EDITING IMPLEMENTATION PROMPT
## Professional-Grade Transformation with Mandatory Compliance Protocol

### 📋 EXECUTIVE SUMMARY
Transform flowCFD into a truly professional lossless video editing tool by implementing keyframe-aware cutting, smart encoding fallbacks, and industry-standard quality preservation techniques. Every implementation step MUST follow the strict .cursorrules compliance protocol with verifiable testing and proof of functionality.

---

## 🚨 MANDATORY COMPLIANCE FRAMEWORK
**CRITICAL**: This implementation follows `.cursorrules` STRICT ENFORCEMENT. Every code change requires:
1. ✅ **Immediate Testing**: Execute and verify functionality with exact curl commands
2. ✅ **Server Verification**: Confirm all services respond with HTTP 200
3. ✅ **End-to-End Validation**: Test complete user workflows with proof
4. ✅ **Error-Free Logs**: No exceptions or warnings in backend logs
5. ✅ **Rollback Readiness**: Verify rollback capability before major changes

---

## 🎯 IMPLEMENTATION ROADMAP (PRIORITIZED)

### 🔥 PHASE 1: CRITICAL LOSSLESS FOUNDATION (Week 1-2)

#### **Task 1.1: FFmpeg Keyframe Detection System**
**Compliance Checklist:**
- [ ] Code implementation completed
- [ ] Python imports verified (`subprocess`, `json`, `typing`)
- [ ] FFmpeg/FFprobe availability tested
- [ ] Unit tests created and passing
- [ ] Backend server started successfully
- [ ] API endpoint tested with curl
- [ ] No errors in logs

**Implementation Requirements:**
```python
# backend/ffmpeg_utils.py - NEW FUNCTIONS
def get_keyframes(video_path: str) -> List[float]:
    """
    Extract keyframe timestamps for lossless cutting.
    Based on FFmpeg official documentation and LosslessCut implementation.
    """
    # Implementation must handle:
    # - Invalid video files (return empty list)
    # - FFprobe command failures (log and return empty)
    # - Malformed timestamp data (skip invalid entries)
    # - Large video files (stream processing for memory efficiency)

def validate_lossless_compatibility(video_path: str) -> Dict[str, Any]:
    """
    Validate video format for lossless editing capability.
    Reference: FFmpeg documentation on stream copy limitations.
    """
    # Must check:
    # - Video codec compatibility (H.264, H.265, VP9, AV1)
    # - Audio codec compatibility (AAC, MP3, AC3, FLAC)
    # - Container format support (MP4, MKV, MOV)
    # - B-frame presence (affects lossless cutting)
    # - Variable frame rate detection

def find_nearest_keyframe(timestamp: float, keyframes: List[float], 
                         prefer_before: bool = True) -> float:
    """
    Find optimal keyframe for lossless cutting.
    Algorithm based on industry-standard video editing practices.
    """
```

**Testing Protocol:**
```bash
# MANDATORY: Test each function individually
curl -X POST http://localhost:8000/api/videos/analyze-keyframes \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test-video-id"}'

# Expected Response: {"keyframes": [0.0, 2.002, 4.004, ...], "count": 150}
```

#### **Task 1.2: Enhanced Clip Extraction with Lossless Priority**
**Implementation Requirements:**
```python
def extract_clip_lossless(src: str, start: float, end: float, out_path: str,
                         force_keyframe: bool = True, 
                         smart_cut: bool = False) -> Dict[str, Any]:
    """
    Lossless-first clip extraction with comprehensive fallback strategy.
    Based on LosslessCut methodology and FFmpeg best practices.
    """
    # Priority order (CRITICAL):
    # 1. Keyframe-aligned stream copy (truly lossless)
    # 2. Smart cut with minimal re-encoding
    # 3. High-quality re-encoding with original codec
    # 4. Fallback encoding with quality preservation
    
    # MUST return detailed metadata:
    return {
        "success": bool,
        "method_used": str,  # "stream_copy", "smart_cut", "re_encoded"
        "quality_preserved": bool,
        "keyframe_aligned": bool,
        "processing_time": float,
        "file_size": int,
        "warnings": List[str]
    }
```

**Mandatory Testing:**
```bash
# Test 1: Keyframe-aligned extraction (should be lossless)
curl -X POST http://localhost:8000/api/clips/extract \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test", "start": 2.002, "end": 6.006, "lossless": true}'

# Test 2: Non-keyframe extraction (should use smart cut)
curl -X POST http://localhost:8000/api/clips/extract \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test", "start": 1.5, "end": 5.7, "lossless": true}'

# Verify response includes quality metadata
```

---

### ⚡ PHASE 2: SMART CUTTING & UI ENHANCEMENT (Week 2-3)

#### **Task 2.1: Smart Cut Implementation**
**Technical Foundation:**
Based on FFmpeg segment muxer and LosslessCut's smart cutting algorithm:
```python
def extract_clip_smart_cut(src: str, start: float, end: float, out_path: str) -> bool:
    """
    Implement smart cutting for non-keyframe-aligned edits.
    Re-encodes only affected frames while preserving quality.
    Reference: FFmpeg segment muxer documentation.
    """
    # Algorithm:
    # 1. Find keyframes before/after cut points
    # 2. Extract keyframe-aligned segments with stream copy
    # 3. Re-encode only the precise cut segments
    # 4. Concatenate all segments losslessly
```

**Compliance Testing:**
```bash
# Test smart cut precision
curl -X POST http://localhost:8000/api/clips/smart-cut \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test", "start": 1.234, "end": 5.678}'

# Verify quality metrics in response
# Expected: PSNR > 45dB, SSIM > 0.99
```

#### **Task 2.2: Frontend Lossless Indicators**
**React Component Enhancements:**
```typescript
// frontend/src/components/LosslessIndicator.tsx
interface LosslessStatus {
  isLosslessCapable: boolean;
  keyframeAlignment: 'perfect' | 'adjusted' | 'reencoded';
  qualityPreservation: number; // 0-100%
  suggestedCuts: { start: number; end: number; }[];
}

// frontend/src/components/KeyframeTimeline.tsx
// Visual keyframe indicators on timeline
// Snap-to-keyframe functionality
// Lossless cut preview
```

**UI Testing Protocol:**
```bash
# Verify frontend communicates with lossless API
curl -X GET http://localhost:5173/api/videos/test/lossless-info

# Test keyframe visualization endpoint
curl -X GET http://localhost:8000/api/videos/test/keyframes \
  -H "Accept: application/json"
```

---

### 📊 PHASE 3: QUALITY ASSURANCE & MONITORING (Week 3-4)

#### **Task 3.1: Quality Metrics Implementation**
```python
def analyze_quality_loss(original: str, processed: str) -> Dict[str, float]:
    """
    Comprehensive quality analysis using FFmpeg filters.
    Reference: FFmpeg SSIM/PSNR filter documentation.
    """
    # Metrics to calculate:
    # - SSIM (Structural Similarity Index)
    # - PSNR (Peak Signal-to-Noise Ratio) 
    # - VMAF (Video Multimethod Assessment Fusion)
    # - File size comparison
    # - Bitrate preservation ratio

def generate_quality_report(processing_chain: List[Dict]) -> Dict:
    """
    Generate comprehensive quality preservation report.
    Track quality loss through entire editing pipeline.
    """
```

**Quality Validation Testing:**
```bash
# Test quality metrics endpoint
curl -X POST http://localhost:8000/api/quality/analyze \
  -H "Content-Type: application/json" \
  -d '{"original_id": "source", "processed_id": "result"}'

# Expected response includes SSIM, PSNR, VMAF scores
```

#### **Task 3.2: Advanced Concatenation with Quality Preservation**
```python
def concat_clips_lossless(clips: List[Dict], output: str, 
                         quality_target: str = "lossless") -> Dict:
    """
    Enhanced concatenation preserving maximum quality.
    Based on FFmpeg concat demuxer best practices.
    """
    # Quality targets:
    # - "lossless": Stream copy only, fail if impossible
    # - "near_lossless": Minimal quality loss (<1%)
    # - "high_quality": Optimized re-encoding if needed
    # - "fast": Prioritize speed over quality
```

---

## 🔧 TECHNICAL SPECIFICATIONS

### **FFmpeg Command Optimization**
Based on official FFmpeg documentation and industry best practices:

```bash
# Lossless keyframe-aligned extraction
ffmpeg -ss {keyframe_start} -i {input} -t {duration} -c copy -avoid_negative_ts make_zero {output}

# Smart cut with quality preservation
ffmpeg -ss {pre_keyframe} -i {input} -filter_complex \
  "[0:v]trim=start={precise_start}:end={precise_end}[v];[0:a]atrim=start={precise_start}:end={precise_end}[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium {output}

# Quality-preserving concatenation
ffmpeg -f concat -safe 0 -i {filelist} -c copy -movflags +faststart {output}
```

### **Database Schema Extensions**
```sql
-- Add lossless tracking to clips table
ALTER TABLE clips ADD COLUMN is_lossless BOOLEAN DEFAULT FALSE;
ALTER TABLE clips ADD COLUMN keyframe_aligned BOOLEAN DEFAULT FALSE;
ALTER TABLE clips ADD COLUMN quality_score FLOAT DEFAULT NULL;
ALTER TABLE clips ADD COLUMN processing_method VARCHAR(50) DEFAULT 'unknown';

-- Add quality metrics table
CREATE TABLE quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_clip_id VARCHAR(36) NOT NULL,
    target_clip_id VARCHAR(36) NOT NULL,
    ssim_score FLOAT,
    psnr_score FLOAT,
    vmaf_score FLOAT,
    file_size_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_clip_id) REFERENCES clips(id),
    FOREIGN KEY (target_clip_id) REFERENCES clips(id)
);
```

---

## 🧪 COMPREHENSIVE TESTING STRATEGY

### **Unit Testing Requirements**
```python
# tests/test_lossless_cutting.py
class TestLosslessCutting:
    def test_keyframe_detection_accuracy(self):
        """Verify keyframe detection matches FFprobe output exactly."""
        
    def test_lossless_extraction_quality(self):
        """Ensure stream copy maintains identical quality."""
        
    def test_smart_cut_precision(self):
        """Verify smart cuts are frame-accurate."""
        
    def test_concatenation_seamless(self):
        """Ensure no artifacts at clip boundaries."""
```

### **Integration Testing Protocol**
```bash
#!/bin/bash
# integration_test.sh - MANDATORY before deployment

echo "🧪 Testing lossless video editing pipeline..."

# Test 1: Upload high-quality test video
curl -X POST -F "file=@test_4k_60fps.mp4" http://localhost:8000/api/videos/upload
VIDEO_ID=$(echo $response | jq -r '.id')

# Test 2: Analyze keyframes
curl -X GET http://localhost:8000/api/videos/$VIDEO_ID/keyframes
KEYFRAMES=$(echo $response | jq -r '.keyframes')

# Test 3: Extract lossless clip at keyframe
curl -X POST -H "Content-Type: application/json" \
  -d "{\"start\": 2.002, \"end\": 6.006, \"lossless\": true}" \
  http://localhost:8000/api/clips/mark

# Test 4: Build timeline with quality preservation
curl -X POST http://localhost:8000/api/projects/build?video_id=$VIDEO_ID

# Test 5: Verify quality metrics
curl -X GET http://localhost:8000/api/quality/report/$VIDEO_ID

echo "✅ All lossless tests passed with verified quality preservation"
```

---

## 🚀 DEPLOYMENT & VALIDATION CHECKLIST

### **Pre-Deployment Requirements**
- [ ] All FFmpeg commands tested with sample videos
- [ ] Quality metrics validated against known benchmarks
- [ ] Frontend UI properly displays lossless indicators
- [ ] Database migrations applied successfully
- [ ] No memory leaks in video processing pipeline
- [ ] Error handling covers all edge cases
- [ ] Performance benchmarks meet requirements (< 2x processing time)

### **Success Criteria Verification**
```bash
# MANDATORY: Prove lossless capability
./run_lossless_validation.sh

# Expected outputs:
# ✅ Keyframe detection: 100% accurate
# ✅ Stream copy: Identical file hash for keyframe cuts
# ✅ Smart cuts: SSIM > 0.99, PSNR > 45dB
# ✅ Concatenation: No frame drops or artifacts
# ✅ UI feedback: Real-time lossless status
# ✅ Performance: < 2x realtime for lossless operations
```

---

## 📚 REFERENCE DOCUMENTATION

### **Official Sources**
- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html
  - Stream copy limitations and keyframe requirements
  - Quality analysis filters (SSIM, PSNR, VMAF)
  - Concat demuxer best practices

- **LosslessCut GitHub**: https://github.com/mifi/lossless-cut
  - Smart cutting algorithm implementation
  - Keyframe detection methodology
  - User experience patterns for lossless editing

- **Video Engineering Standards**:
  - ITU-R BT.500: Video quality assessment methods
  - SMPTE standards for professional video editing
  - EBU R128: Audio loudness standards

### **Industry Best Practices**
- **Adobe Premiere Pro**: Proxy workflows and conform processes
- **DaVinci Resolve**: Smart reframing and quality preservation
- **Avid Media Composer**: Professional lossless editing workflows

---

## 🎯 IMPLEMENTATION EXECUTION PROTOCOL

### **Step-by-Step Execution**
1. **Start with .cursorrules compliance check**
2. **Implement Phase 1 with mandatory testing after each function**
3. **Verify backend functionality with curl before proceeding**
4. **Test frontend integration thoroughly**
5. **Run comprehensive quality validation**
6. **Document all changes with before/after comparisons**
7. **Create rollback plan and test rollback procedure**

### **Quality Gates**
Each phase MUST pass these gates before proceeding:
- ✅ All unit tests passing
- ✅ Integration tests successful
- ✅ No errors in server logs
- ✅ Frontend properly displays new features
- ✅ Performance within acceptable bounds
- ✅ Quality metrics meet professional standards

---

## 🔥 CRITICAL SUCCESS FACTORS

1. **Strict .cursorrules Adherence**: Every change tested and verified
2. **Quality-First Approach**: Lossless capability proven with metrics
3. **User Experience Excellence**: Clear feedback on editing decisions
4. **Performance Optimization**: Fast processing without quality compromise
5. **Professional Standards**: Match or exceed industry-standard tools

**FINAL VALIDATION**: The implementation is only successful when users can perform frame-accurate, truly lossless video editing with real-time feedback and professional-grade quality preservation, all verified through comprehensive testing protocols.
