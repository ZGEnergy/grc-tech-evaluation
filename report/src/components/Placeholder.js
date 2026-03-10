import React from 'react';

const placeholderStyle = {
  border: '2px dashed #b0b0b0',
  borderRadius: '8px',
  backgroundColor: '#f5f5f5',
  padding: '2rem',
  margin: '1.5rem 0',
  textAlign: 'center',
};

const titleStyle = {
  fontSize: '1.1rem',
  fontWeight: 600,
  color: '#333',
  marginBottom: '0.5rem',
};

const subtitleStyle = {
  fontSize: '0.9rem',
  color: '#666',
  fontStyle: 'italic',
};

export default function Placeholder({ title }) {
  return (
    <div style={placeholderStyle}>
      <div style={titleStyle}>{title}</div>
      <div style={subtitleStyle}>Interactive version coming soon</div>
    </div>
  );
}
