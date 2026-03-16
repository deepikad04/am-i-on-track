import { motion } from 'framer-motion';
import { GraduationCap, Trophy, ScrollText, BookOpen, Sparkles, Target } from 'lucide-react';

export default function FloatingElements() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      {/* Graduation Cap — top left */}
      <motion.div
        className="absolute top-16 left-[8%]"
        animate={{ y: [0, -20, 0], rotate: [-12, -8, -12] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
      >
        <GraduationCap className="w-28 h-28 text-violet-500/[0.10] stroke-[1]" />
      </motion.div>

      {/* Trophy — bottom left */}
      <motion.div
        className="absolute bottom-32 left-[5%]"
        animate={{ y: [0, -16, 0], rotate: [12, 16, 12] }}
        transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 0.7 }}
      >
        <Trophy className="w-24 h-24 text-fuchsia-500/[0.12] stroke-[1]" />
      </motion.div>

      {/* Scroll/Diploma — top right */}
      <motion.div
        className="absolute top-32 right-[8%]"
        animate={{ y: [0, -18, 0], rotate: [-20, -16, -20] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
      >
        <ScrollText className="w-24 h-24 text-cyan-400/[0.12] stroke-[1]" />
      </motion.div>

      {/* Book — bottom right */}
      <motion.div
        className="absolute bottom-24 right-[6%]"
        animate={{ y: [0, -14, 0], rotate: [8, 12, 8] }}
        transition={{ duration: 6.5, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
      >
        <BookOpen className="w-28 h-28 text-violet-400/[0.10] stroke-[1]" />
      </motion.div>

      {/* Sparkles — mid left */}
      <motion.div
        className="absolute top-1/2 left-[15%] -translate-y-1/2"
        animate={{ y: [0, -10, 0], scale: [1, 1.1, 1] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }}
      >
        <Sparkles className="w-16 h-16 text-fuchsia-400/[0.12] stroke-[1]" />
      </motion.div>

      {/* Target — mid right */}
      <motion.div
        className="absolute top-1/3 right-[12%]"
        animate={{ y: [0, -12, 0], scale: [1, 1.05, 1] }}
        transition={{ duration: 7.5, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
      >
        <Target className="w-20 h-20 text-cyan-500/[0.10] stroke-[1]" />
      </motion.div>

      {/* Large glow orbs */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-violet-200/20 rounded-full blur-[120px]" />
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-fuchsia-200/15 rounded-full blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 w-[350px] h-[350px] bg-cyan-200/15 rounded-full blur-[100px]" />
    </div>
  );
}
