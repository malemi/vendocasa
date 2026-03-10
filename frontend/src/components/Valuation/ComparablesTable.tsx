import type { ComparableItem } from "../../types";

interface ComparablesTableProps {
  comparables: ComparableItem[];
}

export function ComparablesTable({ comparables }: ComparablesTableProps) {
  if (comparables.length === 0) {
    return (
      <p className="text-text-secondary text-sm">
        Nessuna transazione comparabile registrata
      </p>
    );
  }

  return (
    <div className="bg-bg-elevated rounded-lg p-3 border border-border">
      <h4 className="mb-2 text-sm text-text-secondary font-semibold">Transazioni comparabili</h4>
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Data</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Prezzo</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Cat.</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Consist.</th>
            <th className="text-left px-2 py-1.5 border-b-2 border-border text-text-tertiary font-semibold text-[0.7rem] uppercase">Note</th>
          </tr>
        </thead>
        <tbody>
          {comparables.map((c, i) => (
            <tr key={i}>
              <td className="px-2 py-1.5 border-b border-border-light text-text-primary">
                {c.transaction_date || "-"}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-right font-mono tabular-nums text-accent">
                {c.declared_price
                  ? new Intl.NumberFormat("it-IT", {
                      style: "currency",
                      currency: "EUR",
                      maximumFractionDigits: 0,
                    }).format(c.declared_price)
                  : "-"}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-text-primary">
                {c.cadastral_category || "-"}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-right font-mono tabular-nums text-text-primary">
                {c.cadastral_mq
                  ? `${c.cadastral_mq} m2`
                  : c.cadastral_vani
                    ? `${c.cadastral_vani} vani`
                    : "-"}
              </td>
              <td className="px-2 py-1.5 border-b border-border-light text-text-secondary">
                {c.notes ? (c.notes.length > 40 ? c.notes.slice(0, 40) + "..." : c.notes) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
