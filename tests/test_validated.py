from __future__ import annotations

from pydantic import BaseModel, ValidationError
import pytest

from dooservice_kernel.validated import (
    CountryCode,
    CustomDomain,
    DnsLabel,
    EmailAddress,
    Identifier,
    LanguageTag,
    ProviderCode,
    Sha256,
    TimeZoneName,
)


class Form(BaseModel):
    email: EmailAddress = "a@b.co"
    label: DnsLabel = "shop"
    domain: CustomDomain = "example.com"
    zone: TimeZoneName = "America/Lima"


def test_an_email_is_trimmed_and_lowered() -> None:
    assert Form(email="  Ana@Example.COM ").email == "ana@example.com"


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"label": "Shop"}, "invalid_name"),
        ({"label": "-shop"}, "invalid_name"),
        ({"domain": "example"}, "invalid_domain"),
        ({"zone": "Mars/Base"}, "invalid_time_zone"),
        ({"email": "no-at-sign"}, "invalid_email"),
    ],
)
def test_a_malformed_value_is_refused_with_its_code(values: dict, code: str) -> None:
    with pytest.raises(ValidationError) as refused:
        Form(**values)
    assert refused.value.errors()[0]["type"] == code


class Request(BaseModel):
    environment_id: Identifier = "00000000-0000-0000-0000-000000000001"
    region: ProviderCode = "fsn1"
    language: LanguageTag = ""
    country: CountryCode = "PE"
    sha256: Sha256 = ""


def test_what_comes_in_is_written_the_one_way_it_is_kept() -> None:
    received = Request(
        environment_id="00000000000000000000000000000001", country="pe", sha256="A" * 64, language="es-PE"
    )
    assert received.environment_id == "00000000-0000-0000-0000-000000000001"
    assert received.country == "PE"
    assert received.sha256 == "a" * 64
    assert Request(language="pt_BR").language == "pt_BR"


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"environment_id": "shop"}, "invalid_identifier"),
        ({"region": "fsn 1"}, "invalid_option"),
        ({"language": "Spanish"}, "invalid_language"),
        ({"language": "es-PER"}, "invalid_language"),
        ({"country": "PER"}, "invalid_country"),
        ({"sha256": "xyz"}, "invalid_digest"),
    ],
)
def test_a_value_of_the_new_kinds_is_refused_with_its_code(values: dict, code: str) -> None:
    with pytest.raises(ValidationError) as refused:
        Request(**values)
    assert refused.value.errors()[0]["type"] == code
