import { useState, useCallback } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LandingPage } from "./components/Landing/LandingPage";
import { AppDrawer } from "./components/AppDrawer/AppDrawer";
import { MobileTabBar } from "./components/AppDrawer/MobileTabBar";
import { MapView } from "./components/Map/MapContainer";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { CookieBanner } from "./components/CookieBanner";
import { PrivacyPolicy } from "./pages/PrivacyPolicy";
import { TermsOfService } from "./pages/TermsOfService";
import type { Coordinates } from "./types";

const queryClient = new QueryClient();

function HomePage() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [mapCenter, setMapCenter] = useState<Coordinates | undefined>(undefined);
  const [mobileTab, setMobileTab] = useState<"chat" | "map">("chat");
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

  const handleMapUpdate = useCallback((coords: Coordinates) => {
    setMapCenter(coords);
    // On mobile, briefly switch to map tab when location is found
    setMobileTab("map");
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

      {/* App drawer (chat + map) — stays mounted for state preservation */}
      <AppDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      >
        {/* Desktop: side-by-side layout */}
        {/* Mobile: tab-switched (only one visible at a time) */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat sidebar */}
          <div className={`
            w-full md:w-[420px] lg:w-[480px] h-full flex flex-col
            bg-bg-elevated border-r border-border shrink-0
            ${mobileTab === "chat" ? "flex" : "hidden md:flex"}
          `}>
            <div className="flex-1 overflow-auto flex flex-col">
              <ChatPanel onMapUpdate={handleMapUpdate} />
            </div>
          </div>

          {/* Map */}
          <div className={`
            flex-1 h-full
            ${mobileTab === "map" ? "block" : "hidden md:block"}
          `}>
            <MapView center={mapCenter} />
          </div>
        </div>

        {/* Mobile tab bar */}
        <MobileTabBar activeTab={mobileTab} onTabChange={setMobileTab} />
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
