import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/Layout/Header";
import { Sidebar } from "./components/Layout/Sidebar";
import { AddressSearch } from "./components/Search/AddressSearch";
import { MapView } from "./components/Map/MapContainer";
import { ValuationCard } from "./components/Valuation/ValuationCard";
import { QuotationTable } from "./components/Valuation/QuotationTable";
import { ComparablesTable } from "./components/Valuation/ComparablesTable";
import { CoefficientWizard } from "./components/Valuation/CoefficientWizard";
import { AgentIncentives } from "./components/Education/AgentIncentives";
import { TransactionForm } from "./components/Transactions/TransactionForm";
import { valuate, enhancedValuate } from "./api/client";
import type { ValuationResponse, EnhancedValuationResponse, PropertyDetails } from "./types";

const queryClient = new QueryClient();

function AppContent() {
  const [valuation, setValuation] = useState<ValuationResponse | null>(null);
  const [enhancedResult, setEnhancedResult] = useState<EnhancedValuationResponse | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isEnhancedLoading, setIsEnhancedLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useState<{
    address: string;
    property_type: number;
    surface_m2?: number;
  } | null>(null);

  const handleSearch = async (params: {
    address: string;
    property_type: number;
    surface_m2?: number;
  }) => {
    setIsLoading(true);
    setError(null);
    setEnhancedResult(null);
    setShowWizard(false);
    setSearchParams(params);
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

  const handleEnhancedSubmit = async (details: PropertyDetails) => {
    if (!searchParams || !valuation) return;

    setIsEnhancedLoading(true);
    try {
      const result = await enhancedValuate({
        address: searchParams.address,
        surface_m2: searchParams.surface_m2 || 0,
        property_type: searchParams.property_type,
        details,
      });
      setEnhancedResult(result);
    } catch (err: unknown) {
      console.error("Enhanced valuation error:", err);
      // Wizard will show client-side calculation as fallback
    } finally {
      setIsEnhancedLoading(false);
    }
  };

  // Determine the estimated value for the AgentIncentives math
  const estimatedValue = enhancedResult?.adjusted_estimate?.total_mid
    || valuation?.estimate?.mid
    || undefined;

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

              {/* Wizard trigger */}
              {!showWizard && valuation.estimate && (
                <button
                  style={styles.refineBtn}
                  onClick={() => setShowWizard(true)}
                >
                  Affina la valutazione con i coefficienti correttivi
                </button>
              )}

              {/* Coefficient Wizard */}
              {showWizard && (
                <CoefficientWizard
                  basicValuation={valuation}
                  onResult={setEnhancedResult}
                  isLoading={isEnhancedLoading}
                  onSubmit={handleEnhancedSubmit}
                />
              )}

              {/* Agent Incentives Education (shown after wizard) */}
              {showWizard && (
                <AgentIncentives estimatedValue={estimatedValue} />
              )}

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
  refineBtn: {
    width: "100%",
    padding: "10px 16px",
    backgroundColor: "#ebf8ff",
    color: "#2b6cb0",
    border: "2px dashed #90cdf4",
    borderRadius: "6px",
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.15s",
  } as React.CSSProperties,
};
