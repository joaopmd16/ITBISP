"""
billing.py — integração com Stripe (assinatura recorrente mensal).
"""

import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8000")


def garantir_price_id() -> str:
    """Cria Produto + Price mensal no Stripe se STRIPE_PRICE_ID não estiver configurado.
    Útil apenas em desenvolvimento/primeira execução — em produção defina STRIPE_PRICE_ID no .env."""
    global PRICE_ID
    if PRICE_ID:
        return PRICE_ID
    produto = stripe.Product.create(name="Dashboard ITBI-SP — Assinatura mensal")
    price = stripe.Price.create(
        product=produto.id,
        unit_amount=3000,  # R$ 30,00
        currency="brl",
        recurring={"interval": "month"},
    )
    PRICE_ID = price.id
    return PRICE_ID


def criar_checkout_session(email: str, usuario_id: int, stripe_customer_id: str | None) -> str:
    price_id = garantir_price_id()
    params = dict(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/?checkout=sucesso",
        cancel_url=f"{FRONTEND_URL}/login.html?checkout=cancelado",
        client_reference_id=str(usuario_id),
        metadata={"usuario_id": str(usuario_id)},
        allow_promotion_codes=True,
    )
    if stripe_customer_id:
        params["customer"] = stripe_customer_id
    else:
        params["customer_email"] = email
    session = stripe.checkout.Session.create(**params)
    return session.url


def criar_portal_session(stripe_customer_id: str) -> str:
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{FRONTEND_URL}/",
    )
    return session.url


def construir_evento(payload: bytes, assinatura_header: str):
    if not WEBHOOK_SECRET:
        import json
        return json.loads(payload)
    return stripe.Webhook.construct_event(payload, assinatura_header, WEBHOOK_SECRET)


# ──────────────────────────────────────────────
# ADMIN — histórico de pagamentos e gestão de assinatura
# ──────────────────────────────────────────────

def listar_faturas(stripe_customer_id: str, limite: int = 20) -> list[dict]:
    faturas = stripe.Invoice.list(customer=stripe_customer_id, limit=limite)
    return [
        {
            "id": f.id,
            "status": f.status,
            "valor": (f.amount_paid or f.amount_due or 0) / 100,
            "moeda": f.currency,
            "criada_em": f.created,
            "paga_em": f.status_transitions.paid_at if f.status_transitions else None,
            "url_pdf": f.invoice_pdf,
            "url_hospedada": f.hosted_invoice_url,
        }
        for f in faturas.data
    ]


def detalhes_assinatura(stripe_subscription_id: str) -> dict | None:
    if not stripe_subscription_id:
        return None
    sub = stripe.Subscription.retrieve(stripe_subscription_id)
    item = sub["items"]["data"][0] if sub["items"]["data"] else None
    # current_period_end mudou de posição entre versões da API do Stripe (objeto
    # subscription vs. subscription item) — tenta os dois locais por segurança.
    periodo_fim = sub.get("current_period_end") or (item.get("current_period_end") if item else None)
    return {
        "status": sub.status,
        "inicio": sub.get("start_date"),
        "periodo_fim": periodo_fim,
        "cancela_no_fim": sub.cancel_at_period_end,
    }


def cancelar_assinatura(stripe_subscription_id: str) -> None:
    """Cancela a assinatura no Stripe imediatamente (usado quando o admin revoga acesso
    de um usuário pagante — sem isso o Stripe continuaria cobrando e o próximo webhook
    reativaria o acesso local)."""
    stripe.Subscription.cancel(stripe_subscription_id)
