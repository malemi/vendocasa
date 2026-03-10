import { type ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-bg-primary font-semibold hover:bg-accent-hover " +
    "shadow-[0_0_20px_rgba(247,166,0,0.25)] hover:shadow-[0_0_30px_rgba(247,166,0,0.4)] " +
    "active:scale-[0.98] transition-all duration-200",
  secondary:
    "bg-bg-surface text-text-primary border border-border " +
    "hover:border-border-light hover:bg-bg-elevated " +
    "active:scale-[0.98] transition-all duration-200",
  ghost:
    "bg-transparent text-text-secondary hover:text-text-primary " +
    "hover:bg-bg-surface/50 transition-all duration-200",
  danger:
    "bg-danger-muted text-danger border border-danger/30 " +
    "hover:bg-danger/20 active:scale-[0.98] transition-all duration-200",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-4 py-2 text-sm rounded-lg",
  md: "px-6 py-3 text-base rounded-xl",
  lg: "px-8 py-4 text-lg rounded-2xl",
};

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className = "",
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2
        font-medium cursor-pointer select-none
        disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${fullWidth ? "w-full" : ""}
        ${className}
      `}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
