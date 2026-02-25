import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/Layout/Header";
import { Sidebar } from "./components/Layout/Sidebar";
import { AddressSearch } from "./components/Search/AddressSearch";
import { MapView } from "./components/Map/MapContainer";
import { ValuationCard } from "./components/Valuation/ValuationCard";
import { QuotationTable } from "./components/Valuation/QuotationTable";
import { ComparablesTable } from "./components/Valuation/ComparablesTable";
import { TransactionForm } from "./components/Transactions/TransactionForm";
import { valuate } from "./api/client";
import type { ValuationResponse } from "./types";

const queryClient = new QueryClient();

function AppContent() {
  const [valuation, setValuation] = useState<ValuationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (params: {
    address: string;
    property_type: number;
    surface_m2?: number;
  }) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await valuate(params);
      setValuation(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Errore nella valutazione. Verifica l'indirizzo.";
      setError(message);
      setValuation(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.app}>
      <Header />
      <div style={styles.content}>
        <Sidebar>
          <AddressSearch onSearch={handleSearch} isLoading={isLoading} />

          {error && <div style={styles.error}>{error}</div>}

          {valuation && (
            <>
              <ValuationCard data={valuation} />
              <QuotationTable quotations={valuation.quotations} />
              <ComparablesTable comparables={valuation.comparables} />
              <TransactionForm
                defaultLinkZona={valuation.zone.link_zona}
                defaultZoneCode={valuation.zone.zone_code}
                defaultMunicipality={valuation.zone.municipality || ""}
              />
            </>
          )}
        </Sidebar>
        <div style={styles.map}>
          <MapView
            center={valuation?.coordinates || undefined}
          />
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
  error: {
    padding: "10px 12px",
    backgroundColor: "#fed7d7",
    color: "#9b2c2c",
    borderRadius: "6px",
    fontSize: "0.85rem",
  } as React.CSSProperties,
};
