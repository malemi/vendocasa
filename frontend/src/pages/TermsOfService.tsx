import { Link } from "react-router-dom";

export function TermsOfService() {
  return (
    <div className="min-h-screen bg-bg-primary px-5 py-10">
      <div className="max-w-[720px] mx-auto bg-bg-elevated rounded-xl p-8 md:p-10 shadow-lg border border-border">
        <Link
          to="/"
          className="text-accent no-underline text-sm inline-block mb-6 hover:text-accent-hover transition-colors"
        >
          &larr; Torna a VendoCasa
        </Link>

        <h1 className="text-[28px] font-bold text-text-primary m-0 mb-2">
          Termini di Utilizzo
        </h1>
        <p className="text-[13px] text-text-tertiary m-0 mb-8">
          Ultimo aggiornamento: febbraio 2026
        </p>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            1. Descrizione del Servizio
          </h2>
          <p>
            VendoCasa è uno strumento personale per la valutazione indicativa di
            immobili in Italia, basato sui dati pubblici dell'Osservatorio del
            Mercato Immobiliare (OMI) dell'Agenzia delle Entrate. Il servizio
            è fornito gratuitamente e senza finalità commerciali.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            2. Natura Indicativa delle Valutazioni
          </h2>
          <p>
            <strong className="text-text-primary">
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

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            3. Esclusione di Garanzia
          </h2>
          <p>
            Il servizio è fornito "così com'è" (<em>as is</em>), senza alcuna
            garanzia, esplicita o implicita. In particolare:
          </p>
          <ul className="pl-6 my-2 space-y-1">
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

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            4. Limitazione di Responsabilità
          </h2>
          <p>
            Il titolare del servizio non è responsabile per eventuali danni
            diretti o indiretti derivanti dall'utilizzo delle valutazioni
            fornite, incluse ma non limitate a decisioni di acquisto, vendita
            o investimento immobiliare prese sulla base dei dati presentati.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            5. Uso Consentito
          </h2>
          <p>L'utente si impegna a:</p>
          <ul className="pl-6 my-2 space-y-1">
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

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            6. Blocco per Abuso
          </h2>
          <p>
            Il titolare si riserva il diritto di bloccare l'accesso al servizio
            per gli utenti che ne facciano un uso improprio o abusivo, come
            identificato tramite il cookie tecnico (vendocasa_uid). Il blocco
            può avvenire senza preavviso in caso di violazioni evidenti dei
            presenti termini.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            7. Proprietà Intellettuale
          </h2>
          <p>
            Il codice sorgente di VendoCasa è di proprietà del suo autore. I
            dati OMI sono di proprietà dell'Agenzia delle Entrate e vengono
            utilizzati secondo le condizioni di pubblicazione dell'Osservatorio
            del Mercato Immobiliare.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            8. Attribuzione Fonti Dati
          </h2>
          <p>
            I dati di valutazione immobiliare provengono dall'
            <strong className="text-text-primary">
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

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            9. Modifiche ai Termini
          </h2>
          <p>
            Il titolare si riserva il diritto di modificare i presenti termini
            in qualsiasi momento. Le modifiche saranno efficaci dal momento
            della pubblicazione su questa pagina. L'uso continuato del servizio
            dopo la pubblicazione delle modifiche costituisce accettazione dei
            nuovi termini.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            10. Legge Applicabile
          </h2>
          <p>
            I presenti termini sono regolati dalla legge italiana. Per qualsiasi
            controversia è competente il foro del luogo di residenza del
            titolare del servizio.
          </p>
        </section>

        <div className="mt-10 pt-5 border-t border-border text-center text-sm text-text-tertiary">
          <Link to="/" className="text-accent underline hover:text-accent-hover transition-colors">
            Torna a VendoCasa
          </Link>
          {" | "}
          <Link to="/privacy" className="text-accent underline hover:text-accent-hover transition-colors">
            Informativa Privacy
          </Link>
        </div>
      </div>
    </div>
  );
}
