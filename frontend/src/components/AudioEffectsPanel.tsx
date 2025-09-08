import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

interface EffectParameter {
  type: string;
  min: number;
  max: number;
  default: number;
  description: string;
}

interface EffectDefinition {
  name: string;
  parameters: Record<string, EffectParameter>;
}

interface AudioEffect {
  type: string;
  parameters: Record<string, any>;
  enabled: boolean;
  order: number;
}

interface EffectPreset {
  name: string;
  effects_count: number;
  effects: AudioEffect[];
}

interface AudioEffectsPanelProps {
  videoId?: string;
  onProcessingComplete?: (result: any) => void;
  className?: string;
}

export const AudioEffectsPanel: React.FC<AudioEffectsPanelProps> = ({
  videoId,
  onProcessingComplete,
  className = ''
}) => {
  const [availableEffects, setAvailableEffects] = useState<Record<string, EffectDefinition>>({});
  const [presets, setPresets] = useState<Record<string, EffectPreset>>({});
  const [currentEffects, setCurrentEffects] = useState<AudioEffect[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState<'presets' | 'custom'>('presets');

  // Fetch available effects and presets
  useEffect(() => {
    const fetchEffectsData = async () => {
      try {
        setIsLoading(true);
        
        // Fetch available effects
        const effectsResponse = await fetch('/api/audio/effects/available');
        const effectsData = await effectsResponse.json();
        
        if (effectsData.success) {
          setAvailableEffects(effectsData.effects);
        }
        
        // Fetch presets
        const presetsResponse = await fetch('/api/audio/effects/presets');
        const presetsData = await presetsResponse.json();
        
        if (presetsData.success) {
          setPresets(presetsData.presets);
        }
        
      } catch (error) {
        console.error('Error fetching effects data:', error);
        toast.error('Failed to load audio effects');
      } finally {
        setIsLoading(false);
      }
    };

    fetchEffectsData();
  }, []);

  // Apply preset to current effects
  const applyPreset = useCallback((presetName: string) => {
    const preset = presets[presetName];
    if (preset) {
      setCurrentEffects([...preset.effects]);
      setSelectedPreset(presetName);
      setActiveTab('custom'); // Switch to custom tab to show applied effects
    }
  }, [presets]);

  // Add effect to chain
  const addEffect = useCallback((effectType: string) => {
    const effectDef = availableEffects[effectType];
    if (!effectDef) return;

    const defaultParameters: Record<string, any> = {};
    Object.entries(effectDef.parameters).forEach(([key, param]) => {
      defaultParameters[key] = param.default;
    });

    const newEffect: AudioEffect = {
      type: effectType,
      parameters: defaultParameters,
      enabled: true,
      order: currentEffects.length
    };

    setCurrentEffects(prev => [...prev, newEffect]);
    setSelectedPreset(''); // Clear preset selection when manually adding effects
  }, [availableEffects, currentEffects.length]);

  // Remove effect from chain
  const removeEffect = useCallback((index: number) => {
    setCurrentEffects(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Update effect parameter
  const updateEffectParameter = useCallback((effectIndex: number, paramName: string, value: any) => {
    setCurrentEffects(prev => prev.map((effect, i) => 
      i === effectIndex 
        ? { ...effect, parameters: { ...effect.parameters, [paramName]: value } }
        : effect
    ));
  }, []);

  // Toggle effect enabled state
  const toggleEffect = useCallback((index: number) => {
    setCurrentEffects(prev => prev.map((effect, i) => 
      i === index ? { ...effect, enabled: !effect.enabled } : effect
    ));
  }, []);

  // Move effect in chain
  const moveEffect = useCallback((fromIndex: number, toIndex: number) => {
    setCurrentEffects(prev => {
      const newEffects = [...prev];
      const [moved] = newEffects.splice(fromIndex, 1);
      newEffects.splice(toIndex, 0, moved);
      
      // Update order indices
      return newEffects.map((effect, i) => ({ ...effect, order: i }));
    });
  }, []);

  // Process audio with current effects
  const processAudio = useCallback(async () => {
    if (!videoId) {
      toast.error('No video selected');
      return;
    }

    if (currentEffects.length === 0) {
      toast.error('No effects to apply');
      return;
    }

    setIsProcessing(true);
    
    try {
      const requestBody = {
        video_id: videoId,
        effects: currentEffects,
        preserve_video: true
      };

      const response = await fetch('/api/audio/effects/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      const result = await response.json();

      if (result.success) {
        toast.success(`Audio processed with ${result.effects_applied} effects!`);
        onProcessingComplete?.(result);
      } else {
        throw new Error(result.error || 'Processing failed');
      }

    } catch (error) {
      console.error('Audio processing error:', error);
      toast.error('Failed to process audio');
    } finally {
      setIsProcessing(false);
    }
  }, [videoId, currentEffects, onProcessingComplete]);

  // Generate preview
  const generatePreview = useCallback(async () => {
    if (!videoId || currentEffects.length === 0) return;

    try {
      const response = await fetch('/api/audio/effects/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: videoId,
          start_time: 0,
          duration: 10,
          effects: currentEffects
        })
      });

      const result = await response.json();

      if (result.success) {
        // Create audio element to play preview
        const audio = new Audio(result.download_url);
        audio.play();
        toast.success('Preview generated! Playing 10-second sample.');
      } else {
        throw new Error(result.error);
      }

    } catch (error) {
      console.error('Preview error:', error);
      toast.error('Failed to generate preview');
    }
  }, [videoId, currentEffects]);

  if (isLoading) {
    return (
      <div className={`audio-effects-panel loading ${className}`} style={{
        padding: '2rem',
        textAlign: 'center',
        backgroundColor: '#f9fafb',
        borderRadius: '8px',
        border: '1px solid #e5e7eb'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
          <div style={{
            width: '20px', height: '20px', border: '2px solid #e5e7eb',
            borderTop: '2px solid #3b82f6', borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          Loading audio effects...
        </div>
      </div>
    );
  }

  return (
    <div className={`audio-effects-panel ${className}`} style={{
      backgroundColor: '#ffffff',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: '#f9fafb'
      }}>
        <h3 style={{
          margin: 0,
          fontSize: '1.25rem',
          fontWeight: '600',
          color: '#374151'
        }}>
          🎛️ Audio Effects Studio
        </h3>
        <p style={{
          margin: '0.5rem 0 0 0',
          fontSize: '0.875rem',
          color: '#6b7280'
        }}>
          Apply professional audio effects and processing
        </p>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid #e5e7eb'
      }}>
        <button
          onClick={() => setActiveTab('presets')}
          style={{
            flex: 1,
            padding: '0.75rem 1rem',
            backgroundColor: activeTab === 'presets' ? '#3b82f6' : 'transparent',
            color: activeTab === 'presets' ? 'white' : '#374151',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          📦 Presets
        </button>
        <button
          onClick={() => setActiveTab('custom')}
          style={{
            flex: 1,
            padding: '0.75rem 1rem',
            backgroundColor: activeTab === 'custom' ? '#3b82f6' : 'transparent',
            color: activeTab === 'custom' ? 'white' : '#374151',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          🔧 Custom Chain
        </button>
      </div>

      <div style={{ padding: '1rem' }}>
        {activeTab === 'presets' ? (
          /* Presets Tab */
          <div>
            <h4 style={{ margin: '0 0 1rem 0', color: '#374151' }}>Effect Presets</h4>
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {Object.entries(presets).map(([presetName, preset]) => (
                <div
                  key={presetName}
                  style={{
                    padding: '1rem',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    backgroundColor: selectedPreset === presetName ? '#eff6ff' : '#f9fafb',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onClick={() => applyPreset(presetName)}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.5rem'
                  }}>
                    <h5 style={{ margin: 0, color: '#374151', fontSize: '1rem' }}>
                      {preset.name}
                    </h5>
                    <span style={{
                      fontSize: '0.75rem',
                      color: '#6b7280',
                      backgroundColor: '#e5e7eb',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px'
                    }}>
                      {preset.effects_count} effects
                    </span>
                  </div>
                  <p style={{
                    margin: 0,
                    fontSize: '0.875rem',
                    color: '#6b7280'
                  }}>
                    {preset.effects.map(e => e.type).join(', ')}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Custom Chain Tab */
          <div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem'
            }}>
              <h4 style={{ margin: 0, color: '#374151' }}>
                Effect Chain ({currentEffects.length} effects)
              </h4>
              <select
                onChange={(e) => e.target.value && addEffect(e.target.value)}
                value=""
                style={{
                  padding: '0.5rem',
                  border: '1px solid #444',
                  borderRadius: '4px',
                  backgroundColor: '#2a2a2a',
                  color: '#eee'
                }}
              >
                <option value="">+ Add Effect</option>
                {Object.entries(availableEffects).map(([type, effect]) => (
                  <option key={type} value={type}>{effect.name}</option>
                ))}
              </select>
            </div>

            {/* Effects List */}
            <div style={{ marginBottom: '1rem', maxHeight: '400px', overflowY: 'auto' }}>
              {currentEffects.length === 0 ? (
                <div style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: '#6b7280',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                  border: '2px dashed #d1d5db'
                }}>
                  No effects added. Select a preset or add effects manually.
                </div>
              ) : (
                currentEffects.map((effect, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '1rem',
                      border: '1px solid #e5e7eb',
                      borderRadius: '6px',
                      marginBottom: '0.75rem',
                      backgroundColor: effect.enabled ? '#ffffff' : '#f3f4f6',
                      opacity: effect.enabled ? 1 : 0.6
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.75rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <button
                          onClick={() => toggleEffect(index)}
                          style={{
                            padding: '0.25rem',
                            backgroundColor: effect.enabled ? '#10b981' : '#6b7280',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          {effect.enabled ? '✓' : '✗'}
                        </button>
                        <h5 style={{ margin: 0, color: '#374151' }}>
                          {availableEffects[effect.type]?.name || effect.type}
                        </h5>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => index > 0 && moveEffect(index, index - 1)}
                          disabled={index === 0}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: '#6b7280',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: index === 0 ? 'not-allowed' : 'pointer',
                            opacity: index === 0 ? 0.5 : 1
                          }}
                        >
                          ↑
                        </button>
                        <button
                          onClick={() => index < currentEffects.length - 1 && moveEffect(index, index + 1)}
                          disabled={index === currentEffects.length - 1}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: '#6b7280',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: index === currentEffects.length - 1 ? 'not-allowed' : 'pointer',
                            opacity: index === currentEffects.length - 1 ? 0.5 : 1
                          }}
                        >
                          ↓
                        </button>
                        <button
                          onClick={() => removeEffect(index)}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: '#ef4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    {/* Effect Parameters */}
                    {effect.enabled && availableEffects[effect.type] && (
                      <div style={{ display: 'grid', gap: '0.75rem' }}>
                        {Object.entries(availableEffects[effect.type].parameters).map(([paramName, param]) => (
                          <div key={paramName}>
                            <label style={{
                              display: 'block',
                              fontSize: '0.875rem',
                              fontWeight: '500',
                              color: '#374151',
                              marginBottom: '0.25rem'
                            }}>
                              {paramName.replace(/_/g, ' ')}
                            </label>
                            <input
                              type="range"
                              min={param.min}
                              max={param.max}
                              step={param.type === 'float' ? 0.1 : 1}
                              value={effect.parameters[paramName] || param.default}
                              onChange={(e) => updateEffectParameter(index, paramName, parseFloat(e.target.value))}
                              style={{ width: '100%' }}
                            />
                            <div style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              fontSize: '0.75rem',
                              color: '#6b7280',
                              marginTop: '0.25rem'
                            }}>
                              <span>{param.min}</span>
                              <span>{effect.parameters[paramName] || param.default}</span>
                              <span>{param.max}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: '0.75rem',
          paddingTop: '1rem',
          borderTop: '1px solid #e5e7eb'
        }}>
          <button
            onClick={generatePreview}
            disabled={!videoId || currentEffects.length === 0}
            style={{
              flex: 1,
              padding: '0.75rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '500',
              cursor: !videoId || currentEffects.length === 0 ? 'not-allowed' : 'pointer',
              opacity: !videoId || currentEffects.length === 0 ? 0.5 : 1
            }}
          >
            🎧 Preview (10s)
          </button>
          <button
            onClick={processAudio}
            disabled={!videoId || currentEffects.length === 0 || isProcessing}
            style={{
              flex: 2,
              padding: '0.75rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '500',
              cursor: !videoId || currentEffects.length === 0 || isProcessing ? 'not-allowed' : 'pointer',
              opacity: !videoId || currentEffects.length === 0 || isProcessing ? 0.5 : 1
            }}
          >
            {isProcessing ? '⏳ Processing...' : '🎚️ Process Audio'}
          </button>
        </div>
      </div>

      {/* CSS Animation */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default AudioEffectsPanel;
