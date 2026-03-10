import { HeroSection } from "./HeroSection";
import { HowItWorks } from "./HowItWorks";
import { FreakonomicsSection } from "./FreakonomicsSection";
import { TrustSection } from "./TrustSection";
import { CtaSection } from "./CtaSection";
import { Footer } from "./Footer";

interface LandingPageProps {
  onOpenApp: () => void;
}

export function LandingPage({ onOpenApp }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-bg-primary text-text-primary overflow-y-auto">
      <HeroSection onOpenApp={onOpenApp} />
      <HowItWorks />
      <FreakonomicsSection onOpenApp={onOpenApp} />
      <TrustSection />
      <CtaSection onOpenApp={onOpenApp} />
      <Footer />
    </div>
  );
}
