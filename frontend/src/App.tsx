import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/Layout/Header";
import { Sidebar } from "./components/Layout/Sidebar";
import { MapView } from "./components/Map/MapContainer";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { CookieBanner } from "./components/CookieBanner";
import { PrivacyPolicy } from "./pages/PrivacyPolicy";
import { TermsOfService } from "./pages/TermsOfService";
import type { Coordinates } from "./types";

const queryClient = new QueryClient();

function MainApp() {
  const [mapCenter, setMapCenter] = useState<Coordinates | undefined>(undefined);
  const [cookieConsent, setCookieConsent] = useState(
    () => localStorage.getItem("cookieConsent") === "true"
  );

  const handleAccept = () => {
    localStorage.setItem("cookieConsent", "true");
    setCookieConsent(true);
  };

  if (!cookieConsent) {
    return <CookieBanner onAccept={handleAccept} />;
  }

  return (
    <div style={styles.app}>
      <Header />
      <div style={styles.content}>
        <Sidebar>
          <ChatPanel onMapUpdate={setMapCenter} />
        </Sidebar>
        <div style={styles.map}>
          <MapView center={mapCenter} />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainApp />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const styles = {
  app: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  } as React.CSSProperties,
  content: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
  } as React.CSSProperties,
  map: {
    flex: 1,
  } as React.CSSProperties,
};
