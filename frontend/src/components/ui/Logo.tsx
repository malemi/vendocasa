interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = {
  sm: "text-xl",
  md: "text-2xl",
  lg: "text-4xl",
};

export function Logo({ size = "md", className = "" }: LogoProps) {
  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      {/* House icon */}
      <svg
        viewBox="0 0 32 32"
        fill="none"
        className={`${size === "sm" ? "w-6 h-6" : size === "md" ? "w-8 h-8" : "w-10 h-10"}`}
      >
        {/* Roof */}
        <path
          d="M16 4L3 15h4v12h18V15h4L16 4z"
          fill="var(--color-accent)"
          opacity="0.9"
        />
        {/* Door */}
        <rect x="13" y="19" width="6" height="8" rx="1" fill="var(--color-bg-primary)" />
        {/* Window left */}
        <rect x="8" y="17" width="4" height="4" rx="0.5" fill="var(--color-bg-primary)" opacity="0.7" />
        {/* Window right */}
        <rect x="20" y="17" width="4" height="4" rx="0.5" fill="var(--color-bg-primary)" opacity="0.7" />
        {/* Chimney accent */}
        <rect x="21" y="7" width="3" height="6" rx="0.5" fill="var(--color-accent)" opacity="0.6" />
      </svg>

      {/* Wordmark */}
      <span className={`font-bold tracking-tight ${sizeMap[size]}`}>
        <span className="text-text-primary">Vendo</span>
        <span className="text-accent">Casa</span>
      </span>
    </div>
  );
}
