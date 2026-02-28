import { Link } from "react-router-dom";

export function PrivacyPolicy() {
  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <Link to="/" style={styles.backLink}>
          &larr; Torna a VendoCasa
        </Link>

        <h1 style={styles.h1}>Informativa Privacy</h1>
        <p style={styles.lastUpdate}>Ultimo aggiornamento: febbraio 2026</p>

        <section style={styles.section}>
          <h2 style={styles.h2}>1. Titolare del Trattamento</h2>
          <p>
            VendoCasa è un progetto personale per la valutazione immobiliare
            basata sui dati OMI (Osservatorio del Mercato Immobiliare)
            dell'Agenzia delle Entrate. Il servizio è fornito a titolo gratuito
            e senza finalità commerciali.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>2. Dati Raccolti</h2>
          <p>Il servizio raccoglie i seguenti dati:</p>
          <ul style={styles.list}>
            <li>
              <strong>Cookie identificativo (vendocasa_uid):</strong> un
              identificatore univoco (UUID) assegnato al browser per
              riconoscere gli utenti e prevenire abusi del servizio. Durata: 1
              anno.
            </li>
            <li>
              <strong>Messaggi di chat:</strong> le domande inviate all'agente
              AI vengono elaborate in tempo reale per fornire risposte. Non
              vengono salvate in modo permanente.
            </li>
            <li>
              <strong>Indirizzo IP:</strong> registrato nei log del server per
              motivi di sicurezza e diagnostica.
            </li>
          </ul>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>3. Finalità del Trattamento</h2>
          <ul style={styles.list}>
            <li>Erogazione del servizio di valutazione immobiliare</li>
            <li>
              Prevenzione di abusi (identificazione e blocco di utilizzi
              impropri)
            </li>
            <li>Diagnostica e miglioramento del servizio</li>
          </ul>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>4. Base Giuridica</h2>
          <p>
            Il trattamento dei dati si basa sul <strong>consenso</strong>{" "}
            dell'utente (art. 6, par. 1, lett. a, GDPR) per quanto riguarda
            l'impostazione del cookie identificativo, e sul{" "}
            <strong>legittimo interesse</strong> del titolare (art. 6, par. 1,
            lett. f, GDPR) per la prevenzione di abusi e la sicurezza del
            servizio.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>5. Cookie Utilizzati</h2>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Nome</th>
                <th style={styles.th}>Tipo</th>
                <th style={styles.th}>Durata</th>
                <th style={styles.th}>Finalità</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={styles.td}>vendocasa_uid</td>
                <td style={styles.td}>Tecnico / Identificativo</td>
                <td style={styles.td}>1 anno</td>
                <td style={styles.td}>
                  Identificazione utente per prevenzione abusi
                </td>
              </tr>
              <tr>
                <td style={styles.td}>cookieConsent</td>
                <td style={styles.td}>Tecnico (localStorage)</td>
                <td style={styles.td}>Persistente</td>
                <td style={styles.td}>Memorizzazione del consenso cookie</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>6. Conservazione dei Dati</h2>
          <p>
            I log del server contenenti l'indirizzo IP e l'identificativo
            utente vengono conservati per un massimo di 90 giorni. I messaggi
            di chat non vengono memorizzati in modo permanente.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>7. Servizi di Terze Parti</h2>
          <p>
            Il servizio si avvale dei seguenti fornitori terzi per il suo
            funzionamento:
          </p>
          <ul style={styles.list}>
            <li>
              <strong>Anthropic (Claude AI):</strong> elaborazione delle
              risposte dell'agente AI. I messaggi vengono inviati ai server di
              Anthropic per la generazione delle risposte.
            </li>
            <li>
              <strong>Supabase:</strong> hosting del database PostgreSQL
              contenente i dati OMI.
            </li>
            <li>
              <strong>Railway:</strong> hosting del backend applicativo.
            </li>
            <li>
              <strong>Vercel:</strong> hosting del frontend.
            </li>
            <li>
              <strong>Nominatim (OpenStreetMap):</strong> geocodifica degli
              indirizzi.
            </li>
            <li>
              <strong>Google Geocoding API:</strong> geocodifica degli indirizzi
              come fallback.
            </li>
          </ul>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>8. Diritti dell'Utente</h2>
          <p>
            Ai sensi del GDPR (Regolamento UE 2016/679), l'utente ha diritto
            di:
          </p>
          <ul style={styles.list}>
            <li>Accedere ai propri dati personali</li>
            <li>Richiederne la rettifica o la cancellazione</li>
            <li>Opporsi al trattamento</li>
            <li>Richiedere la portabilità dei dati</li>
            <li>Revocare il consenso in qualsiasi momento</li>
          </ul>
          <p>
            Per esercitare questi diritti è possibile cancellare il cookie
            vendocasa_uid dalle impostazioni del browser, oppure contattare il
            titolare del trattamento.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>9. Contatti</h2>
          <p>
            Per qualsiasi domanda relativa alla privacy, è possibile aprire una
            issue sul{" "}
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              style={styles.link}
            >
              repository del progetto
            </a>
            .
          </p>
        </section>

        <div style={styles.footer}>
          <Link to="/" style={styles.link}>
            Torna a VendoCasa
          </Link>
          {" | "}
          <Link to="/terms" style={styles.link}>
            Termini di Utilizzo
          </Link>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    backgroundColor: "#f7fafc",
    padding: "40px 20px",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  } as React.CSSProperties,
  content: {
    maxWidth: "720px",
    margin: "0 auto",
    backgroundColor: "#fff",
    borderRadius: "12px",
    padding: "40px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  } as React.CSSProperties,
  backLink: {
    color: "#3182ce",
    textDecoration: "none",
    fontSize: "14px",
    display: "inline-block",
    marginBottom: "24px",
  } as React.CSSProperties,
  h1: {
    fontSize: "28px",
    fontWeight: 700,
    color: "#1a202c",
    margin: "0 0 8px 0",
  } as React.CSSProperties,
  lastUpdate: {
    fontSize: "13px",
    color: "#a0aec0",
    margin: "0 0 32px 0",
  } as React.CSSProperties,
  section: {
    marginBottom: "28px",
    lineHeight: 1.7,
    fontSize: "15px",
    color: "#2d3748",
  } as React.CSSProperties,
  h2: {
    fontSize: "18px",
    fontWeight: 600,
    color: "#2d3748",
    margin: "0 0 12px 0",
  } as React.CSSProperties,
  list: {
    paddingLeft: "24px",
    margin: "8px 0",
  } as React.CSSProperties,
  table: {
    width: "100%",
    borderCollapse: "collapse",
    margin: "12px 0",
    fontSize: "14px",
  } as React.CSSProperties,
  th: {
    textAlign: "left",
    padding: "8px 12px",
    backgroundColor: "#edf2f7",
    borderBottom: "2px solid #e2e8f0",
    fontWeight: 600,
    fontSize: "13px",
  } as React.CSSProperties,
  td: {
    padding: "8px 12px",
    borderBottom: "1px solid #e2e8f0",
  } as React.CSSProperties,
  link: {
    color: "#3182ce",
    textDecoration: "underline",
  } as React.CSSProperties,
  footer: {
    marginTop: "40px",
    paddingTop: "20px",
    borderTop: "1px solid #e2e8f0",
    textAlign: "center",
    fontSize: "14px",
    color: "#718096",
  } as React.CSSProperties,
};
