import { useState, useCallback, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LandingPage } from "./components/Landing/LandingPage";
import { AppDrawer } from "./components/AppDrawer/AppDrawer";
import { ChatPanel } from "./components/Chat/ChatPanel";
import { CookieBanner } from "./components/CookieBanner";
import { SignInPanel } from "./components/Auth/SignInPanel";
import { signOut, useSession } from "./hooks/useSession";
import { PrivacyPolicy } from "./pages/PrivacyPolicy";
import { TermsOfService } from "./pages/TermsOfService";

const queryClient = new QueryClient();

function HomePage() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [cookieConsent, setCookieConsent] = useState(
    () => localStorage.getItem("cookieConsent") === "true"
  );
  const [showCookieBanner, setShowCookieBanner] = useState(false);
  const { session, ready, arrivedFromSignInLink } = useSession();
  // Why the user must sign in again, shown on the sign-in panel.
  const [signInNotice, setSignInNotice] = useState<string | null>(null);

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

  // Coming back from a sign-in link: open the app straight away.
  useEffect(() => {
    if (ready && session && arrivedFromSignInLink) handleOpenApp();
    // Run once, when the stored or linked session has been read.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  const handleSessionLost = useCallback((message: string) => {
    setSignInNotice(message);
    void signOut();
  }, []);

  const handleSignOut = useCallback(() => {
    setSignInNotice(null);
    void signOut();
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
        onSignOut={session ? handleSignOut : undefined}
      >
        {session ? (
          <ChatPanel onSessionLost={handleSessionLost} />
        ) : (
          <SignInPanel notice={signInNotice} />
        )}
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
