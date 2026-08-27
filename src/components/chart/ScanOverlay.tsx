import React from 'react';
import { motion } from 'framer-motion';
import { Camera, Sparkles } from 'lucide-react';

interface ScanOverlayProps {
  stage: number;
  timeframe: string;
  assetPair: string;
}

export const ScanOverlay: React.FC<ScanOverlayProps> = ({
  stage,
  timeframe,
  assetPair,
}) => {
  return (
    <div className="absolute inset-0 z-20 pointer-events-none rounded-2xl overflow-hidden bg-cyan-950/20 backdrop-blur-[2px] border-2 border-cyan-400/50">
      
      {/* High-tech sweeping laser line */}
      <motion.div
        animate={{
          top: ['0%', '100%', '0%'],
        }}
        transition={{
          duration: 2.2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="absolute left-0 right-0 h-[3px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_20px_#00f0ff] z-30"
      />

      {/* Target Reticles in 4 Corners */}
      <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-cyan-400" />
      <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-cyan-400" />
      <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-cyan-400" />
      <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-cyan-400" />

      {/* Simulated Vision API Object Bounding Boxes */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3 }}
        className="absolute top-1/4 left-1/3 w-48 h-28 border border-dashed border-cyan-400/80 bg-cyan-500/10 rounded-lg p-2 flex flex-col justify-between"
      >
        <div className="flex items-center justify-between text-[10px] font-mono text-cyan-300 bg-dark-900/80 px-1.5 py-0.5 rounded">
          <span>PATTERN: ASCENDING_TRIANGLE</span>
          <span>91%</span>
        </div>
        <div className="text-[9px] font-mono text-cyan-200">
          Target Breakout Zone: +5.2%
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.6 }}
        className="absolute bottom-1/3 right-1/4 w-40 h-16 border border-dashed border-emerald-400/80 bg-emerald-500/10 rounded-lg p-1.5 flex flex-col justify-between"
      >
        <div className="flex items-center justify-between text-[10px] font-mono text-emerald-300 bg-dark-900/80 px-1.5 py-0.5 rounded">
          <span>DEMAND ZONE (0.618 FIB)</span>
        </div>
        <div className="text-[9px] font-mono text-emerald-200">
          Support Confluence 20 EMA
        </div>
      </motion.div>

      {/* Center HUD status banner */}
      <div className="absolute inset-x-0 bottom-6 flex justify-center">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center gap-3 px-5 py-2.5 rounded-2xl bg-dark-900/90 border border-cyan-400/50 shadow-glow-cyan text-cyan-300 font-mono text-xs backdrop-blur-xl"
        >
          <Camera className="w-4 h-4 text-cyan-400 animate-bounce" />
          <div className="flex flex-col">
            <span className="font-bold flex items-center gap-1.5">
              <span>CAPTURING {assetPair} [{timeframe}] VIEWPORT (STAGE {stage}/4)</span>
              <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
            </span>
            <span className="text-[10px] text-cyan-400/70">
              Ingesting frame to Gemini Vision 2.0 & streaming to LangChain debate node...
            </span>
          </div>
        </motion.div>
      </div>

    </div>
  );
};
