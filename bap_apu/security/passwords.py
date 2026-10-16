import base64
import hashlib
import hmac
import os


ALGORITHM = "scrypt"
N = 2 ** 14
R = 8
P = 1


def hash_password(password):
    if not isinstance(password, str) or not password:
        raise ValueError("La contraseña es obligatoria")
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=N, r=R, p=P, dklen=32)
    return "$".join((ALGORITHM, str(N), str(R), str(P), base64.b64encode(salt).decode(), base64.b64encode(digest).decode()))


def verify_password(password, encoded):
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=base64.b64decode(salt),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return hmac.compare_digest(digest, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def validar_fortaleza(password):
    errores = []
    if len(password) < 8: errores.append("mínimo 8 caracteres")
    if not any(c.isupper() for c in password): errores.append("una mayúscula")
    if not any(c.islower() for c in password): errores.append("una minúscula")
    if not any(c.isdigit() for c in password): errores.append("un número")
    return errores
