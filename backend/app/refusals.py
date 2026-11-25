"""Refusal codes and their Italian user messages.

Every request the backend refuses for an account, limit or size reason
returns `{"detail": {"error": <code>, "message": <Italian text>}}`. The
frontend shows `message` to the user, so each code here has exactly one
message written for the end user.
"""

from __future__ import annotations

REFUSAL_MESSAGES: dict[str, str] = {
    # Access
    "not_authenticated": "Accedi con la tua email per usare VendoCasa.",
    "session_expired": "La sessione è scaduta. Accedi di nuovo.",
    "invalid_token": "Accesso non valido. Accedi di nuovo.",
    "disposable_email": "Questo indirizzo email non è accettato. Usa un indirizzo personale.",
    "auth_unavailable": "L'accesso è momentaneamente non disponibile. Riprova più tardi.",
    "owner_only": "Questa operazione è riservata al proprietario del servizio.",
    # Limits
    "rate_limited": "Troppe richieste ravvicinate. Attendi qualche istante e riprova.",
    "daily_limit": "VendoCasa ha raggiunto il limite di richieste di oggi. Riprova domani.",
    "account_limit": (
        "Hai usato tutto il credito gratuito di questo mese. "
        "Si rinnova il primo giorno del mese prossimo."
    ),
    "global_limit": (
        "VendoCasa ha esaurito il credito gratuito disponibile per questo mese. "
        "Riprova il mese prossimo."
    ),
    "paused": "L'assistente è momentaneamente in pausa. Riprova più tardi.",
    "too_large": "Il file o la richiesta è troppo grande.",
    "account_uploads_full": (
        "Hai già caricato il massimo di documenti consentito. "
        "I documenti scadono dopo 30 minuti: riprova più tardi."
    ),
    "uploads_full": "Il caricamento dei documenti è momentaneamente pieno. Riprova più tardi.",
    "concurrent": "C'è già una risposta in corso. Attendi che finisca.",
    "model_refusal": "Non posso aiutarti con questa richiesta. Prova a riformularla.",
    # Not a refusal: the provider failed. Shown instead of the provider's error.
    "assistant_unavailable": "L'assistente non è al momento disponibile. Riprova tra poco.",
}


def refusal(code: str) -> dict[str, str]:
    """Return the response detail for a refusal code."""
    return {"error": code, "message": REFUSAL_MESSAGES[code]}
