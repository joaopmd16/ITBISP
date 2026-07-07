"""
auth.py — autenticação (JWT) e checagem de assinatura ativa.
"""

import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
JWT_EXP_DIAS = 7


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, hash_: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_.encode())


def criar_token(usuario_id: int, email: str) -> str:
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DIAS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


def get_usuario_atual(authorization: str = Header(None)) -> dict:
    """Dependency: extrai e valida o JWT do header Authorization: Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Não autenticado")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decodificar_token(token)
    return {"id": int(payload["sub"]), "email": payload["email"]}
