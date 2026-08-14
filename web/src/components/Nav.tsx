"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

export function Nav({ active }: { active: "stage" | "lab" | "about" }) {
  const item = (id: typeof active, href: string, label: string) => (
    <Link
      href={href}
      className={cn(
        "font-mono text-[10px] uppercase tracking-[0.28em] transition",
        active === id ? "text-gold" : "text-white/45 hover:text-white/80",
      )}
    >
      {label}
    </Link>
  );

  return (
    <header className="pointer-events-none absolute inset-x-0 top-0 z-30 flex items-center justify-between px-6 py-5">
      <Link href="/" className="pointer-events-auto flex items-baseline gap-3">
        <span className="font-serif text-2xl tracking-wide text-white">Vaani</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-sea/80">
          वाणी
        </span>
      </Link>
      <nav className="pointer-events-auto flex items-center gap-6">
        {item("stage", "/", "stage")}
        {item("lab", "/lab", "lab")}
        {item("about", "/about", "about")}
      </nav>
    </header>
  );
}
