"use client";

import { motion } from "framer-motion";

const PLAN = {
  name: "Básico",
  price: "R$ 49,90",
  period: "/mês",
  desc: "Para quem precisa consultar transações pontualmente.",
  features: [
    "Busca e filtros completos",
    "Histórico 2006–2026",
    "Exportação Excel/PDF (limitada)",
    "1 usuário",
  ],
};

const PROMO = {
  price: "R$ 30",
  meses: 3,
  cupom: "ITBIREMAX30",
  validoAte: "12/08/2026",
};

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
            Um plano simples para consultar transações. Cancele quando
            quiser.
          </p>
        </motion.div>

        <div className="mt-16 flex justify-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5 }}
            className="relative flex w-full max-w-sm flex-col rounded-2xl border border-accent bg-gradient-to-b from-accent/10 to-panel p-7 shadow-xl shadow-accent/10"
          >
            <h3 className="text-lg font-semibold text-white">{PLAN.name}</h3>
            <p className="mt-1 text-sm text-neutral-400">{PLAN.desc}</p>

            <div className="mt-6 flex items-baseline gap-2">
              <span className="text-lg text-neutral-500 line-through">
                {PLAN.price}
              </span>
              <span className="text-4xl font-bold text-white">
                {PROMO.price}
              </span>
              <span className="text-sm text-neutral-500">{PLAN.period}</span>
            </div>
            <p className="mt-2 text-xs font-medium text-accent">
              nos {PROMO.meses} primeiros meses com o cupom{" "}
              <span className="font-mono font-bold">{PROMO.cupom}</span>
              {" "}· depois {PLAN.price}
              {PLAN.period}
            </p>
            <p className="mt-1 text-[11px] text-neutral-600">
              Cupom válido até {PROMO.validoAte}
            </p>

            <ul className="mt-6 flex-1 space-y-3">
              {PLAN.features.map((f) => (
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
              href="/dashboard"
              className="mt-8 block rounded-lg bg-accent px-5 py-3 text-center text-sm font-semibold text-white transition hover:brightness-110"
            >
              Começar agora
            </a>
          </motion.div>
        </div>

        <p className="mt-8 text-center text-xs text-neutral-600">
          Cancele quando quiser. Sem fidelidade.
        </p>
      </div>
    </section>
  );
}
