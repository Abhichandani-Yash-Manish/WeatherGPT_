import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/* One class-merge helper, the shadcn/ui convention: conditional classes through clsx and conflicting
   Tailwind utilities resolved by tailwind-merge, so a caller's className wins over a component default. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
