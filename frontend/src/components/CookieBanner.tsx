import { useState } from "react";

interface CookieBannerProps {
  onAccept: () => void;
}

export function CookieBanner({ onAccept }: CookieBannerProps) {
  const [declined, setDeclined] = useState(false);

  if (declined) {
    return (
      <div style={styles.overlay}>
        <div style={styles.card}>
          <p style={styles.blockMessage}>
            Mi spiace, per motivi di sicurezza questo servizio non pu&ograve;
            funzionare senza il settaggio di cookie. Capiamo perfettamente le
            sue preferenze, ma non possiamo continuare. Arrivederci.
          </p>
          <button
            onClick={() => setDeclined(false)}
            style={styles.linkButton}
          >
            &larr; Torna indietro
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        <h2 style={styles.title}>Cookie e Privacy</h2>
        <p style={styles.text}>
          Questo sito utilizza cookie tecnici per il funzionamento del servizio
          e per identificare eventuali abusi. Proseguendo, accetti l'utilizzo
          dei cookie come descritto nella nostra{" "}
          <a href="/privacy" style={styles.link}>
            Informativa Privacy
          </a>{" "}
          e nei{" "}
          <a href="/terms" style={styles.link}>
            Termini di Utilizzo
          </a>
          .
        </p>
        <div style={styles.buttons}>
          <button onClick={onAccept} style={styles.acceptButton}>
            Accetto
          </button>
          <button
            onClick={() => setDeclined(true)}
            style={styles.declineButton}
          >
            Rifiuto
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 10000,
  } as React.CSSProperties,
  card: {
    background: "#fff",
    borderRadius: "12px",
    padding: "32px 40px",
    maxWidth: "500px",
    width: "90%",
    boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
    textAlign: "center",
  } as React.CSSProperties,
  title: {
    margin: "0 0 16px 0",
    fontSize: "20px",
    fontWeight: 600,
    color: "#1a202c",
  } as React.CSSProperties,
  text: {
    fontSize: "14px",
    lineHeight: 1.6,
    color: "#4a5568",
    margin: "0 0 24px 0",
  } as React.CSSProperties,
  link: {
    color: "#3182ce",
    textDecoration: "underline",
  } as React.CSSProperties,
  buttons: {
    display: "flex",
    gap: "12px",
    justifyContent: "center",
  } as React.CSSProperties,
  acceptButton: {
    padding: "10px 32px",
    fontSize: "14px",
    fontWeight: 600,
    color: "#fff",
    backgroundColor: "#3182ce",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
  } as React.CSSProperties,
  declineButton: {
    padding: "10px 32px",
    fontSize: "14px",
    fontWeight: 600,
    color: "#4a5568",
    backgroundColor: "#edf2f7",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
  } as React.CSSProperties,
  blockMessage: {
    fontSize: "15px",
    lineHeight: 1.7,
    color: "#2d3748",
    margin: "0 0 24px 0",
    fontStyle: "italic",
  } as React.CSSProperties,
  linkButton: {
    background: "none",
    border: "none",
    color: "#3182ce",
    cursor: "pointer",
    fontSize: "14px",
    textDecoration: "underline",
    padding: 0,
  } as React.CSSProperties,
};
