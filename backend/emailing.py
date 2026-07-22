"""
emailing.py — envio de e-mails transacionais via Resend (API HTTP, sem SMTP).
"""

import os
import requests

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "ITBI Smart <noreply@itbismart.com.br>")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8000")

# API_BASE = origem do backend (FRONTEND_URL aponta para /dashboard; a rota de
# verificação é /api/auth/verificar, no mesmo domínio mas fora do /dashboard).
API_BASE = FRONTEND_URL[: -len("/dashboard")] if FRONTEND_URL.endswith("/dashboard") else FRONTEND_URL


def enviar_verificacao(email: str, nome: str, token: str) -> None:
    link = f"{API_BASE}/api/auth/verificar?token={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#e08560">Confirme seu e-mail</h2>
      <p>Olá{f', {nome}' if nome else ''}! Confirme seu e-mail para ativar sua conta no ITBI Smart.</p>
      <p>
        <a href="{link}" style="background:#e08560;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block">
          Confirmar e-mail
        </a>
      </p>
      <p style="color:#888;font-size:13px">Se você não criou essa conta, ignore este e-mail. Este link expira em 24 horas.</p>
    </div>
    """
    _enviar(email, "Confirme seu e-mail — ITBI Smart", html)


def enviar_redefinicao_senha(email: str, nome: str, token: str) -> None:
    link = f"{FRONTEND_URL}/login.html?resetar={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#e08560">Redefinir senha</h2>
      <p>Olá{f', {nome}' if nome else ''}! Recebemos um pedido para redefinir a senha da sua conta no ITBI Smart.</p>
      <p>
        <a href="{link}" style="background:#e08560;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block">
          Definir nova senha
        </a>
      </p>
      <p style="color:#888;font-size:13px">Se você não pediu isso, ignore este e-mail — sua senha continua a mesma. Este link expira em 1 hora.</p>
    </div>
    """
    _enviar(email, "Redefinir senha — ITBI Smart", html)


def enviar_confirmacao_troca_email(email: str, nome: str, token: str) -> None:
    link = f"{API_BASE}/api/auth/confirmar-troca-email?token={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#e08560">Confirme seu novo e-mail</h2>
      <p>Olá{f', {nome}' if nome else ''}! Confirme para trocar o e-mail da sua conta no ITBI Smart para este endereço.</p>
      <p>
        <a href="{link}" style="background:#e08560;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block">
          Confirmar novo e-mail
        </a>
      </p>
      <p style="color:#888;font-size:13px">Se você não pediu essa troca, ignore este e-mail. Este link expira em 24 horas.</p>
    </div>
    """
    _enviar(email, "Confirme seu novo e-mail — ITBI Smart", html)


def _enviar(destinatario: str, assunto: str, html: str) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY não configurado")
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": RESEND_FROM, "to": [destinatario], "subject": assunto, "html": html},
        timeout=10,
    )
    resp.raise_for_status()
