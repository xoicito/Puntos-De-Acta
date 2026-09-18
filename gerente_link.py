from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import (
    GERENTE_LINK_BASE_URL,
    GERENTE_LINK_EXPIRATION_HOURS,
    GERENTE_LINK_SECRET_KEY,
)

SALT = "firma-gerente-v1"


class InvalidLinkError(ValueError):
    """Raised with a user-facing reason when a signing link can't be used."""


def _serializer():
    if not GERENTE_LINK_SECRET_KEY:
        raise RuntimeError(
            "GERENTE_LINK_SECRET_KEY no esta configurada - no se pueden "
            "generar ni verificar enlaces de firma"
        )

    return URLSafeTimedSerializer(GERENTE_LINK_SECRET_KEY, salt=SALT)


def generate_signing_link(item_id, board_id):
    token = _serializer().dumps({"item_id": str(item_id), "board_id": str(board_id)})

    return f"{GERENTE_LINK_BASE_URL.rstrip('/')}/firmar-gerente/{token}"


def verify_token(token):
    """Return {"item_id", "board_id"} if the token is valid and unexpired.

    Raises InvalidLinkError with a message safe to show the signer.
    """

    try:
        data = _serializer().loads(
            token, max_age=GERENTE_LINK_EXPIRATION_HOURS * 3600
        )
    except SignatureExpired:
        raise InvalidLinkError(
            "Este enlace ya expiro. Pida que le generen uno nuevo."
        )
    except BadSignature:
        raise InvalidLinkError("Este enlace no es valido.")

    if not isinstance(data, dict) or not data.get("item_id") or not data.get("board_id"):
        raise InvalidLinkError("Este enlace no es valido.")

    return data
