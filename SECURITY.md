# Security policy

## Reporting a vulnerability

Do not open a public issue. Report it privately through GitHub:
[**Report a vulnerability**](https://github.com/dooservice/kernel/security/advisories/new),
in the *Security* tab of this repository, or by email to
[soporte@apiservicesac.com](mailto:soporte@apiservicesac.com) with «Security» in the
subject.

Include the version, what an attacker can do and from where, and how to reproduce it.
The pieces most worth a look are `security` (password hashing, signed cookies, the
sealing cipher), `throttle`, `validated` and how `problems` renders an error.

We answer within **3 working days**, keep you informed while we fix it, and publish an
advisory once the fix is out, crediting you if you want. Please give us up to **90 days**
before disclosing.

Only the latest release gets fixes.
