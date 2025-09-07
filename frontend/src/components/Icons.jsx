import React from 'react';

// Original icons
export const SettingsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

export const VentIcon = () => (
  <svg width="30" height="30" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg">
    {/* Device Body */}
    <rect x="10" y="20" width="100" height="110" rx="8" ry="8" fill="#444" stroke="#222" strokeWidth="2"/>

    {/* Screen */}
    <rect x="20" y="30" width="80" height="40" rx="2" ry="2" fill="#ccc" stroke="#888" strokeWidth="1"/>
    <text x="25" y="55" fontSize="8" fill="#000">Ventilator</text>

    {/* Knob on Side */}
    <circle cx="115" cy="75" r="10" fill="#337ab7" stroke="#222" strokeWidth="1"/>
    <circle cx="115" cy="75" r="4" fill="#fff"/>

    {/* Speaker Grill */}
    <circle cx="30" cy="100" r="6" fill="#222"/>
    <circle cx="30" cy="100" r="2" fill="#555"/>

    {/* Power Button */}
    <circle cx="90" cy="110" r="6" fill="#0a0" stroke="#222" strokeWidth="1"/>
    <text x="87" y="113" fontSize="5" fill="#fff">⏻</text>

    {/* Ports at Bottom */}
    <rect x="50" y="120" width="10" height="5" fill="#888"/>
    <rect x="65" y="120" width="10" height="5" fill="#888"/>
  </svg>
);

export const PulseOxIcon = () => (
  <svg width="30" height="30" viewBox="0 0 150 100" xmlns="http://www.w3.org/2000/svg">
    {/* Device Body */}
    <rect x="10" y="10" width="130" height="80" rx="12" ry="12" fill="#333" stroke="#111" strokeWidth="2"/>

    {/* Screen Area */}
    <rect x="25" y="25" width="100" height="40" rx="4" ry="4" fill="#0a0a0a" stroke="#555" strokeWidth="1"/>

    {/* SpO2 Label */}
    <text x="35" y="42" fontSize="8" fill="#0f0">SpO₂</text>

    {/* SpO2 Value */}
    <text x="80" y="42" fontSize="12" fill="#0f0" fontWeight="bold">98%</text>

    {/* BPM Label */}
    <text x="35" y="58" fontSize="8" fill="#0ff">BPM</text>

    {/* BPM Value */}
    <text x="80" y="58" fontSize="12" fill="#0ff" fontWeight="bold">76</text>

    {/* Status Light */}
    <circle cx="125" cy="70" r="5" fill="#0f0" stroke="#222" strokeWidth="1"/>
  </svg>
);

export const ClipboardIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {/* Clipboard Outline */}
    <rect x="4" y="3" width="16" height="18" rx="2" ry="2" />
    
    {/* Top Tab */}
    <rect x="8" y="1" width="8" height="4" rx="1" ry="1" />
    
    {/* Plus Icon to indicate adding a vital */}
    <line x1="12" y1="10" x2="12" y2="14" />
    <line x1="10" y1="12" x2="14" y2="12" />
  </svg>
);

// New minimalist icons
export const MinimalistVentIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {/* Main Body */}
    <rect x="4" y="5" width="16" height="14" rx="2" ry="2"/>

    {/* Screen Area */}
    <rect x="7" y="8" width="10" height="5" rx="0.5" ry="0.5"/>

    {/* Tube Connector Right Side */}
    <circle cx="20" cy="12" r="1.5"/>

    {/* Control Button Below Screen */}
    <circle cx="12" cy="15.5" r="0.8"/>
  </svg>
);

export const MinimalistPulseOxIcon = () => (
   <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
  
  <path d="M12 3 L21 19 H3 Z"/>
  
  <line x1="12" y1="9" x2="12" y2="13"/>
  <circle cx="12" cy="17" r="1"/>
</svg>
);

export const HistoryIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {/* Chart Axes */}
    <polyline points="3 17 3 3 21 3" />

    {/* Trend Line */}
    <polyline points="6 14 10 10 14 13 18 7" />
    
    {/* Data Points */}
    <circle cx="6" cy="14" r="0.8" />
    <circle cx="10" cy="10" r="0.8" />
    <circle cx="14" cy="13" r="0.8" />
    <circle cx="18" cy="7" r="0.8" />
  </svg>
);

export const MedicationIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {/* Capsule shape */}
    <rect x="6" y="9" width="12" height="6" rx="3" ry="3" transform="rotate(45 12 12)" />

    {/* Divider line for half color */}
    <line x1="9.5" y1="14.5" x2="14.5" y2="9.5" />
  </svg>
);

export const CareTasksIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {/* Heart */}
    <path d="M12 21s-6-4.35-8.5-7.6C1.64 10.43 2.63 6.36 6 5.5 7.86 5.01 9.5 6 12 8.5 14.5 6 16.14 5.01 18 5.5c3.37.86 4.36 4.93 2.5 7.9C18 16.65 12 21 12 21z" />

    {/* Checkmark */}
    <polyline points="9 11.5 11 13.5 15 9.5" />
  </svg>
);

export const MessagesIcon = () => (
  <svg width="30" height="30" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {/* Envelope Outline */}
    <rect x="3" y="5" width="18" height="14" rx="2" ry="2" />

    {/* Envelope Flap */}
    <polyline points="3 7 12 13 21 7" />
  </svg>
);