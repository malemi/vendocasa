import { Link } from "react-router-dom";

export function TermsOfService() {
  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <Link to="/" style={styles.backLink}>
          &larr; Torna a VendoCasa
        </Link>

        <h1 style={styles.h1}>Termini di Utilizzo</h1>
        <p style={styles.lastUpdate}>Ultimo aggiornamento: febbraio 2026</p>

        <section style={styles.section}>
          <h2 style={styles.h2}>1. Descrizione del Servizio</h2>
          <p>
            VendoCasa è uno strumento personale per la valutazione indicativa di
            immobili in Italia, basato sui dati pubblici dell'Osservatorio del
            Mercato Immobiliare (OMI) dell'Agenzia delle Entrate. Il servizio
            è fornito gratuitamente e senza finalità commerciali.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>2. Natura Indicativa delle Valutazioni</h2>
          <p>
            <strong>
              Le valutazioni fornite da VendoCasa sono puramente indicative e
              non costituiscono perizie professionali.
            </strong>
          </p>
          <p>
            I range di prezzo si basano sui dati OMI, che rappresentano valori
            medi di mercato per zone omogenee. Il valore effettivo di un
            immobile dipende da numerosi fattori specifici (stato di
            conservazione, piano, esposizione, vista, rumorosità, ecc.) che
            non possono essere valutati automaticamente.
          </p>
          <p>
            Per una valutazione professionale, si consiglia di rivolgersi a un
            perito o agente immobiliare qualificato.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>3. Esclusione di Garanzia</h2>
          <p>
            Il servizio è fornito "così com'è" (<em>as is</em>), senza alcuna
            garanzia, esplicita o implicita. In particolare:
          </p>
          <ul style={styles.list}>
            <li>
              Non si garantisce l'accuratezza, completezza o aggiornamento dei
              dati OMI
            </li>
            <li>
              Non si garantisce il funzionamento ininterrotto del servizio
            </li>
            <li>
              Non si garantisce l'accuratezza delle risposte dell'agente AI
            </li>
          </ul>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>4. Limitazione di Responsabilità</h2>
          <p>
            Il titolare del servizio non è responsabile per eventuali danni
            diretti o indiretti derivanti dall'utilizzo delle valutazioni
            fornite, incluse ma non limitate a decisioni di acquisto, vendita
            o investimento immobiliare prese sulla base dei dati presentati.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>5. Uso Consentito</h2>
          <p>L'utente si impegna a:</p>
          <ul style={styles.list}>
            <li>
              Utilizzare il servizio esclusivamente per consultazione personale
            </li>
            <li>Non effettuare scraping automatizzato dei dati</li>
            <li>
              Non ridistribuire i dati a fini commerciali
            </li>
            <li>Non sovraccaricare il servizio con richieste massive</li>
            <li>
              Non tentare di aggirare le misure di sicurezza del servizio
            </li>
          </ul>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>6. Blocco per Abuso</h2>
          <p>
            Il titolare si riserva il diritto di bloccare l'accesso al servizio
            per gli utenti che ne facciano un uso improprio o abusivo, come
            identificato tramite il cookie tecnico (vendocasa_uid). Il blocco
            può avvenire senza preavviso in caso di violazioni evidenti dei
            presenti termini.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>7. Proprietà Intellettuale</h2>
          <p>
            Il codice sorgente di VendoCasa è di proprietà del suo autore. I
            dati OMI sono di proprietà dell'Agenzia delle Entrate e vengono
            utilizzati secondo le condizioni di pubblicazione dell'Osservatorio
            del Mercato Immobiliare.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>8. Attribuzione Fonti Dati</h2>
          <p>
            I dati di valutazione immobiliare provengono dall'
            <strong>
              Osservatorio del Mercato Immobiliare (OMI) dell'Agenzia delle
              Entrate
            </strong>
            . Tali dati sono pubblici e vengono aggiornati semestralmente.
          </p>
          <p>
            La geocodifica degli indirizzi utilizza i servizi di OpenStreetMap
            (Nominatim) e Google Geocoding API.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>9. Modifiche ai Termini</h2>
          <p>
            Il titolare si riserva il diritto di modificare i presenti termini
            in qualsiasi momento. Le modifiche saranno efficaci dal momento
            della pubblicazione su questa pagina. L'uso continuato del servizio
            dopo la pubblicazione delle modifiche costituisce accettazione dei
            nuovi termini.
          </p>
        </section>

        <section style={styles.section}>
          <h2 style={styles.h2}>10. Legge Applicabile</h2>
          <p>
            I presenti termini sono regolati dalla legge italiana. Per qualsiasi
            controversia è competente il foro del luogo di residenza del
            titolare del servizio.
          </p>
        </section>

        <div style={styles.footer}>
          <Link to="/" style={styles.link}>
            Torna a VendoCasa
          </Link>
          {" | "}
          <Link to="/privacy" style={styles.link}>
            Informativa Privacy
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
