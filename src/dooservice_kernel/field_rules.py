"""The checks a length or a range cannot say, each refusing with its own code.

Plain string methods, no patterns: a rule somebody can read is a rule somebody can change.
"""

from __future__ import annotations

from string import ascii_lowercase, digits
from zoneinfo import available_timezones

from email_validator import EmailNotValidError, validate_email
from pydantic_core import PydanticCustomError

LABEL_CHARACTERS = frozenset(ascii_lowercase + digits + "-")


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
