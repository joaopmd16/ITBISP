"use client";

import { motion } from "framer-motion";

const PLANS = [
  {
    name: "Básico",
    price: "R$ 49",
    period: "/mês",
    desc: "Para quem precisa consultar transações pontualmente.",
    features: [
      "Busca e filtros completos",
      "Histórico 2006–2026",
      "Exportação Excel/PDF (limitada)",
      "1 usuário",
    ],
    highlight: false,
  },
  {
    name: "Profissional",
    price: "R$ 149",
    period: "/mês",
    desc: "Para corretores e avaliadores que usam o sistema no dia a dia.",
    features: [
      "Tudo do plano Básico",
      "Mapa geográfico por CEP",
      "Exportação ilimitada",
      "Calculadora de m² avançada",
      "Até 5 usuários",
    ],
    highlight: true,
  },
  {
    name: "Empresarial",
    price: "Sob consulta",
    period: "",
    desc: "Para imobiliárias e empresas com necessidade de volume e integração.",
    features: [
      "Tudo do plano Profissional",
      "Acesso via API",
      "Usuários ilimitados",
      "Suporte dedicado",
    ],
    highlight: false,
  },
];

export default function Pricing() {
  return (
    <section id="precos" className="relative px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-2xl text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Planos e preços
          </h2>
          <p className="mt-4 text-neutral-400">
            Escolha o plano ideal para o seu volume de consultas. Cancele
            quando quiser.
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {PLANS.map((p, i) => (
            <motion.div
              key={p.name}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className={`relative flex flex-col rounded-2xl border p-7 ${
                p.highlight
                  ? "border-accent bg-gradient-to-b from-accent/10 to-panel shadow-xl shadow-accent/10"
                  : "border-panel-border bg-panel"
              }`}
            >
              {p.highlight && (
                <span className="absolute -top-3 left-7 rounded-full bg-accent px-3 py-1 text-[11px] font-semibold text-white">
                  Mais popular
                </span>
              )}
              <h3 className="text-lg font-semibold text-white">{p.name}</h3>
              <p className="mt-1 text-sm text-neutral-400">{p.desc}</p>
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-white">
                  {p.price}
                </span>
                <span className="text-sm text-neutral-500">{p.period}</span>
              </div>

              <ul className="mt-6 flex-1 space-y-3">
                {p.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2 text-sm text-neutral-300"
                  >
                    <span className="mt-0.5 text-accent">✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <a
                href="https://itbismart.com.br"
                className={`mt-8 block rounded-lg px-5 py-3 text-center text-sm font-semibold transition ${
                  p.highlight
                    ? "bg-accent text-white hover:brightness-110"
                    : "border border-panel-border text-neutral-200 hover:border-neutral-600"
                }`}
              >
                Começar agora
              </a>
            </motion.div>
          ))}
        </div>

        <p className="mt-8 text-center text-xs text-neutral-600">
          * Valores de exemplo, sujeitos a ajuste.
        </p>
      </div>
    </section>
  );
}
