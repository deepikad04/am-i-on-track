import { useRef } from 'react';
import Hero from './Hero';
import Features from './Features';

interface LandingPageProps {
  onGetStarted: () => void;
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  const featuresRef = useRef<HTMLDivElement>(null);

  const scrollToFeatures = () => {
    featuresRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-violet-50/30 mesh-bg">
      <Hero onScrollDown={scrollToFeatures} />
      <div ref={featuresRef}>
        <Features onGetStarted={onGetStarted} />
      </div>
    </div>
  );
}
