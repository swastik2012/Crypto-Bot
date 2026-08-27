import React, { memo } from 'react';

export const LiquidBackground: React.FC = memo(() => {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0 select-none">
      {/* Base soft gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-100 via-[#EBF3FC] to-slate-200 dark:from-[#070A11] dark:via-[#0B0F19] dark:to-[#070A11] transition-colors duration-500" />

      {/* GPU Accelerated Primary Orb */}
      <div 
        className="absolute -top-32 -left-20 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-cyan-400/25 via-blue-500/20 to-transparent blur-[90px] dark:from-cyan-500/20 dark:via-blue-600/15 dark:blur-[100px] animate-pulse-slow will-change-transform"
        style={{ transform: 'translate3d(0, 0, 0)' }}
      />

      {/* GPU Accelerated Secondary Orb */}
      <div 
        className="absolute top-1/3 -right-32 w-[550px] h-[550px] rounded-full bg-gradient-to-bl from-purple-400/20 via-pink-400/15 to-transparent blur-[100px] dark:from-purple-600/15 dark:via-pink-500/10 dark:blur-[110px] will-change-transform"
        style={{ transform: 'translate3d(0, 0, 0)' }}
      />

      {/* GPU Accelerated Tertiary Orb */}
      <div 
        className="absolute -bottom-40 left-1/4 w-[550px] h-[550px] rounded-full bg-gradient-to-tr from-emerald-400/20 via-teal-400/15 to-transparent blur-[90px] dark:from-emerald-500/15 dark:via-brand-nvidia/10 dark:blur-[100px] will-change-transform"
        style={{ transform: 'translate3d(0, 0, 0)' }}
      />

      {/* Ambient micro-grid dots */}
      <div className="absolute inset-0 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:32px_32px] opacity-[0.05] dark:opacity-[0.03]" />
    </div>
  );
});
