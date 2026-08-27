import React from 'react';
import { motion } from 'framer-motion';
import type { HTMLMotionProps } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface GlassCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'subtle' | 'accent' | 'glow-cyan' | 'glow-emerald' | 'glow-purple' | 'glow-rose';
  hoverEffect?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className,
  variant = 'default',
  hoverEffect = false,
  ...props
}) => {
  const baseClasses = 'relative rounded-2xl md:rounded-3xl transition-all duration-300 overflow-hidden';

  const variantClasses = {
    default: 'liquid-glass text-slate-800 dark:text-slate-100',
    subtle: 'liquid-glass-subtle text-slate-700 dark:text-slate-200',
    accent: 'liquid-glass-accent text-slate-800 dark:text-slate-100',
    'glow-cyan': 'liquid-glass border-cyan-500/30 shadow-glow-cyan text-slate-800 dark:text-slate-100',
    'glow-emerald': 'liquid-glass border-emerald-500/30 shadow-glow-emerald text-slate-800 dark:text-slate-100',
    'glow-purple': 'liquid-glass border-purple-500/30 shadow-glow-purple text-slate-800 dark:text-slate-100',
    'glow-rose': 'liquid-glass border-rose-500/30 shadow-glow-rose text-slate-800 dark:text-slate-100',
  };

  const hoverClasses = hoverEffect
    ? 'glass-hover hover:-translate-y-0.5 cursor-pointer'
    : '';

  return (
    <motion.div
      className={twMerge(clsx(baseClasses, variantClasses[variant], hoverClasses, className))}
      {...props}
    >
      {/* Specular inner top highlight line */}
      <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/25 to-transparent pointer-events-none" />
      {children}
    </motion.div>
  );
};
