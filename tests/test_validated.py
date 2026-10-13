from __future__ import annotations

from pydantic import BaseModel, ValidationError
import pytest

from dooservice_kernel.validated import CustomDomain, DnsLabel, EmailAddress, TimeZoneName


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
