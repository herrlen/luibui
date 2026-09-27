// Small form primitives so every form looks and behaves the same.
import type { InputHTMLAttributes, ReactNode } from "react";

export function Feld({ label, ...props }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-semibold">{label}</span>
      <input
        {...props}
        className="rounded-lg border border-linie bg-surface px-3 py-2 text-base focus:border-petrol"
      />
    </label>
  );
}

export function Knopf({ children, disabled }: { children: ReactNode; disabled?: boolean }) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="rounded-[10px] bg-petrol px-4 py-2 font-semibold text-white hover:bg-petrol-dunkel disabled:opacity-60"
    >
      {children}
    </button>
  );
}

export function Meldung({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <p role="alert" className="rounded-lg bg-rot-bg px-3 py-2 text-sm text-rot">
      {text}
    </p>
  );
}
