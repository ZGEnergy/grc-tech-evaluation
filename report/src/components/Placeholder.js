import React from 'react';

const placeholderStyle = {
  border: '1px solid #c7d3dd',
  borderRadius: '8px',
  background: 'linear-gradient(180deg, #f8fbfd 0%, #eef4f8 100%)',
  padding: '2rem',
  margin: '1.5rem 0',
  textAlign: 'left',
};

const titleStyle = {
  fontSize: '1.1rem',
  fontWeight: 600,
  color: '#12344d',
  marginBottom: '0.75rem',
};

const subtitleStyle = {
  fontSize: '0.9rem',
  color: '#4f6475',
  margin: 0,
};

export default function Placeholder({ title }) {
  return (
    <div style={placeholderStyle}>
      <div style={titleStyle}>{title}</div>
      <p style={subtitleStyle}>
        Static preview card for this report section. Interactive treatment is not
        required for the published GitHub Pages build.
      </p>
    </div>
  );
}
