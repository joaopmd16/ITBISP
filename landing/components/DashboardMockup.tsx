const STATS = [
  { label: "Transações", value: "539.313", delta: "-60,51%", down: true, icon: "▦" },
  { label: "Volume total", value: "345,1 Bi", delta: "+18,20%", down: false, icon: "$" },
  { label: "Ticket médio", value: "R$ 639,8k", delta: "+4,10%", down: false, icon: "◷" },
  { label: "Base ITBI", value: "R$ 194,4 Bi", delta: "+15,60%", down: false, icon: "▤" },
];

const BARS = [38, 52, 44, 61, 70, 55, 80, 66, 90, 74, 58, 40];

export default function DashboardMockup() {
  return (
    <div className="w-full rounded-2xl border border-panel-border bg-panel shadow-2xl overflow-hidden select-none">
      {/* title bar */}
      <div className="flex items-center gap-2 border-b border-panel-border px-4 py-3 bg-[#101010]">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-3 text-[11px] text-neutral-500">itbismart.com.br</span>
      </div>

      <div className="flex">
        {/* sidebar */}
        <div className="hidden sm:flex w-12 flex-col items-center gap-4 border-r border-panel-border bg-[#0d0d0d] py-4">
          <div className="h-7 w-7 rounded-lg bg-accent/90" />
          {["▦", "◷", "◔", "☰", "▽"].map((ic, i) => (
            <span
              key={i}
              className={`text-[13px] ${i === 0 ? "text-accent" : "text-neutral-600"}`}
            >
              {ic}
            </span>
          ))}
        </div>

        {/* main */}
        <div className="flex-1 p-4 sm:p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-[13px] font-semibold text-white">Visão geral</div>
              <div className="text-[10px] text-neutral-500">
                ITBI · transações imobiliárias em São Paulo · 2024–2026
              </div>
            </div>
            <div className="rounded-md border border-panel-border bg-[#161616] px-2 py-1 text-[10px] text-neutral-400">
              2024–2026
            </div>
          </div>

          {/* stat cards */}
          <div className="grid grid-cols-2 gap-2.5 sm:gap-3">
            {STATS.map((s) => (
              <div
                key={s.label}
                className="rounded-xl border border-panel-border bg-[#161616] p-3"
              >
                <div className="mb-2 flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 text-[11px] text-accent">
                  {s.icon}
                </div>
                <div className="text-[15px] font-bold text-white leading-none">
                  {s.value}
                </div>
                <div className="mt-1 text-[9px] text-neutral-500">{s.label}</div>
                <div
                  className={`mt-1 text-[9px] font-medium ${
                    s.down ? "text-red-400" : "text-emerald-400"
                  }`}
                >
                  {s.delta}
                </div>
              </div>
            ))}
          </div>

          {/* chart */}
          <div className="mt-3 rounded-xl border border-panel-border bg-[#161616] p-3">
            <div className="mb-2 text-[10px] text-neutral-500">
              Transações por ano
            </div>
            <div className="flex h-16 items-end gap-1.5">
              {BARS.map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t-sm"
                  style={{
                    height: `${h}%`,
                    background:
                      i === 8
                        ? "var(--accent)"
                        : "linear-gradient(to top, #ffffff14, #ffffff28)",
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
