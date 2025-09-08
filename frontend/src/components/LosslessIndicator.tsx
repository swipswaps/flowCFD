import React from 'react';

interface LosslessStatusProps {
  methodUsed: string;
  qualityPreserved: boolean;
  keyframeAligned: boolean;
  processingTime: number;
  warnings: string[];
}

interface LosslessIndicatorProps {
  methodUsed: string;
  qualityPreserved: boolean;
  keyframeAligned: boolean;
  processingTime: number;
  warnings: string[];
  className?: string;
}

const LosslessIndicator: React.FC<LosslessIndicatorProps> = ({ 
  methodUsed, 
  qualityPreserved, 
  keyframeAligned, 
  processingTime, 
  warnings, 
  className = '' 
}) => {
  const getStatusColor = () => {
    if (methodUsed === 'stream_copy') return '#10b981'; // Green
    if (methodUsed === 'smart_cut') return '#f59e0b'; // Amber
    return '#ef4444'; // Red
  };

  const getStatusIcon = () => {
    if (methodUsed === 'stream_copy') return '✅';
    if (methodUsed === 'smart_cut') return '⚠️';
    return '🔄';
  };

  const getStatusText = () => {
    switch (methodUsed) {
      case 'stream_copy': return 'Lossless (Stream Copy)';
      case 'smart_cut': return 'Near-Lossless (Smart Cut)';
      case 're_encoded': return 'Re-encoded (Quality Loss)';
      case 'fallback_encoded': return 'Fallback Encoding';
      default: return `Method: ${methodUsed}`;
    }
  };

  return (
    <div className={`lossless-indicator ${className}`} style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 12px',
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      borderRadius: '6px',
      border: `2px solid ${getStatusColor()}`,
      color: 'white',
      fontSize: '0.875rem',
      fontWeight: '500'
    }}>
      <span style={{ fontSize: '1rem' }}>{getStatusIcon()}</span>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ color: getStatusColor() }}>
          {getStatusText()}
        </span>
        
        <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>
          Quality: {qualityPreserved ? 'Preserved' : 'Reduced'}
        </span>
        
        <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
          Keyframes: {keyframeAligned ? 'Aligned' : 'Misaligned'}
        </span>
        
        <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
          Time: {processingTime.toFixed(2)}s
        </span>

        {warnings.length > 0 && (
          <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>
            ⚠️ {warnings[0]}
          </span>
        )}
      </div>

      {qualityPreserved && (
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: '#10b981',
          marginLeft: 'auto'
        }} title="Quality preserved" />
      )}
    </div>
  );
};

export default LosslessIndicator;
