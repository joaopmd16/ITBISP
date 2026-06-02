"""
pdf_weasy.py — Gerador de PDF profissional via ReportLab
Relatório ITBI · São Paulo
"""
import io
import math
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.lib.utils import ImageReader

# ─── Paleta ───────────────────────────────────────────────────────────────────
C_PRIMARY  = colors.HexColor('#E08560')
C_NAVY     = colors.HexColor('#1B2A4A')
C_INK      = colors.HexColor('#1F2937')
C_MU       = colors.HexColor('#6B7280')
C_LINE     = colors.HexColor('#E5E7EB')
C_SURFACE  = colors.HexColor('#F8FAFC')
C_SURFACE2 = colors.HexColor('#F1F5F9')
C_GREEN    = colors.HexColor('#10B981')
C_BLUE     = colors.HexColor('#2563EB')
C_PURPLE   = colors.HexColor('#7C3AED')
C_AMBER    = colors.HexColor('#F59E0B')
C_TEAL     = colors.HexColor('#0891B2')
C_WHITE    = colors.white
C_BLACK    = colors.black

# matplotlib hex strings
M_PRIMARY  = '#E08560'
M_NAVY     = '#1B2A4A'
M_GREEN    = '#10B981'
M_BLUE     = '#2563EB'
M_PURPLE   = '#7C3AED'
M_AMBER    = '#F59E0B'
M_TEAL     = '#0891B2'
M_MU       = '#6B7280'

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 1.5 * cm


# ─── Helpers matplotlib ───────────────────────────────────────────────────────
def _fig_to_img(fig, w_cm=8.5, h_cm=5.5):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    img = Image(buf, width=w_cm * cm, height=h_cm * cm)
    return img


def _setup_ax(ax, title='', bg='#F8FAFC'):
    ax.set_facecolor(bg)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.tick_params(colors='#6B7280', labelsize=7)
    ax.yaxis.label.set_color('#6B7280')
    ax.xaxis.label.set_color('#6B7280')
    if title:
        ax.set_title(title, fontsize=9, fontweight='bold', color='#1F2937', pad=6)


def _fmt_brl(x, pos=None):
    if x >= 1e9:
        return f'R${x/1e9:.1f}B'
    if x >= 1e6:
        return f'R${x/1e6:.1f}M'
    if x >= 1e3:
        return f'R${x/1e3:.0f}K'
    return f'R${x:.0f}'


