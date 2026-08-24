import type { ReactNode, HTMLAttributes } from 'react';
import { clsx } from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div className={clsx("bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: CardProps) {
  return <div className={clsx("px-6 py-4 border-b border-slate-100", className)}>{children}</div>;
}

export function CardTitle({ children, className }: CardProps) {
  return <h3 className={clsx("text-lg font-medium text-slate-800", className)}>{children}</h3>;
}

export function CardContent({ children, className }: CardProps) {
  return <div className={clsx("px-6 py-4", className)}>{children}</div>;
}
