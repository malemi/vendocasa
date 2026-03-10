import { useState } from "react";
import { PROPERTY_TYPES } from "../../types";

interface AddressSearchProps {
  onSearch: (params: {
    address: string;
    property_type: number;
    surface_m2?: number;
  }) => void;
  isLoading: boolean;
}

export function AddressSearch({ onSearch, isLoading }: AddressSearchProps) {
  const [address, setAddress] = useState("");
  const [propertyType, setPropertyType] = useState(20);
  const [surfaceM2, setSurfaceM2] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    onSearch({
      address: address.trim(),
      property_type: propertyType,
      surface_m2: surfaceM2 ? parseFloat(surfaceM2) : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <label className="text-[0.8rem] font-semibold text-text-secondary uppercase tracking-wide">
          Indirizzo
        </label>
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Via Roma 1, Milano"
          className="px-3 py-2 border border-border rounded-md text-[0.95rem] outline-none bg-bg-surface text-text-primary placeholder:text-text-tertiary focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors"
        />
      </div>

      <div className="flex gap-3">
        <div className="flex flex-col gap-1 flex-1">
          <label className="text-[0.8rem] font-semibold text-text-secondary uppercase tracking-wide">
            Tipo immobile
          </label>
          <select
            value={propertyType}
            onChange={(e) => setPropertyType(parseInt(e.target.value))}
            className="px-3 py-2 border border-border rounded-md text-[0.95rem] outline-none bg-bg-surface text-text-primary focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors"
          >
            {PROPERTY_TYPES.map((pt) => (
              <option key={pt.code} value={pt.code}>
                {pt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1 w-[120px]">
          <label className="text-[0.8rem] font-semibold text-text-secondary uppercase tracking-wide">
            Superficie m2
          </label>
          <input
            type="number"
            value={surfaceM2}
            onChange={(e) => setSurfaceM2(e.target.value)}
            placeholder="80"
            min="1"
            className="px-3 py-2 border border-border rounded-md text-[0.95rem] outline-none bg-bg-surface text-text-primary placeholder:text-text-tertiary focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading || !address.trim()}
        className="px-4 py-2.5 bg-accent text-bg-primary border-none rounded-md text-base font-semibold cursor-pointer hover:bg-accent-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {isLoading ? "Ricerca..." : "Valuta"}
      </button>
    </form>
  );
}
