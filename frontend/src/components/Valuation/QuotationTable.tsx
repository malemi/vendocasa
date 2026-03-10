import type { QuotationItem } from "../../types";

interface QuotationTableProps {
  quotations: QuotationItem[];
}

export function QuotationTable({ quotations }: QuotationTableProps) {
  if (quotations.length === 0) {
    return <p className="text-text-secondary text-sm">Nessuna quotazione disponibile</p>;
  }

  return (
    <div className="bg-bg-elevated rounded-lg p-3 border border-border">
      <h4 className="mb-2 text-sm text-text-secondary font-semibold">Quotazioni OMI</h4>
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Stato conserv.</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">EUR/m2 min</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">EUR/m2 max</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Sup.</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Affitto min</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Affitto max</th>
          </tr>
        </thead>
        <tbody>
          {quotations.map((q, i) => (
            <tr key={i} className={q.is_prevalent ? "bg-accent-muted" : undefined}>
              <td className="px-2 py-1.5 border-b border-border-light text-text-primary">
                {q.conservation_state}
                {q.is_prevalent && (
                  <span className="ml-1.5 px-1.5 py-px bg-accent-muted text-accent rounded text-[0.65rem] font-bold">
                    P
                  </span>
                )}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-right font-mono tabular-nums text-accent">
                {q.price_min?.toLocaleString("it-IT")}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-right font-mono tabular-nums text-accent">
                {q.price_max?.toLocaleString("it-IT")}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-text-primary">
                {q.surface_type_sale}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-right font-mono tabular-nums text-text-primary">
                {q.rent_min?.toLocaleString("it-IT")}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-right font-mono tabular-nums text-text-primary">
                {q.rent_max?.toLocaleString("it-IT")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
