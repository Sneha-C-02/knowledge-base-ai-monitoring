import type { InputHTMLAttributes } from 'react';
import { forwardRef } from 'react';
import { clsx } from 'clsx';

export const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>((
  { className, ...props }, ref
) => {
  return (
    <input
      ref={ref}
      className={clsx(
        "block w-full rounded-md border-slate-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border",
        className
      )}
      {...props}
    />
  );
});
TextInput.displayName = 'TextInput';
