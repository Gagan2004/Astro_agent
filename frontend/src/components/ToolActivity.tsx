import React from 'react';

interface ToolActivityProps {
  toolName: string;
  label: string;
}

export const ToolActivity: React.FC<ToolActivityProps> = ({ toolName, label }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        padding: '0.6rem 1rem',
        background: 'rgba(212, 175, 55, 0.05)',
        border: '1px solid rgba(212, 175, 55, 0.1)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--color-gold-light)',
        fontSize: '0.85rem',
        margin: '0.5rem 0',
        width: 'fit-content',
        animation: 'float 3s infinite ease-in-out',
      }}
    >
      <span className="pulse-indicator" style={{ display: 'flex', alignItems: 'center' }}>
        {getToolIcon(toolName)}
      </span>
      <span style={{ fontStyle: 'italic', letterSpacing: '0.2px' }}>{label}</span>
    </div>
  );
};

function getToolIcon(name: string): string {
  switch (name) {
    case 'geocode_place_tool': return '🧭';
    case 'compute_birth_chart_tool': return '🔮';
    case 'get_daily_transits_tool': return '🪐';
    case 'knowledge_lookup_tool': return '📖';
    default: return '⚙️';
  }
}
