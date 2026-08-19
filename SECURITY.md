# Security policy

mangouse reads the screen and, with an explicit grant, shares the keyboard and
pointer of a live desktop session. A bug here is not a crash — it is someone
else's password on someone else's screen. Reports are welcome.

## Reporting a vulnerability

Email **info@gianlucamazza.it** with `mangouse` in the subject. Please do not
open a public issue for a vulnerability.

Include what you need to make it reproducible: the version
(`mangouse --version`), the compositor and its version, and the smallest set of
steps that shows the problem.

This is a single-maintainer project, so treat these as intent rather than a
contractual SLA: acknowledgement within a week, an assessment within two, and
coordinated disclosure once a fix ships. If you would rather disclose publicly
on your own timeline, say so in the report.

## Supported versions

Only the latest release gets fixes. There are no maintenance branches.

## Threat model

What mangouse assumes, so you can tell a vulnerability from intended behaviour:

**Trusted.** The local user, their compositor, and the binaries mangouse shells
out to (`grim`, `wtype`, `ydotool`, `wl-paste`). mangouse runs with your
privileges and adds no sandbox of its own.

**Untrusted.** Everything that reaches it from the desktop: window titles,
`app_id` values, clipboard contents, and every pixel in a screenshot. Any web
page can put text in a window title. An agent that follows instructions found
there has been prompt-injected, and the docs say so at every layer.

**Out of scope.** That an input-enabled session can type anywhere — that is the
feature, gated behind `--allow-input`. That a screenshot of an output includes
other windows on that output — that is what capturing an output means.

**In scope** — the hardening release in the changelog is a good sample of
what qualifies:

- Anything that lets a _different local user_ reach the protocol socket, read a
  shot, or influence mangouse's behaviour.
- Any way to mutate the seat without a grant, or to keep input working while a
  lock screen is up.
- Any config value, compositor reply, or protocol frame that causes memory
  exhaustion, a crash instead of a structured error, or unexpected privilege.
- Any path where the MCP server does something other than observe.

The design that backs this is in
[docs/security-model.md](docs/security-model.md).
