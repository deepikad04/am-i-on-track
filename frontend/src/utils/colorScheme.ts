import { CheckCircle2, Clock, Lock, AlertTriangle, Star } from 'lucide-react';
import type { CourseStatus } from '../types/degree';

export const statusIcons: Record<CourseStatus, typeof CheckCircle2> = {
  completed: CheckCircle2,
  scheduled: Clock,
  locked: Lock,
  bottleneck: AlertTriangle,
  elective: Star,
};

export const statusColors: Record<CourseStatus, { bg: string; border: string; borderLeft: string; text: string; badge: string }> = {
  completed: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-400',
    borderLeft: 'border-l-emerald-400',
    text: 'text-emerald-800',
    badge: 'bg-emerald-500',
  },
  scheduled: {
    bg: 'bg-violet-50',
    border: 'border-violet-400',
    borderLeft: 'border-l-violet-400',
    text: 'text-violet-800',
    badge: 'bg-violet-500',
  },
  elective: {
    bg: 'bg-amber-50',
    border: 'border-amber-400',
    borderLeft: 'border-l-amber-400',
    text: 'text-amber-800',
    badge: 'bg-amber-500',
  },
  bottleneck: {
    bg: 'bg-rose-50',
    border: 'border-rose-400',
    borderLeft: 'border-l-rose-400',
    text: 'text-rose-800',
    badge: 'bg-rose-500',
  },
  locked: {
    bg: 'bg-slate-50',
    border: 'border-slate-300',
    borderLeft: 'border-l-slate-300',
    text: 'text-slate-500',
    badge: 'bg-slate-400',
  },
};

export const statusLabels: Record<CourseStatus, string> = {
  completed: 'Completed',
  scheduled: 'Scheduled',
  elective: 'Elective',
  bottleneck: 'Bottleneck',
  locked: 'Locked',
};
