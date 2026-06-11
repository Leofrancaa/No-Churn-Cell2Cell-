"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const PAGINAS = [
  { href: "/", titulo: "Engenheiro de IA" },
  { href: "/analista", titulo: "Analista de Retenção" },
] as const;

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  async function sair() {
    await fetch("/api/py/logout", { method: "POST" });
    router.push("/login");
  }

  return (
    <nav className="flex items-center justify-between border-b border-slate-800 pb-4">
      <div className="flex items-center gap-2">
        <span className="mr-3 text-lg font-semibold">📡 Retenção Cell2Cell</span>
        {PAGINAS.map((pagina) => (
          <Link
            key={pagina.href}
            href={pagina.href}
            className={`rounded-lg px-3 py-1.5 text-sm transition ${
              pathname === pagina.href
                ? "bg-sky-600 text-white"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            {pagina.titulo}
          </Link>
        ))}
      </div>
      <button
        onClick={sair}
        className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-800"
      >
        Sair
      </button>
    </nav>
  );
}
