import React from 'react';

export default function Logo({ size = 28, className = "" }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 32 32" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Dynamic Background Shield */}
      <path 
        d="M16 2.5L28.5 9.71698V22.283L16 29.5L3.5 22.283V9.71698L16 2.5Z" 
        fill="url(#logo-grad-bg)" 
        stroke="url(#logo-grad-border)" 
        strokeWidth="1.25"
        className="animate-pulse-slow"
      />
      
      {/* Subtle Grid behind the A */}
      <path d="M8 12H24" stroke="white" strokeOpacity="0.05" strokeWidth="0.5"/>
      <path d="M8 16H24" stroke="white" strokeOpacity="0.05" strokeWidth="0.5"/>
      <path d="M8 20H24" stroke="white" strokeOpacity="0.05" strokeWidth="0.5"/>
      
      {/* Stylized 'A' forming an ascending structure */}
      <path 
        d="M16 7L8 23H11.5L13.5 19H18.5L20.5 23H24L16 7Z" 
        fill="url(#logo-grad-a)" 
      />
      
      {/* Ascending Chart Line / Trading Signal cutting through */}
      <path 
        d="M6 21L13 12L17.5 16L25 6" 
        stroke="#10b981" 
        strokeWidth="2.5" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      />
      
      {/* Signal Node */}
      <circle cx="25" cy="6" r="2.5" fill="#34d399" className="animate-pulse" />
      <circle cx="13" cy="12" r="1.5" fill="#10b981" />
      <circle cx="17.5" cy="16" r="1.5" fill="#10b981" />

      <defs>
        <linearGradient id="logo-grad-bg" x1="16" y1="2" x2="16" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--accent)" stopOpacity="0.15"/>
          <stop offset="1" stopColor="var(--app-bg)" stopOpacity="0.9"/>
        </linearGradient>
        
        <linearGradient id="logo-grad-border" x1="3.5" y1="2.5" x2="28.5" y2="29.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--accent)" stopOpacity="0.8" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="0.1" />
        </linearGradient>
        
        <linearGradient id="logo-grad-a" x1="16" y1="7" x2="16" y2="23" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffffff" />
          <stop offset="1" stopColor="#94a3b8" />
        </linearGradient>
      </defs>
    </svg>
  );
}
