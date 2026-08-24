import { forwardRef } from 'react';
import type { TextareaHTMLAttributes } from 'react';
import { clsx } from 'clsx';

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>((
  { className, ...props }, ref
) => {
  return (
    <textarea
      ref={ref}
      className={clsx(
        "block w-full rounded-md border-slate-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border",
        className
      )}
      {...props}
    />
  );
});
TextArea.displayName = 'TextArea';
