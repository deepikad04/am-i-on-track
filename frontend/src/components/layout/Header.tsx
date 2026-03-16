import { GraduationCap, Activity, LogOut, User } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

interface HeaderProps {
  connected: boolean;
}

export default function Header({ connected }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="h-14 border-b border-violet-100/50 bg-white/80 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <GraduationCap className="w-7 h-7 text-violet-600" />
        <h1 className="text-lg font-semibold text-slate-900">Am I On Track?</h1>
        <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">
          Powered by Amazon Nova
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Activity className={`w-4 h-4 ${connected ? 'text-green-500' : 'text-red-400'}`} />
          <span>{connected ? 'Nova Connected' : 'Disconnected'}</span>
        </div>
        {user && (
          <div className="flex items-center gap-3 border-l border-slate-200 pl-4">
            <div className="flex items-center gap-1.5 text-sm text-slate-700">
              <User className="w-4 h-4 text-slate-400" />
              <span className="font-medium">{user.name}</span>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-red-500 transition-colors"
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