# ─── Geração de gráficos ─────────────────────────────────────────────────────
def _build_charts(df: pd.DataFrame):
    charts = {}
    bg = '#F8FAFC'

    # 1) Volume por ano
    if 'ano_referencia' in df.columns and len(df):
        gc = df.groupby('ano_referencia').size().sort_index()
        fig, ax = plt.subplots(figsize=(8.5, 4.5), facecolor=bg)
        bars = ax.bar(gc.index.astype(str), gc.values, color=M_PRIMARY, width=0.65, zorder=2)
        ax.bar_label(bars, fmt='%d', fontsize=7, color='#1F2937', padding=2)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_axisbelow(True); ax.yaxis.grid(True, color='#E5E7EB', linewidth=0.5)
        _setup_ax(ax, 'Transações por Ano', bg)
        charts['bar_ano'] = _fig_to_img(fig, 8.5, 4.5)

    # 2) Ticket médio por ano
    if 'valor_declarado' in df.columns and 'ano_referencia' in df.columns and len(df):
        tm = df.groupby('ano_referencia')['valor_declarado'].median().sort_index()
        fig, ax = plt.subplots(figsize=(8.5, 4.5), facecolor=bg)
        ax.plot(tm.index.astype(str), tm.values, color=M_GREEN, linewidth=2, marker='o',
                markersize=5, markerfacecolor='white', markeredgewidth=2)
        ax.fill_between(range(len(tm)), tm.values, alpha=0.12, color=M_GREEN)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_brl))
        ax.set_axisbelow(True); ax.yaxis.grid(True, color='#E5E7EB', linewidth=0.5)
        ax.tick_params(axis='x', rotation=45)
        _setup_ax(ax, 'Mediana do Valor (R$)', bg)
        charts['line_ticket'] = _fig_to_img(fig, 8.5, 4.5)

    # 3) Top 10 bairros
    if 'bairro' in df.columns and len(df):
        top = df['bairro'].dropna().value_counts().head(10)
        fig, ax = plt.subplots(figsize=(8.5, 4.5), facecolor=bg)
        ax.barh(top.index[::-1], top.values[::-1], color=M_BLUE, height=0.65)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_axisbelow(True); ax.xaxis.grid(True, color='#E5E7EB', linewidth=0.5)
        _setup_ax(ax, 'Top 10 Bairros', bg)
        charts['bar_bairros'] = _fig_to_img(fig, 8.5, 4.5)

    # 4) Distribuição por natureza
    if 'natureza' in df.columns and len(df):
        nat = df['natureza'].dropna().value_counts().head(6)
        palette = [M_PRIMARY, M_BLUE, M_GREEN, M_PURPLE, M_AMBER, M_TEAL]
        fig, ax = plt.subplots(figsize=(5.5, 4.5), facecolor=bg)
        wedges, texts, autotexts = ax.pie(
            nat.values, labels=None,
            autopct='%1.1f%%', startangle=90,
            colors=palette[:len(nat)],
            pctdistance=0.82,
            wedgeprops={'linewidth': 1.5, 'edgecolor': 'white'}
        )
        for t in autotexts: t.set_fontsize(7); t.set_color('white')
        ax.legend(nat.index, loc='lower center', bbox_to_anchor=(0.5, -0.15),
                  fontsize=7, ncol=2, frameon=False)
        _setup_ax(ax, 'Tipos de Transação', bg)
        charts['pizza_nat'] = _fig_to_img(fig, 5.5, 4.5)

    # 5) Histograma de valores
    if 'valor_declarado' in df.columns and len(df):
        vals = df['valor_declarado'].dropna()
        vals = vals[(vals > 0) & (vals < vals.quantile(0.98))]
        fig, ax = plt.subplots(figsize=(8.5, 4.5), facecolor=bg)
        ax.hist(vals, bins=40, color=M_PURPLE, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_brl))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_axisbelow(True); ax.yaxis.grid(True, color='#E5E7EB', linewidth=0.5)
        _setup_ax(ax, 'Distribuição de Valores', bg)
        charts['hist_vals'] = _fig_to_img(fig, 8.5, 4.5)

    # 6) Volume mensal (últimos 24 meses se disponível)
    if 'mes_referencia' in df.columns and 'ano_referencia' in df.columns and len(df):
        df2 = df.copy()
        df2['periodo'] = df2['ano_referencia'].astype(str) + '-' + df2['mes_referencia'].astype(str).str.zfill(2)
        gm = df2.groupby('periodo').size().sort_index().tail(24)
        fig, ax = plt.subplots(figsize=(8.5, 4.5), facecolor=bg)
        ax.plot(range(len(gm)), gm.values, color=M_TEAL, linewidth=1.8, marker='o',
                markersize=3.5, markerfacecolor='white', markeredgewidth=1.8)
        ax.fill_between(range(len(gm)), gm.values, alpha=0.12, color=M_TEAL)
        step = max(1, len(gm) // 8)
        ax.set_xticks(range(0, len(gm), step))
        ax.set_xticklabels([gm.index[i] for i in range(0, len(gm), step)], rotation=45, fontsize=6)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_axisbelow(True); ax.yaxis.grid(True, color='#E5E7EB', linewidth=0.5)
        _setup_ax(ax, 'Volume Mensal', bg)
        charts['line_vol'] = _fig_to_img(fig, 8.5, 4.5)

    return charts


# ─── Insights ─────────────────────────────────────────────────────────────────
def _gerar_insights(df: pd.DataFrame, filtros: dict = None) -> list:
    ins = []
    n = len(df)
    if n == 0:
        return ["Nenhum dado encontrado para os filtros selecionados."]

    total_vol = df['valor_declarado'].sum() if 'valor_declarado' in df.columns else 0
    mediana   = df['valor_declarado'].median() if 'valor_declarado' in df.columns else 0
    media     = df['valor_declarado'].mean()   if 'valor_declarado' in df.columns else 0

    def brl(v):
        if v >= 1e9: return f'R$ {v/1e9:.2f} bilhões'
        if v >= 1e6: return f'R$ {v/1e6:.2f} milhões'
        return f'R$ {v:,.2f}'

    ins.append(
        f"O conjunto analisado contém <b>{n:,}</b> transações com volume financeiro total de "
        f"<b>{brl(total_vol)}</b>. O valor mediano por transação é <b>{brl(mediana)}</b> "
        f"e a média é <b>{brl(media)}</b>, sugerindo "
        + ("uma distribuição com cauda alta (imóveis de alto valor elevando a média)."
           if media > mediana * 1.3 else "uma distribuição relativamente simétrica.")
    )

    if 'ano_referencia' in df.columns:
        by_year = df.groupby('ano_referencia').size()
        peak_y = by_year.idxmax()
        peak_n = by_year.max()
        ins.append(
            f"O ano com maior número de transações no período filtrado foi <b>{peak_y}</b>, "
            f"com <b>{peak_n:,}</b> operações registradas. "
            + (f"A tendência recente mostra {'crescimento' if by_year.iloc[-1] > by_year.iloc[-2] else 'retração'} "
               f"em relação ao ano anterior."
               if len(by_year) >= 2 else "")
        )

    if 'bairro' in df.columns:
        top3 = df['bairro'].dropna().value_counts().head(3)
        if len(top3):
            bairros_str = ', '.join([f"<b>{b}</b> ({v:,})" for b, v in top3.items()])
            pct = top3.sum() / n * 100
            ins.append(
                f"Os 3 bairros mais ativos concentram <b>{pct:.1f}%</b> das transações: {bairros_str}. "
                f"Total de bairros distintos na seleção: <b>{df['bairro'].nunique():,}</b>."
            )

    if 'valor_m2_construida' in df.columns:
        m2 = df['valor_m2_construida'].dropna()
        m2 = m2[(m2 > 0) & (m2 < m2.quantile(0.99))]
        if len(m2):
            ins.append(
                f"O preço médio por m² construído é <b>{brl(m2.mean())}</b>, "
                f"com mediana de <b>{brl(m2.median())}</b>. "
                f"O percentil 75 está em <b>{brl(m2.quantile(0.75))}</b>."
            )

    return ins[:4]


# ─── Canvas com header/footer ─────────────────────────────────────────────────
class _PageDecor:
    def __init__(self, title='Relatório ITBI · São Paulo', generated_at=''):
        self.title = title
        self.generated_at = generated_at

    def __call__(self, canvas, doc):
        canvas.saveState()
        w, h = landscape(A4)

        # Top bar
        canvas.setFillColor(C_NAVY)
        canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(MARGIN, h - 0.72 * cm, self.title)
        canvas.setFont('Helvetica', 7.5)
        canvas.drawRightString(w - MARGIN, h - 0.72 * cm, self.generated_at)

        # Bottom bar
        canvas.setFillColor(C_LINE)
        canvas.rect(0, 0, w, 0.7 * cm, fill=1, stroke=0)
        canvas.setFillColor(C_MU)
        canvas.setFont('Helvetica', 7)
        canvas.drawString(MARGIN, 0.22 * cm, 'ITBI SP · Dados: Prefeitura de São Paulo')
        canvas.drawRightString(w - MARGIN, 0.22 * cm, f'Página {doc.page}')

        canvas.restoreState()


# ─── Flowable: KPI card ───────────────────────────────────────────────────────
class KPICard(Flowable):
    def __init__(self, label, value, sub='', accent=None, w=5.5*cm, h=2.2*cm):
        super().__init__()
        self.label = label
        self.value = value
        self.sub = sub
        self.accent = accent or C_PRIMARY
        self.card_w = w
        self.card_h = h
        self.width = w
        self.height = h

    def draw(self):
        c = self.canv
        r = 6
        # Background
        c.setFillColor(C_SURFACE)
        c.roundRect(0, 0, self.card_w, self.card_h, r, fill=1, stroke=0)
        # Left accent bar
        c.setFillColor(self.accent)
        c.rect(0, 0, 3, self.card_h, fill=1, stroke=0)
        c.roundRect(0, 0, 3 + r, self.card_h, r, fill=1, stroke=0)
        # Label
        c.setFillColor(C_MU)
        c.setFont('Helvetica', 7)
        c.drawString(10, self.card_h - 14, self.label.upper())
        # Value
        c.setFillColor(C_INK)
        font_size = 13 if len(self.value) < 14 else 10
        c.setFont('Helvetica-Bold', font_size)
        c.drawString(10, self.card_h - 30, self.value)
        # Sub
        if self.sub:
            c.setFillColor(C_MU)
            c.setFont('Helvetica', 7)
            c.drawString(10, 6, self.sub)


# ─── Estilos de parágrafo ─────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    s = {}
    s['title'] = ParagraphStyle('title', parent=base['Normal'],
        fontSize=22, fontName='Helvetica-Bold', textColor=C_NAVY,
        spaceAfter=4, leading=28)
    s['subtitle'] = ParagraphStyle('subtitle', parent=base['Normal'],
        fontSize=10, fontName='Helvetica', textColor=C_MU,
        spaceAfter=2, leading=14)
    s['section'] = ParagraphStyle('section', parent=base['Normal'],
        fontSize=11, fontName='Helvetica-Bold', textColor=C_NAVY,
        spaceBefore=10, spaceAfter=4, leading=16)
    s['body'] = ParagraphStyle('body', parent=base['Normal'],
        fontSize=8.5, fontName='Helvetica', textColor=C_INK,
        spaceAfter=4, leading=13)
    s['small'] = ParagraphStyle('small', parent=base['Normal'],
        fontSize=7, fontName='Helvetica', textColor=C_MU,
        spaceAfter=2, leading=10)
    s['chip'] = ParagraphStyle('chip', parent=base['Normal'],
        fontSize=7.5, fontName='Helvetica', textColor=C_WHITE,
        leading=10, backColor=C_NAVY, borderPadding=(2, 5, 2, 5))
    return s


# ─── Table style helpers ──────────────────────────────────────────────────────
def _table_style_main():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, C_SURFACE]),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('TEXTCOLOR', (0, 1), (-1, -1), C_INK),
        ('GRID', (0, 0), (-1, -1), 0.25, C_LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ])


