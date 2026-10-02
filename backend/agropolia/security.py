from __future__ import annotations

import hashlib
import hmac
import re
from typing import Literal


PHONE_RE = re.compile(r"^\+[1-9]\d{9,14}$")


def normalize_phone(value: str) -> str:
    raw = re.sub(r"[^\d+]", "", value.strip())
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    normalized = "+" + digits
    if not PHONE_RE.fullmatch(normalized):
        raise ValueError("Некорректный номер телефона")
    return normalized


def validate_inn(value: str) -> str:
    inn = re.sub(r"\D", "", value)
    if len(inn) == 10:
        weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        check = sum(int(inn[i]) * weights[i] for i in range(9)) % 11 % 10
        if check != int(inn[9]):
            raise ValueError("Некорректный ИНН")
    elif len(inn) == 12:
        w11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        w12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        c11 = sum(int(inn[i]) * w11[i] for i in range(10)) % 11 % 10
        c12 = sum(int(inn[i]) * w12[i] for i in range(11)) % 11 % 10
        if c11 != int(inn[10]) or c12 != int(inn[11]):
            raise ValueError("Некорректный ИНН")
    else:
        raise ValueError("ИНН должен содержать 10 или 12 цифр")
    return inn


def secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def otp_digest(secret: str, phone: str, device_id: str, purpose: str, code: str) -> str:
    message = f"{phone}|{device_id}|{purpose}|{code}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
