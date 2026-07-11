"use client";

import { motion } from "framer-motion";

const FEATURES = [
  {
    icon: "🔍",
    title: "Busca avançada",
    desc: "Filtre por logradouro, bairro, CEP, número de IPTU, natureza, período e faixa de valor — com autocomplete instantâneo.",
  },
  {
    icon: "🗺️",
    title: "Mapa geográfico",
    desc: "Visualize transações agrupadas por CEP em um mapa interativo, com volume e ticket médio por região.",
  },
  {
    icon: "📊",
    title: "Painéis analíticos",
    desc: "Sazonalidade mensal, distribuição por faixa de valor, natureza da transação e top bairros em tempo real.",
  },
  {
    icon: "📐",
    title: "Calculadora de m²",
    desc: "Estime o valor do metro quadrado com base no ticket médio do filtro aplicado, na hora.",
  },
  {
    icon: "📁",
    title: "Exportação",
    desc: "Exporte qualquer resultado filtrado direto para Excel ou PDF, pronto para relatório.",
  },
  {
    icon: "🗄️",
    title: "Dados oficiais 2006–2026",
    desc: "Base atualizada continuamente a partir da fonte oficial da Prefeitura de São Paulo — mais de 2 milhões de registros.",
  },
];

export default function Features() {
  return (
    <section id="sistema" className="relative px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            O que o ITBI Smart faz
          </h2>
          <p className="mt-4 text-neutral-400">
            Tudo que você precisa para analisar o mercado imobiliário
            paulistano em um só lugar, sem depender de planilhas soltas.
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.06 }}
              whileHover={{ y: -4 }}
              className="rounded-2xl border border-panel-border bg-panel p-6 transition-colors hover:border-neutral-600"
            >
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-accent/15 text-xl">
                {f.icon}
              </div>
              <h3 className="text-base font-semibold text-white">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-400">
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
