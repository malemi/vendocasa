interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "accent" | "success" | "danger";
}

const variantClasses: Record<string, string> = {
  default: "bg-bg-elevated border-border",
  accent: "bg-accent-muted border-accent/30",
  success: "bg-success-muted border-success/30",
  danger: "bg-danger-muted border-danger/30",
};

export function Card({ children, className = "", variant = "default" }: CardProps) {
  return (
    <div
      className={`rounded-xl border p-4 ${variantClasses[variant]} ${className}`}
    >
      {children}
    </div>
  );
}
