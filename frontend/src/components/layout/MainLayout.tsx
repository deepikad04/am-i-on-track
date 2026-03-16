import { ReactNode } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import FloatingElements from '../landing/FloatingElements';

interface MainLayoutProps {
  children: ReactNode;
  activeSection: string;
  onSectionChange: (section: string) => void;
  hasDegreeParsed: boolean;
  connected: boolean;
}

export default function MainLayout({
  children,
  activeSection,
  onSectionChange,
  hasDegreeParsed,
  connected,
}: MainLayoutProps) {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header connected={connected} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeSection={activeSection}
          onSectionChange={onSectionChange}
          hasDegreeParsed={hasDegreeParsed}
        />
        <main className="flex-1 overflow-auto bg-slate-50 p-6 relative mesh-bg">
          <FloatingElements />
          <div className="relative z-10 h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
