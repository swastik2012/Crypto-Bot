import React, { memo } from 'react';

export const LiquidBackground: React.FC = memo(() => {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0 select-none">
      {/* Base soft gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-100 via-[#EBF3FC] to-slate-200 dark:from-[#070A11] dark:via-[#0B0F19] dark:to-[#070A11] transition-colors duration-500" />

      {/* Primary Orb: Ultra-efficient native radial gradient (No heavy 100px Gaussian blur passes) */}
      <div 
        className="absolute -top-32 -left-20 w-[520px] h-[520px] rounded-full pointer-events-none opacity-80 dark:opacity-70 transition-opacity duration-700"
        style={{
          background: 'radial-gradient(circle, rgba(6,182,212,0.22) 0%, rgba(59,130,246,0.14) 35%, transparent 70%)',
        }}
      />

      {/* Secondary Orb */}
      <div 
        className="absolute top-1/3 -right-32 w-[560px] h-[560px] rounded-full pointer-events-none opacity-70 dark:opacity-60 transition-opacity duration-700"
        style={{
          background: 'radial-gradient(circle, rgba(168,85,247,0.18) 0%, rgba(236,72,153,0.10) 35%, transparent 70%)',
        }}
      />

      {/* Tertiary Orb */}
      <div 
        className="absolute -bottom-40 left-1/4 w-[560px] h-[560px] rounded-full pointer-events-none opacity-70 dark:opacity-55 transition-opacity duration-700"
        style={{
          background: 'radial-gradient(circle, rgba(16,185,129,0.16) 0%, rgba(20,184,166,0.08) 35%, transparent 70%)',
        }}
      />

      {/* Ambient micro-grid dots */}
      <div className="absolute inset-0 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:32px_32px] opacity-[0.05] dark:opacity-[0.03]" />
    </div>
  );
});
