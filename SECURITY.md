# Security Policy

## Supported versions

This is a community-maintained Home Assistant custom integration. Only the
latest released version receives fixes. Please make sure you can reproduce an
issue on the current release before reporting it.

| Version | Supported |
| ------- | --------- |
| Latest release | :white_check_mark: |
| Older releases | :x: |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately using GitHub's
[private vulnerability reporting](https://github.com/lgladdy/ha-southglos-recycling/security/advisories/new)
(the "Report a vulnerability" button under the repository's **Security** tab).

Please include:

- the integration version and your Home Assistant version
- a description of the issue and its impact
- steps to reproduce, if possible

You can expect an initial response within about a week. Once a fix is available
it will be released and the advisory published, crediting you unless you ask
otherwise.

## Scope

This integration talks to South Gloucestershire Council's public waste
collection APIs and stores only your postcode and UPRN in the Home Assistant
config entry. It does not handle credentials or payment data.

Vulnerabilities in Home Assistant core, HACS, or the council's APIs should be
reported to those projects directly.
