"use client";

import { motion } from "framer-motion";
import Image from "next/image";

export default function Navbar() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="fixed inset-x-0 top-0 z-50 border-b border-panel-border/60 bg-[#0a0a0a]/80 backdrop-blur-md"
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <a href="#" className="flex items-center gap-2">
          <Image
            src="/logo-icon.png"
            alt="ITBI Smart"
            width={38}
            height={38}
            className="rounded-lg"
            priority
          />
          <span className="text-sm font-semibold text-white">ITBI Smart</span>
        </a>

        <nav className="hidden items-center gap-8 text-sm text-neutral-400 sm:flex">
          <a href="#sistema" className="transition hover:text-white">
            O sistema
          </a>
          <a href="#quem-somos" className="transition hover:text-white">
            Quem somos
          </a>
          <a href="#precos" className="transition hover:text-white">
            Preços
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <a
            href="/dashboard"
            className="hidden rounded-lg border border-panel-border px-4 py-2 text-sm font-medium text-neutral-200 transition hover:border-neutral-600 sm:block"
          >
            Login
          </a>
          <a
            href="#precos"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
          >
            Ver preços
          </a>
        </div>
      </div>
    </motion.header>
  );
}
