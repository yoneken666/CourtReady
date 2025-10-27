import React from 'react';

const OLIVE = "#6B8E23";

function Emblem({ size = 64 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <rect width="128" height="128" rx="14" fill="white" />
      <g transform="translate(14,12)" stroke={OLIVE} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M42 90 L86 90" stroke={OLIVE} />
        <path d="M64 18 v56" stroke={OLIVE} />
        <path d="M40 34 L64 18 L88 34" stroke={OLIVE} />
        <path d="M40 34 C34 44, 30 54, 24 66" stroke={OLIVE} />
        <circle cx="20" cy="74" r="6" fill="white" stroke={OLIVE} />
        <path d="M88 34 C94 44, 98 54, 104 66" stroke={OLIVE} />
        <circle cx="104" cy="74" r="6" fill="white" stroke={OLIVE} />
        <path d="M64 6 C58 2, 50 2, 44 6 C50 8, 56 12, 64 12 C72 12, 78 8, 84 6 C78 2, 70 2, 64 6 Z" fill={OLIVE} stroke="none" />
      </g>
    </svg>
  );
}

export default Emblem;
