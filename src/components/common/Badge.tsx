import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { SignalType } from '../../types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'cyan' | 'emerald' | 'rose' | 'amber' | 'purple' | 'nvidia' | 'slate' | 'signal';
  signal?: SignalType;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'cyan',
  signal,
  size = 'md',
  className,
  pulse = false,
}) => {
  let activeVariant = variant;
  if (signal) {
    if (signal === 'STRONG BUY' || signal === 'BUY') activeVariant = 'emerald';
    else if (signal === 'HOLD') activeVariant = 'amber';
    else if (signal === 'SELL' || signal === 'STRONG SELL') activeVariant = 'rose';
  }

  const variantStyles = {
    cyan: 'bg-cyan-500/15 text-cyan-800 border-cyan-400/40 shadow-sm dark:bg-cyan-400/10 dark:text-cyan-300 dark:border-cyan-400/30',
    emerald: 'bg-emerald-500/15 text-emerald-800 border-emerald-500/40 shadow-sm dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/30',
    rose: 'bg-rose-500/15 text-rose-800 border-rose-500/40 shadow-sm dark:bg-rose-500/15 dark:text-rose-400 dark:border-rose-500/30',
    amber: 'bg-amber-500/15 text-amber-900 border-amber-500/40 shadow-sm dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/30',
    purple: 'bg-purple-500/15 text-purple-900 border-purple-500/40 shadow-sm dark:bg-purple-500/15 dark:text-purple-400 dark:border-purple-500/30',
    nvidia: 'bg-[#76B900]/15 text-[#426b00] border-[#76B900]/40 shadow-sm dark:bg-[#76B900]/15 dark:text-[#8bd800] dark:border-[#76B900]/30',
    slate: 'bg-slate-200/80 text-slate-800 border-slate-300 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700/50',
    signal: '',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 font-bold tracking-wider rounded-md uppercase',
    md: 'text-xs px-2.5 py-1 font-bold tracking-wide rounded-lg',
    lg: 'text-sm px-3.5 py-1.5 font-extrabold tracking-wide rounded-xl',
  };

  return (
    <span
      className={twMerge(
        clsx(
          'inline-flex items-center gap-1.5 border backdrop-blur-md transition-all font-mono',
          variantStyles[activeVariant],
          sizeStyles[size],
          className
        )
      )}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-current" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-current" />
        </span>
      )}
      {children}
    </span>
  );
};
