import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/Layout/Header";
import { Sidebar } from "./components/Layout/Sidebar";
import { MapView } from "./components/Map/MapContainer";
import { ChatPanel } from "./components/Chat/ChatPanel";
import type { Coordinates } from "./types";

const queryClient = new QueryClient();

function AppContent() {
  const [mapCenter, setMapCenter] = useState<Coordinates | undefined>(undefined);

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
      <AppContent />
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
