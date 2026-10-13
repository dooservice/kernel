"""What a request may carry, checked before any function sees it.

Each type is the rule for one kind of value, written once and used by every request
that takes one: a malformed value is refused with a 422 naming the field and its code,
and the service behind it only answers what needs the platform: whether it exists,
whether it is allowed, whether it fits.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field, HttpUrl, StringConstraints, UrlConstraints

from .field_rules import Rules

Trimmed = StringConstraints(strip_whitespace=True)
Lowered = StringConstraints(strip_whitespace=True, to_lower=True)

EmailAddress = Annotated[str, Trimmed, Field(max_length=254), AfterValidator(Rules.email)]
DisplayName = Annotated[str, Trimmed, Field(min_length=2, max_length=80)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
GivenPassword = Annotated[str, Field(min_length=1, max_length=128)]
OtpCode = Annotated[str, Trimmed, Field(min_length=6, max_length=6), AfterValidator(Rules.digits)]
LanguageCode = Annotated[str, Field(min_length=2, max_length=2)]
OptionalLanguageCode = Annotated[str, Field(max_length=2)]
TimeZoneName = Annotated[str, Trimmed, Field(max_length=64), AfterValidator(Rules.time_zone)]
Hour = Annotated[int, Field(ge=0, le=23)]
DnsLabel = Annotated[str, Trimmed, Field(min_length=1, max_length=63), AfterValidator(Rules.dns_label)]
InstanceName = DnsLabel
ServerName = DnsLabel
CustomDomain = Annotated[str, Lowered, Field(min_length=4, max_length=253), AfterValidator(Rules.domain)]
StorageEndpoint = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"], max_length=512)]
BranchName = Annotated[str, Trimmed, Field(min_length=1, max_length=255)]
CardholderName = Annotated[str, Trimmed, Field(min_length=2, max_length=80), AfterValidator(Rules.letters)]
