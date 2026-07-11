"use client";

import { motion } from "framer-motion";
import DashboardMockup from "./DashboardMockup";

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-grid px-6 pt-36 pb-24 sm:pt-44 sm:pb-32">
      {/* glow */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[560px] w-[900px] -translate-x-1/2 rounded-full bg-accent/20 blur-[140px]" />

      <div className="relative mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto mb-6 flex w-fit items-center gap-2 rounded-full border border-panel-border bg-panel px-4 py-1.5 text-xs text-neutral-400"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          Dados oficiais da Prefeitura de São Paulo · 2006–2026
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mx-auto max-w-3xl text-center text-4xl font-bold tracking-tight text-white sm:text-6xl"
        >
          Inteligência imobiliária sobre{" "}
          <span className="text-accent">2 milhões</span> de transações de ITBI
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mx-auto mt-5 max-w-2xl text-center text-base text-neutral-400 sm:text-lg"
        >
          Consulte, filtre e cruze transações imobiliárias de São Paulo em
          segundos. Mapa por CEP, exportação em Excel/PDF e calculadora de
          valor por m² — tudo em um dashboard só.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <a
            href="/dashboard"
            className="rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-accent/25 transition hover:brightness-110"
          >
            Entrar no dashboard
          </a>
          <a
            href="#precos"
            className="rounded-lg border border-panel-border bg-panel px-6 py-3 text-sm font-semibold text-neutral-200 transition hover:border-neutral-600"
          >
            Ver preços
          </a>
        </motion.div>

        {/* mockup em perspectiva dinâmica */}
        <motion.div
          initial={{ opacity: 0, y: 60, rotateX: 24, rotateY: -8 }}
          animate={{ opacity: 1, y: 0, rotateX: 10, rotateY: -4 }}
          transition={{ duration: 1, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
          whileHover={{ rotateX: 4, rotateY: -1, scale: 1.01 }}
          style={{ transformStyle: "preserve-3d" }}
          className="perspective-frame mx-auto mt-20 max-w-4xl"
        >
          <div className="rounded-2xl bg-gradient-to-b from-white/10 to-transparent p-[1px]">
            <DashboardMockup />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
