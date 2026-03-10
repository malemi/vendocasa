import { Link } from "react-router-dom";

export function PrivacyPolicy() {
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
          Informativa Privacy
        </h1>
        <p className="text-[13px] text-text-tertiary m-0 mb-8">
          Ultimo aggiornamento: febbraio 2026
        </p>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            1. Titolare del Trattamento
          </h2>
          <p>
            VendoCasa è un progetto personale per la valutazione immobiliare
            basata sui dati OMI (Osservatorio del Mercato Immobiliare)
            dell'Agenzia delle Entrate. Il servizio è fornito a titolo gratuito
            e senza finalità commerciali.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            2. Dati Raccolti
          </h2>
          <p>Il servizio raccoglie i seguenti dati:</p>
          <ul className="pl-6 my-2 space-y-1">
            <li>
              <strong className="text-text-primary">Cookie identificativo (vendocasa_uid):</strong> un
              identificatore univoco (UUID) assegnato al browser per
              riconoscere gli utenti e prevenire abusi del servizio. Durata: 1
              anno.
            </li>
            <li>
              <strong className="text-text-primary">Messaggi di chat:</strong> le domande inviate all'agente
              AI vengono elaborate in tempo reale per fornire risposte. Non
              vengono salvate in modo permanente.
            </li>
            <li>
              <strong className="text-text-primary">Indirizzo IP:</strong> registrato nei log del server per
              motivi di sicurezza e diagnostica.
            </li>
          </ul>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            3. Finalità del Trattamento
          </h2>
          <ul className="pl-6 my-2 space-y-1">
            <li>Erogazione del servizio di valutazione immobiliare</li>
            <li>
              Prevenzione di abusi (identificazione e blocco di utilizzi
              impropri)
            </li>
            <li>Diagnostica e miglioramento del servizio</li>
          </ul>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            4. Base Giuridica
          </h2>
          <p>
            Il trattamento dei dati si basa sul <strong className="text-text-primary">consenso</strong>{" "}
            dell'utente (art. 6, par. 1, lett. a, GDPR) per quanto riguarda
            l'impostazione del cookie identificativo, e sul{" "}
            <strong className="text-text-primary">legittimo interesse</strong> del titolare (art. 6, par. 1,
            lett. f, GDPR) per la prevenzione di abusi e la sicurezza del
            servizio.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            5. Cookie Utilizzati
          </h2>
          <div className="overflow-x-auto my-3">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="text-left p-2 px-3 bg-bg-surface border-b-2 border-border font-semibold text-[13px] text-text-secondary">
                    Nome
                  </th>
                  <th className="text-left p-2 px-3 bg-bg-surface border-b-2 border-border font-semibold text-[13px] text-text-secondary">
                    Tipo
                  </th>
                  <th className="text-left p-2 px-3 bg-bg-surface border-b-2 border-border font-semibold text-[13px] text-text-secondary">
                    Durata
                  </th>
                  <th className="text-left p-2 px-3 bg-bg-surface border-b-2 border-border font-semibold text-[13px] text-text-secondary">
                    Finalità
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 px-3 border-b border-border font-mono text-xs">vendocasa_uid</td>
                  <td className="p-2 px-3 border-b border-border">Tecnico / Identificativo</td>
                  <td className="p-2 px-3 border-b border-border">1 anno</td>
                  <td className="p-2 px-3 border-b border-border">
                    Identificazione utente per prevenzione abusi
                  </td>
                </tr>
                <tr>
                  <td className="p-2 px-3 border-b border-border font-mono text-xs">cookieConsent</td>
                  <td className="p-2 px-3 border-b border-border">Tecnico (localStorage)</td>
                  <td className="p-2 px-3 border-b border-border">Persistente</td>
                  <td className="p-2 px-3 border-b border-border">Memorizzazione del consenso cookie</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            6. Conservazione dei Dati
          </h2>
          <p>
            I log del server contenenti l'indirizzo IP e l'identificativo
            utente vengono conservati per un massimo di 90 giorni. I messaggi
            di chat non vengono memorizzati in modo permanente.
          </p>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            7. Servizi di Terze Parti
          </h2>
          <p>
            Il servizio si avvale dei seguenti fornitori terzi per il suo
            funzionamento:
          </p>
          <ul className="pl-6 my-2 space-y-1">
            <li>
              <strong className="text-text-primary">Anthropic (Claude AI):</strong> elaborazione delle
              risposte dell'agente AI. I messaggi vengono inviati ai server di
              Anthropic per la generazione delle risposte.
            </li>
            <li>
              <strong className="text-text-primary">Supabase:</strong> hosting del database PostgreSQL
              contenente i dati OMI.
            </li>
            <li>
              <strong className="text-text-primary">Railway:</strong> hosting del backend applicativo.
            </li>
            <li>
              <strong className="text-text-primary">Vercel:</strong> hosting del frontend.
            </li>
            <li>
              <strong className="text-text-primary">Nominatim (OpenStreetMap):</strong> geocodifica degli
              indirizzi.
            </li>
            <li>
              <strong className="text-text-primary">Google Geocoding API:</strong> geocodifica degli indirizzi
              come fallback.
            </li>
          </ul>
        </section>

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            8. Diritti dell'Utente
          </h2>
          <p>
            Ai sensi del GDPR (Regolamento UE 2016/679), l'utente ha diritto
            di:
          </p>
          <ul className="pl-6 my-2 space-y-1">
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

        <section className="mb-7 leading-[1.7] text-[15px] text-text-secondary">
          <h2 className="text-lg font-semibold text-text-primary m-0 mb-3">
            9. Contatti
          </h2>
          <p>
            Per qualsiasi domanda relativa alla privacy, è possibile aprire una
            issue sul{" "}
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent underline hover:text-accent-hover transition-colors"
            >
              repository del progetto
            </a>
            .
          </p>
        </section>

        <div className="mt-10 pt-5 border-t border-border text-center text-sm text-text-tertiary">
          <Link to="/" className="text-accent underline hover:text-accent-hover transition-colors">
            Torna a VendoCasa
          </Link>
          {" | "}
          <Link to="/terms" className="text-accent underline hover:text-accent-hover transition-colors">
            Termini di Utilizzo
          </Link>
        </div>
      </div>
    </div>
  );
}
