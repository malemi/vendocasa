interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "accent" | "teal" | "success" | "danger";
  className?: string;
}

const variantClasses: Record<string, string> = {
  default: "bg-bg-surface text-text-secondary border-border",
  accent: "bg-accent-muted text-accent border-accent/30",
  teal: "bg-teal-muted text-teal border-teal/30",
  success: "bg-success-muted text-success border-success/30",
  danger: "bg-danger-muted text-danger border-danger/30",
};

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center px-2.5 py-0.5
        text-xs font-semibold rounded-full border
        ${variantClasses[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  );
}
