// src/components/auth/AuthBackgroundPattern.tsx
import React from "react";


export function AuthBackgroundPattern() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0 opacity-40">
      <svg
        className="w-full h-full"
        xmlns="http://www.w3.org/2000/svg"
        width="100%"
        height="100%"
        fill="none"
      >
        <defs>
          <pattern
            id="education-grid"
            width="32"
            height="32"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="2" cy="2" r="1" fill="#428a5d" opacity="0.3" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#education-grid)" />
      </svg>
    </div>
  );
}