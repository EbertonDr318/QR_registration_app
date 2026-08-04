"""Reglas compartidas para los campos editables de una Persona."""

import re
import unicodedata

GROUPS = ("Damas", "Caballeros", "Jóvenes", "Adolescentes", "Niños")
PHONE = re.compile(r"^\d{1,25}$")


def valid_phone(value: str) -> bool:
    """Acepta un teléfono vacío o compuesto exclusivamente por dígitos."""
    return not value or bool(PHONE.fullmatch(value))


def normalize_group(value: str) -> str | None:
    """Devuelve el nombre canónico de un grupo permitido."""
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", str(value or "").strip())
        if not unicodedata.combining(character)
    ).casefold()
    aliases = {"adolecentes": "Adolescentes"}
    if normalized in aliases:
        return aliases[normalized]
    return next(
        (
            group
            for group in GROUPS
            if "".join(
                character
                for character in unicodedata.normalize("NFKD", group)
                if not unicodedata.combining(character)
            ).casefold()
            == normalized
        ),
        None,
    )
