# Legal Considerations

Scope: data-use constraints for the OMI quotations and the declared transaction values that VendoCasa shows to registered users, and the personal data the service keeps. This page records checked facts and the operator's decisions. It is not legal advice.

## Operator decision

VendoCasa is an open product: anyone can register and receive the valuation information. The transaction data, including declared prices and cadastral attributes, is public information that registered users receive. The operator decided this on 2026-11-23; it is decision 1 of the workstream's brief, an internal document that is not published.

## OMI quotation CSVs

- **Source:** downloadable from the Agenzia delle Entrate portal after SPID authentication.
- **License:** no explicit open license is attached to the download. As public administration data, the quotations are arguably covered by the open-by-default principle of art. 52 of the Codice dell'Amministrazione Digitale (D.Lgs. 82/2005).
- **Attribution:** cite the source as "Agenzia delle Entrate -- OMI". The landing page and its footer do; the chat cards do not.

## Declared transaction values

- **Source:** the Agenzia delle Entrate's "Consultazione Valori Immobiliari Dichiarati" service. The owner enters the records by hand; only the owner account can create, change or delete them.
- **The former reuse ban.** Legge 311/2004, art. 1, comma 367 banned the commercial reuse of cadastral and mortgage data. It was repealed with effect from 1 September 2011 by D.L. 70/2011, art. 5, comma 4-bis, added on conversion by Legge 106/2011. This rests on secondary sources: [Ipsoa, 2011-09-09](https://www.ipsoa.it/documents/quotidiano/2011/09/09/dati-ipotecari-e-catastali-abolito-il-divieto-di-riutilizzazione-commerciale) and Fiscal Focus. Commi 368-373 regulated reuse under that ban. Nobody has examined their current text.
- **Public-sector data reuse.** The current [art. 3 of D.Lgs. 36/2006](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2006-01-24;36~art3) excludes neither cadastral data nor declared values from reuse. Its closest exclusion, letter h-quater, concerns personal data.
- **The service's own terms.** The Agenzia's [data-use notice of September 2024](https://agenziaentrate.gov.it/portale/documents/20143/2974856/ConsultazioneValoriImmobiliariDichiarati_INFO+UTILIZZO+DATI_agg_settembre_2024.pdf/a98f5111-8e3a-9825-a1a5-a7834e325c54) states no restriction on reuse.
- **Anonymization.** The Agenzia anonymizes at source: it shows deed cards only for areas with at least five deeds, and they cannot be linked to points on the map. VendoCasa's records keep zone-level attributes with no address or cadastral identifier. The free-text `notes` column is the exception.
- **Collection.** The service has no API. Consultation is rate-limited: above 10 queries a minute it shows a captcha, and an account that exceeds that limit in more than five sessions is suspended for 30 days. Records are therefore entered by hand.
- **Not examined:** the Agenzia portal's general legal notes.

These facts were checked on 2026-11-24.

## Personal data the service keeps

- **Account emails.** They are stored by the identity service, Supabase Auth, for as long as the account exists.
- **Spending records.** `app.spend_month` and `app.spend_reservation` hold account IDs and amounts, and no conversation content. They are kept until deleted, and no deletion schedule is configured.
- **Uploaded documents.** They stay in the backend's memory for at most 30 minutes, and a restart deletes them.
- **Chat messages.** They are not stored by the backend. They are sent to the model provider for each request.

Retention periods are the operator's decision.
