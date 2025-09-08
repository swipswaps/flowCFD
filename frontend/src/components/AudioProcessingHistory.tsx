import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';

interface ProcessingResult {
  id: string;
  timestamp: string;
  effect_chain: string;
  effects_applied: number;
  file_size_mb: number;
  download_url: string;
  input_file: string;
  output_file: string;
  preserve_video: boolean;
}

interface AudioProcessingHistoryProps {
  className?: string;
}

export const AudioProcessingHistory: React.FC<AudioProcessingHistoryProps> = ({
  className = ''
}) => {
  const [processingHistory, setProcessingHistory] = useState<ProcessingResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Add new processing result to history
  const addToHistory = (result: any) => {
    const historyItem: ProcessingResult = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      effect_chain: result.effect_chain || 'Unknown',
      effects_applied: result.effects_applied || 0,
      file_size_mb: result.file_size_mb || 0,
      download_url: result.download_url || '',
      input_file: result.input_file || 'Unknown',
      output_file: result.output_file || 'Unknown',
      preserve_video: result.preserve_video !== false
    };

    setProcessingHistory(prev => [historyItem, ...prev]);
    
    // Store in localStorage for persistence
    const stored = localStorage.getItem('audio_processing_history');
    const history = stored ? JSON.parse(stored) : [];
    history.unshift(historyItem);
    
    // Keep only last 50 items
    const trimmed = history.slice(0, 50);
    localStorage.setItem('audio_processing_history', JSON.stringify(trimmed));
  };

  // Load history from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('audio_processing_history');
    if (stored) {
      try {
        const history = JSON.parse(stored);
        setProcessingHistory(history);
      } catch (error) {
        console.error('Error loading processing history:', error);
      }
    }
  }, []);

  // Clear history
  const clearHistory = () => {
    setProcessingHistory([]);
    localStorage.removeItem('audio_processing_history');
    toast.success('Processing history cleared');
  };

  // Download file
  const downloadFile = (url: string, filename: string) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Download started');
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  // Format file size
  const formatFileSize = (sizeMb: number) => {
    if (sizeMb < 1) {
      return `${(sizeMb * 1024).toFixed(0)} KB`;
    }
    return `${sizeMb.toFixed(1)} MB`;
  };

  // Get effect type color
  const getEffectTypeColor = (effectChain: string) => {
    if (effectChain.includes('voice')) return '#10b981';
    if (effectChain.includes('music')) return '#3b82f6';
    if (effectChain.includes('podcast')) return '#f59e0b';
    if (effectChain.includes('creative')) return '#8b5cf6';
    return '#6b7280';
  };

  // Expose addToHistory method for parent components
  React.useEffect(() => {
    (window as any).addAudioProcessingToHistory = addToHistory;
    return () => {
      delete (window as any).addAudioProcessingToHistory;
    };
  }, []);

  return (
    <div className={`audio-processing-history ${className}`} style={{
      backgroundColor: '#ffffff',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: '#f9fafb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h3 style={{
            margin: 0,
            fontSize: '1.25rem',
            fontWeight: '600',
            color: '#374151'
          }}>
            📊 Processing History
          </h3>
          <p style={{
            margin: '0.25rem 0 0 0',
            fontSize: '0.875rem',
            color: '#6b7280'
          }}>
            {processingHistory.length} processed files
          </p>
        </div>
        
        {processingHistory.length > 0 && (
          <button
            onClick={clearHistory}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            🗑️ Clear History
          </button>
        )}
      </div>

      {/* History List */}
      <div style={{
        maxHeight: '500px',
        overflowY: 'auto',
        padding: processingHistory.length > 0 ? '0' : '2rem'
      }}>
        {processingHistory.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#6b7280'
          }}>
            <div style={{
              fontSize: '3rem',
              marginBottom: '1rem',
              opacity: 0.5
            }}>
              🎚️
            </div>
            <p>No audio processing history yet.</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              Processed audio files will appear here for easy access and re-download.
            </p>
          </div>
        ) : (
          processingHistory.map((item, index) => (
            <div
              key={item.id}
              style={{
                padding: '1rem',
                borderBottom: index < processingHistory.length - 1 ? '1px solid #e5e7eb' : 'none',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '0.75rem'
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    marginBottom: '0.5rem'
                  }}>
                    <h4 style={{
                      margin: 0,
                      fontSize: '1rem',
                      fontWeight: '500',
                      color: '#374151'
                    }}>
                      {item.output_file}
                    </h4>
                    <span
                      style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: getEffectTypeColor(item.effect_chain),
                        color: 'white',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '500'
                      }}
                    >
                      {item.effect_chain}
                    </span>
                  </div>
                  
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: '0.5rem',
                    fontSize: '0.875rem',
                    color: '#6b7280'
                  }}>
                    <div>
                      <strong>Input:</strong> {item.input_file}
                    </div>
                    <div>
                      <strong>Effects:</strong> {item.effects_applied}
                    </div>
                    <div>
                      <strong>Size:</strong> {formatFileSize(item.file_size_mb)}
                    </div>
                    <div>
                      <strong>Type:</strong> {item.preserve_video ? 'Video + Audio' : 'Audio Only'}
                    </div>
                  </div>
                  
                  <div style={{
                    fontSize: '0.75rem',
                    color: '#9ca3af',
                    marginTop: '0.5rem'
                  }}>
                    Processed on {formatTimestamp(item.timestamp)}
                  </div>
                </div>

                <div style={{
                  display: 'flex',
                  gap: '0.5rem',
                  marginLeft: '1rem'
                }}>
                  <button
                    onClick={() => downloadFile(item.download_url, item.output_file)}
                    style={{
                      padding: '0.5rem 0.75rem',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '0.875rem',
                      fontWeight: '500',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem'
                    }}
                  >
                    ⬇️ Download
                  </button>
                  
                  {item.preserve_video && (
                    <button
                      onClick={() => {
                        // Create video element to preview
                        const video = document.createElement('video');
                        video.src = item.download_url;
                        video.controls = true;
                        video.style.width = '100%';
                        video.style.maxWidth = '600px';
                        
                        // Create modal-like preview
                        const modal = document.createElement('div');
                        modal.style.position = 'fixed';
                        modal.style.top = '0';
                        modal.style.left = '0';
                        modal.style.width = '100%';
                        modal.style.height = '100%';
                        modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
                        modal.style.display = 'flex';
                        modal.style.alignItems = 'center';
                        modal.style.justifyContent = 'center';
                        modal.style.zIndex = '9999';
                        modal.style.cursor = 'pointer';
                        
                        const container = document.createElement('div');
                        container.style.padding = '2rem';
                        container.style.backgroundColor = 'white';
                        container.style.borderRadius = '8px';
                        container.style.maxWidth = '90%';
                        container.style.maxHeight = '90%';
                        
                        container.appendChild(video);
                        modal.appendChild(container);
                        document.body.appendChild(modal);
                        
                        modal.onclick = (e) => {
                          if (e.target === modal) {
                            document.body.removeChild(modal);
                          }
                        };
                      }}
                      style={{
                        padding: '0.5rem 0.75rem',
                        backgroundColor: '#10b981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '0.875rem',
                        fontWeight: '500',
                        cursor: 'pointer'
                      }}
                    >
                      👁️ Preview
                    </button>
                  )}
                </div>
              </div>

              {/* Progress indicator for recent items */}
              {index < 3 && (
                <div style={{
                  width: '100%',
                  height: '2px',
                  backgroundColor: '#e5e7eb',
                  borderRadius: '1px',
                  overflow: 'hidden'
                }}>
                  <div
                    style={{
                      width: '100%',
                      height: '100%',
                      backgroundColor: getEffectTypeColor(item.effect_chain),
                      opacity: 0.7
                    }}
                  />
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Summary Statistics */}
      {processingHistory.length > 0 && (
        <div style={{
          padding: '1rem',
          borderTop: '1px solid #e5e7eb',
          backgroundColor: '#f9fafb'
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '1rem',
            fontSize: '0.875rem'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#3b82f6' }}>
                {processingHistory.length}
              </div>
              <div style={{ color: '#6b7280' }}>Total Files</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#10b981' }}>
                {processingHistory.reduce((sum, item) => sum + item.effects_applied, 0)}
              </div>
              <div style={{ color: '#6b7280' }}>Effects Applied</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#f59e0b' }}>
                {formatFileSize(processingHistory.reduce((sum, item) => sum + item.file_size_mb, 0))}
              </div>
              <div style={{ color: '#6b7280' }}>Total Size</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AudioProcessingHistory;
