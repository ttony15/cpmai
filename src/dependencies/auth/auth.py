import requests
from fastapi import Depends, HTTPException
from jose import jwk
from jose import jwt as jose_jwt

from src.core.settings import settings

jwks = requests.get(settings.jwks_url, timeout=3).json()
key_set = {k["kid"]: k for k in jwks["keys"]}


def verify_jwt(
    token: str = Depends(lambda req: req.headers.get("Authorization", " ").split()[-1]),
):
    """Validate JWT via JWKS"""
    if not token:
        raise HTTPException(401, "Missing bearer token")
    header = jose_jwt.get_unverified_header(token)
    key_data = key_set.get(header["kid"])
    if not key_data:
        raise HTTPException(401, "Invalid token key ID")
    key = jwk.construct(key_data)
    payload = jose_jwt.decode(token, key.to_dict(), algorithms=[header["alg"]])
    return payload  # contains 'sub' as user_id
