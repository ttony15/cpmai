from fastapi import Depends, HTTPException
from jose import jwk
from jose import jwt as jose_jwt


jwks = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "1234example",
            "use": "sig",
            "alg": "RS256",
            "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
            "e": "AQAB",
        },
        {
            "kty": "RSA",
            "kid": "5678example",
            "use": "sig",
            "alg": "RS256",
            "n": "xZ4u9L7KVytFEGJgWXNaUo5dLFtc94XUyLDLWMEQf7y6KUHu2JyYzhAhJEYpwUgL0HQ5RcVDQJzJ4Vk0DpJarZeoZ9HbYMzELnUdgVQGfhEOi2f0TPRDfMtTYcuhTzQUZF5dMYsrp7vYZ2aSZZEaXvVWFJhQNlHFtVUUWJ8S7uXYE46CAw4KFm9jTd2DYLXZq-2Wvt8tvF8hGk0NL7gJbF7QiXpZBnUX6t7S98cUE7FwBcAhvW09Q1JqK_7ha0iBeXYaZELHzrUBWMlWlsrhVEJUdTZVN2bYUDOXPmGg2vjOyxasbXxAnTKUGzFdv6uPToi-V8C-KH2GnCYtOQ6YgPDQNrQUmQ",
            "e": "AQAB",
        },
    ]
}

key_set = {k["kid"]: k for k in jwks.get("keys")}


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
