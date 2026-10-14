"""The checks a length or a range cannot say, each refusing with its own code.

Plain string methods, no patterns: a rule somebody can read is a rule somebody can change.
"""

from __future__ import annotations

from string import ascii_letters, ascii_lowercase, digits
import uuid
from zoneinfo import available_timezones

from email_validator import EmailNotValidError, validate_email
from pydantic_core import PydanticCustomError

LABEL_CHARACTERS = frozenset(ascii_lowercase + digits + "-")
CODE_CHARACTERS = frozenset(ascii_letters + digits + "-_.")
HEX_CHARACTERS = frozenset(digits + "abcdef")


class Rules:
    """The checks a length or a range cannot say, each refusing with its own code."""

    @staticmethod
    def dns_label(value: str) -> str:
        """Lower-case letters, digits and hyphens, not starting or ending with one: what
        a name has to be to go into a domain, a folder and a container name."""
        if not set(value) <= LABEL_CHARACTERS or value.startswith("-") or value.endswith("-"):
            raise PydanticCustomError("invalid_name", "lower-case letters, digits and inner hyphens only")
        return value

    @staticmethod
    def domain(value: str) -> str:
        labels = value.split(".")
        if len(labels) < 2 or not all(labels) or not labels[-1].isalpha():
            raise PydanticCustomError("invalid_domain", "not a domain")
        for label in labels:
            Rules.dns_label(label)
        return value

    @staticmethod
    def email(value: str) -> str:
        try:
            return validate_email(value, check_deliverability=False).normalized.lower()
        except EmailNotValidError as invalid:
            raise PydanticCustomError("invalid_email", "not an email address") from invalid

    @staticmethod
    def time_zone(value: str) -> str:
        if value and value not in available_timezones():
            raise PydanticCustomError("invalid_time_zone", "not a time zone")
        return value

    @staticmethod
    def digits(value: str) -> str:
        if not value.isdigit():
            raise PydanticCustomError("invalid_code", "digits only")
        return value

    @staticmethod
    def letters(value: str) -> str:
        if not all(word.isalpha() for word in value.split()):
            raise PydanticCustomError("invalid_cardholder", "letters and spaces only")
        return value

    @staticmethod
    def identifier(value: str) -> str:
        """A UUID, in the one spelling every table stores it in."""
        try:
            return str(uuid.UUID(value))
        except ValueError as invalid:
            raise PydanticCustomError("invalid_identifier", "not an identifier") from invalid

    @staticmethod
    def code(value: str) -> str:
        """What a provider names a region or a size with: letters, digits, `-`, `_`, `.`."""
        if not set(value) <= CODE_CHARACTERS:
            raise PydanticCustomError("invalid_option", "letters, digits, '-', '_' and '.' only")
        return value

    @staticmethod
    def language_tag(value: str) -> str:
        """`es`, `pt`, `es-PE` or `pt_BR`; empty means the default."""
        language, _, region = value.replace("_", "-").partition("-")
        if value and not (
            2 <= len(language) <= 3
            and language.isascii()
            and language.isalpha()
            and language.islower()
            and (not region or (len(region) == 2 and region.isascii() and region.isalpha()))
        ):
            raise PydanticCustomError("invalid_language", "not a language")
        return value

    @staticmethod
    def country(value: str) -> str:
        """Two letters, ISO 3166, in capitals."""
        upper = value.upper()
        if len(upper) != 2 or not upper.isascii() or not upper.isalpha():
            raise PydanticCustomError("invalid_country", "not a country code")
        return upper

    @staticmethod
    def sha256(value: str) -> str:
        """A SHA-256 written out: 64 hexadecimal characters, or nothing yet."""
        lowered = value.lower()
        if value and (len(lowered) != 64 or not set(lowered) <= HEX_CHARACTERS):
            raise PydanticCustomError("invalid_digest", "not a SHA-256")
        return lowered

    @staticmethod
    def identifier_or_empty(value: str) -> str:
        return Rules.identifier(value) if value else value

    @staticmethod
    def email_or_empty(value: str) -> str:
        return Rules.email(value) if value else value
