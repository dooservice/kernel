# Contributing

## Before you start

- **Bugs**: open an issue with the version, what you did and what happened.
- **Changes**: for anything beyond a small fix, open an issue first. The kernel stays
  small on purpose: something only one application needs belongs in that application,
  as a module.
- **Vulnerabilities**: never in an issue. See [SECURITY.md](SECURITY.md).

## Making a change

```sh
make install
make check      # ruff, basedpyright, pytest
```

- Keep each pull request to one change, with its tests.
- The kernel names no product and imports only its dependencies;
  `tests/test_stands_alone.py` fails if it does otherwise.
- A change to `Module`, `Config`, `Profile` or `ApplicationBuilder` is a change to every
  application built on the kernel: say in the pull request what it breaks, if anything.
- No module-level functions with behaviour and no regular expressions: behaviour lives in
  small classes, and validation uses what the libraries provide or plain string rules.

## Style

Code, comments and commit messages in English. Commit messages say what the change does,
in one line: `fix: a section with no table in the file comes with its defaults`.

## Sign your commits

Every commit must carry a `Signed-off-by` line, which says you wrote the change or have
the right to submit it under this project's license, as the
[Developer Certificate of Origin](https://developercertificate.org) describes. Add it with
`git commit -s`.

## Code of conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md). Report unacceptable
behaviour to [soporte@apiservicesac.com](mailto:soporte@apiservicesac.com).

## License

By contributing, you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE), like the rest of the repository.
