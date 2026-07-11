"use client";

import { motion } from "framer-motion";

const STATS = [
  { value: "2M+", label: "transações mapeadas" },
  { value: "20", label: "anos de histórico (2006–2026)" },
  { value: "R$ 194,4 Bi", label: "em base ITBI processada" },
];

export default function About() {
  return (
    <section id="quem-somos" className="relative border-y border-panel-border/60 bg-panel/40 px-6 py-24 sm:py-32">
      <div className="mx-auto grid max-w-6xl gap-16 lg:grid-cols-2 lg:items-center">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Quem somos
          </h2>
          <p className="mt-5 text-neutral-400 leading-relaxed">
            Somos um time focado em transformar dados públicos de ITBI da
            Prefeitura de São Paulo em inteligência de mercado acessível.
            Reunimos, tratamos e organizamos mais de duas décadas de
            transações imobiliárias para que corretores, investidores,
            avaliadores e empresas do setor tenham decisões baseadas em
            dados reais — não em achismo.
          </p>
          <p className="mt-4 text-neutral-400 leading-relaxed">
            O ITBI Smart nasceu para resolver um problema simples: os dados
            existem, são públicos, mas estão espalhados em planilhas enormes
            e difíceis de cruzar. Nós já fizemos esse trabalho pesado — você
            só filtra, visualiza e exporta.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-1"
        >
          {STATS.map((s) => (
            <div
              key={s.label}
              className="rounded-2xl border border-panel-border bg-panel p-6"
            >
              <div className="text-3xl font-bold text-accent">{s.value}</div>
              <div className="mt-1 text-sm text-neutral-400">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