# ─── Função principal ─────────────────────────────────────────────────────────
def gerar_pdf(df: pd.DataFrame, filtros: dict = None) -> bytes:
    filtros = filtros or {}
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.5 * cm, bottomMargin=1.0 * cm,
        title='Relatório ITBI São Paulo',
        author='ITBI Dashboard',
    )

    decor_title = _PageDecor('Relatório ITBI · São Paulo', f'Gerado em {now_str}')
    S = _styles()
    story = []

    # ── Capa ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph('Relatório de Transações', S['title']))
    story.append(Paragraph('ITBI · Imposto de Transmissão de Bens Imóveis · São Paulo', S['subtitle']))
    story.append(Spacer(1, 0.3 * cm))

    # Filtros ativos como chips inline
    filtro_texts = []
    labels = {
        'logradouro': 'Logradouro', 'bairro': 'Bairro', 'cep': 'CEP',
        'ano_min': 'Ano inicial', 'ano_max': 'Ano final',
        'valor_min': 'Valor mín.', 'valor_max': 'Valor máx.', 'natureza': 'Natureza',
    }
    for k, label in labels.items():
        v = filtros.get(k)
        if v:
            filtro_texts.append(f'{label}: <b>{v}</b>')
    if filtro_texts:
        story.append(Paragraph('Filtros: ' + ' · '.join(filtro_texts), S['small']))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width='100%', thickness=1, color=C_LINE))
    story.append(Spacer(1, 0.4 * cm))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    n = len(df)

    def brl(v):
        if v >= 1e9: return f'R$ {v/1e9:.2f}B'
        if v >= 1e6: return f'R$ {v/1e6:.2f}M'
        return f'R$ {v:,.0f}'

    total_vol = df['valor_declarado'].sum() if 'valor_declarado' in df.columns else 0
    mediana   = df['valor_declarado'].median() if 'valor_declarado' in df.columns else 0
    media     = df['valor_declarado'].mean()   if 'valor_declarado' in df.columns else 0
    n_bairros = df['bairro'].nunique()         if 'bairro' in df.columns else 0
    n_anos    = df['ano_referencia'].nunique() if 'ano_referencia' in df.columns else 0

    kpi_w = (PAGE_W - 2 * MARGIN - 4 * 0.3 * cm) / 5

    kpis_row = [
        KPICard('Total de Transações', f'{n:,}', f'{n_bairros} bairros', C_PRIMARY, kpi_w),
        KPICard('Volume Total', brl(total_vol), f'{n_anos} anos', C_BLUE, kpi_w),
        KPICard('Valor Mediano', brl(mediana), 'por transação', C_GREEN, kpi_w),
        KPICard('Valor Médio', brl(media), 'por transação', C_PURPLE, kpi_w),
        KPICard('Bairros Distintos', f'{n_bairros:,}', 'no filtro atual', C_TEAL, kpi_w),
    ]

    kpi_table = Table(
        [kpis_row],
        colWidths=[kpi_w] * 5,
        rowHeights=[2.3 * cm],
        hAlign='LEFT',
    )
    kpi_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Insights ──────────────────────────────────────────────────────────────
    story.append(Paragraph('Análise Automática', S['section']))
    for txt in _gerar_insights(df, filtros):
        story.append(Paragraph(txt, S['body']))
    story.append(Spacer(1, 0.3 * cm))

    # ── Gráficos ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=1, color=C_LINE))
    story.append(Paragraph('Visualizações', S['section']))

    charts = _build_charts(df)

    chart_w = (PAGE_W - 2 * MARGIN - 0.4 * cm) / 2

    def _chart_cell(img, title):
        inner = [
            Paragraph(title, S['small']),
            Spacer(1, 0.1 * cm),
            img,
        ]
        return inner

    chart_pairs = []
    keys = list(charts.keys())
    for i in range(0, len(keys), 2):
        left  = _chart_cell(charts[keys[i]], _chart_title(keys[i]))
        right = _chart_cell(charts[keys[i+1]], _chart_title(keys[i+1])) if i+1 < len(keys) else [Spacer(1, 1)]
        chart_pairs.append([left, right])

    if chart_pairs:
        ct = Table(chart_pairs, colWidths=[chart_w, chart_w], hAlign='LEFT')
        ct.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(ct)

    # ── Tabela de transações ──────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('Transações', S['section']))

    MAX_ROWS = 500
    df_show = df.head(MAX_ROWS)

    cols_order = ['id', 'ano_referencia', 'mes_referencia', 'logradouro', 'numero',
                  'bairro', 'natureza', 'valor_declarado', 'area_construida', 'valor_m2_construida']
    cols_labels = {
        'id': 'ID', 'ano_referencia': 'Ano', 'mes_referencia': 'Mês',
        'logradouro': 'Logradouro', 'numero': 'Nº', 'bairro': 'Bairro',
        'natureza': 'Natureza', 'valor_declarado': 'Valor (R$)',
        'area_construida': 'Área (m²)', 'valor_m2_construida': 'R$/m²',
    }
    cols_use = [c for c in cols_order if c in df_show.columns]
    headers  = [cols_labels.get(c, c) for c in cols_use]

    data = [headers]
    for _, row in df_show.iterrows():
        r = []
        for c in cols_use:
            v = row.get(c, '')
            if c in ('valor_declarado', 'valor_m2_construida') and pd.notna(v) and v:
                try: v = f'R$ {float(v):,.0f}'
                except: pass
            elif c == 'area_construida' and pd.notna(v) and v:
                try: v = f'{float(v):,.1f}'
                except: pass
            r.append(str(v) if pd.notna(v) and v != '' else '—')
        data.append(r)

    if n > MAX_ROWS:
        story.append(Paragraph(
            f'Exibindo as primeiras {MAX_ROWS:,} de {n:,} transações.',
            S['small']
        ))

    # Column widths (proportional)
    avail = PAGE_W - 2 * MARGIN
    w_map = {'id': 0.5, 'ano_referencia': 0.5, 'mes_referencia': 0.4,
              'logradouro': 2.0, 'numero': 0.4, 'bairro': 1.4,
              'natureza': 1.6, 'valor_declarado': 1.1,
              'area_construida': 0.7, 'valor_m2_construida': 0.8}
    raw_w = [w_map.get(c, 1.0) for c in cols_use]
    total_raw = sum(raw_w)
    col_widths = [avail * w / total_raw for w in raw_w]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(_table_style_main())
    story.append(t)

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f'Relatório gerado em {now_str} · ITBI SP Dashboard · Dados: Prefeitura de São Paulo',
        S['small']
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=decor_title, onLaterPages=decor_title)
    return buf.getvalue()


def _chart_title(key):
    return {
        'bar_ano':     'Transações por Ano',
        'line_ticket': 'Mediana do Valor (R$)',
        'bar_bairros': 'Top 10 Bairros',
        'pizza_nat':   'Tipos de Transação',
        'hist_vals':   'Distribuição de Valores',
        'line_vol':    'Volume Mensal',
    }.get(key, key)
