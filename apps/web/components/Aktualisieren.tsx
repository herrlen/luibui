"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// While a scan waits or runs, reload the server data every two seconds.
export function Aktualisieren({ aktiv }: { aktiv: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!aktiv) return;
    const t = setInterval(() => router.refresh(), 2000);
    return () => clearInterval(t);
  }, [aktiv, router]);
  return null;
}
