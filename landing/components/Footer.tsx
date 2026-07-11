import Image from "next/image";

export default function Footer() {
  return (
    <footer className="border-t border-panel-border/60 px-6 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex items-center gap-2">
          <Image
            src="/logo-icon.png"
            alt="ITBI Smart"
            width={32}
            height={32}
            className="rounded-md"
          />
          <span className="text-sm font-semibold text-white">
            ITBI Smart
          </span>
        </div>
        <p className="text-xs text-neutral-500">
          Dados públicos de ITBI · Prefeitura de São Paulo · 2006–2026
        </p>
        <a
          href="https://itbismart.com.br"
          className="text-xs text-neutral-400 transition hover:text-white"
        >
          Acessar dashboard →
        </a>
      </div>
    </footer>
  );
}
