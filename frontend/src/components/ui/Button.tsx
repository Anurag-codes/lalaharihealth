import Link from "next/link";
import { clsx } from "clsx";

export type Variant = "primary" | "secondary" | "outline" | "outline-white" | "ghost" | "white";
export type Size = "sm" | "md" | "lg";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-primary text-white shadow-lg shadow-primary/25 hover:bg-primary-dark hover:shadow-primary/35",
  secondary: "bg-ink text-white hover:bg-ink/90",
  outline: "border-2 border-primary text-primary-darker hover:bg-primary-light",
  "outline-white": "border-2 border-white text-white hover:bg-white/10",
  ghost: "text-ink hover:bg-primary-light hover:text-primary-darker",
  white: "bg-white text-primary-darker shadow-lg hover:bg-white/90",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-6 py-3 text-sm sm:text-base",
  lg: "px-8 py-4 text-base sm:text-lg",
};

export function getButtonClasses(
  variant: Variant = "primary",
  size: Size = "md",
  className?: string,
) {
  return clsx(
    "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-200 active:scale-[0.97]",
    variantClasses[variant],
    sizeClasses[size],
    className,
  );
}

type BaseProps = {
  variant?: Variant;
  size?: Size;
  className?: string;
  children: React.ReactNode;
};

type ButtonAsLink = BaseProps & {
  href: string;
  onClick?: never;
};

type ButtonAsButton = BaseProps & {
  href?: never;
  onClick?: () => void;
  type?: "button" | "submit";
};

export function Button(props: ButtonAsLink | ButtonAsButton) {
  const { variant = "primary", size = "md", className, children } = props;
  const classes = getButtonClasses(variant, size, className);

  if ("href" in props && props.href) {
    return (
      <Link href={props.href} className={classes}>
        {children}
      </Link>
    );
  }

  const buttonProps = props as ButtonAsButton;
  return (
    <button type={buttonProps.type ?? "button"} onClick={buttonProps.onClick} className={classes}>
      {children}
    </button>
  );
}
