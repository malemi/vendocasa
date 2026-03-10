import { useState, useCallback } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LandingPage } from "./components/Landing/LandingPage";
import { AppDrawer } from "./components/AppDrawer/AppDrawer";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { CookieBanner } from "./components/CookieBanner";
import { PrivacyPolicy } from "./pages/PrivacyPolicy";
import { TermsOfService } from "./pages/TermsOfService";

const queryClient = new QueryClient();

function HomePage() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [cookieConsent, setCookieConsent] = useState(
    () => localStorage.getItem("cookieConsent") === "true"
  );
  const [showCookieBanner, setShowCookieBanner] = useState(false);

  const handleOpenApp = useCallback(() => {
    if (!cookieConsent) {
      setShowCookieBanner(true);
    } else {
      setIsDrawerOpen(true);
    }
  }, [cookieConsent]);

  const handleAcceptCookies = useCallback(() => {
    localStorage.setItem("cookieConsent", "true");
    setCookieConsent(true);
    setShowCookieBanner(false);
    setIsDrawerOpen(true);
  }, []);

  const handleDeclineCookies = useCallback(() => {
    setShowCookieBanner(false);
  }, []);

  return (
    <>
      {/* Landing page (always visible behind drawer) */}
      <LandingPage onOpenApp={handleOpenApp} />

      {/* Cookie banner (shown when trying to open app without consent) */}
      {showCookieBanner && (
        <CookieBanner
          onAccept={handleAcceptCookies}
          onDecline={handleDeclineCookies}
        />
      )}

      {/* Chat overlay — stays mounted for state preservation */}
      <AppDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      >
        <ChatPanel />
      </AppDrawer>
    </>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
