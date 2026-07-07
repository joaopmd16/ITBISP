"""
billing.py — integração com Stripe (assinatura recorrente mensal).
"""

import os
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

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
        unit_amount=2500,  # R$ 25,00
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
