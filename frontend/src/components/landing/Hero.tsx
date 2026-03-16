import { motion } from 'framer-motion';
import { ChevronDown, GraduationCap, Trophy, ScrollText } from 'lucide-react';
import FloatingElements from './FloatingElements';

interface HeroProps {
  onScrollDown: () => void;
}

export default function Hero({ onScrollDown }: HeroProps) {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center text-center px-4 overflow-hidden grain mesh-bg">
      <FloatingElements />

      <div className="relative z-10 max-w-6xl mx-auto space-y-10">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex justify-center"
        >
          <span className="inline-flex items-center gap-2 glass border border-violet-200/50 rounded-full px-4 py-1.5 text-sm text-violet-600 shadow-lg shadow-violet-500/10">
            <span className="w-2 h-2 bg-fuchsia-500 rounded-full animate-pulse" />
            Powered by Amazon Nova AI
          </span>
        </motion.div>

        {/* Main Title */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8 }}
        >
          <h1 className="text-7xl sm:text-8xl md:text-9xl lg:text-[11rem] font-black tracking-tighter leading-[0.85] text-slate-900 uppercase select-none">
            AM I{' '}
            <span className="text-outline">ON</span>
            <br />
            TRACK<span className="gradient-text">?</span>
          </h1>
        </motion.div>

        {/* 3D Icon cluster */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.6, type: 'spring' }}
          className="flex items-center justify-center py-4"
        >
          <div className="relative">
            <GraduationCap className="w-32 h-32 text-violet-700 drop-shadow-2xl" strokeWidth={1.2} />
            <motion.div
              className="absolute -top-6 -left-8"
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <Trophy className="w-14 h-14 text-fuchsia-500 -rotate-12 drop-shadow-lg" strokeWidth={1.5} />
            </motion.div>
            <motion.div
              className="absolute -bottom-4 -right-10"
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
            >
              <ScrollText className="w-16 h-16 text-cyan-400 rotate-12 drop-shadow-lg" strokeWidth={1.5} />
            </motion.div>
            {/* Glow behind icons */}
            <div className="absolute inset-0 -z-10 scale-150 bg-violet-400/15 rounded-full blur-3xl" />
          </div>
        </motion.div>

        {/* Subheadline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="max-w-3xl mx-auto"
        >
          <p className="text-xl sm:text-2xl md:text-3xl text-slate-700 leading-snug font-light tracking-tight">
            Universities track{' '}
            <span className="font-black italic text-slate-900">past</span> progress.
            <br />
            We simulate your{' '}
            <span className="font-black text-slate-900 relative">
              future
              <svg className="absolute -bottom-1 left-0 w-full" viewBox="0 0 120 8" fill="none">
                <path d="M2 6C20 2 40 2 60 4C80 6 100 3 118 2" stroke="#d946ef" strokeWidth="3" strokeLinecap="round" />
              </svg>
            </span>
            .
          </p>
        </motion.div>

        {/* CTA scroll button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="pt-6"
        >
          <button
            onClick={onScrollDown}
            className="group relative bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 text-white w-16 h-16 rounded-full flex items-center justify-center transition-all hover:scale-110 active:scale-95 shadow-xl shadow-violet-600/30 btn-glow"
          >
            <ChevronDown className="w-6 h-6 group-hover:translate-y-0.5 transition-transform" />
            <span className="absolute -bottom-8 text-xs text-slate-400 font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
              Explore
            </span>
          </button>
        </motion.div>
      </div>
    </section>
  );
}
