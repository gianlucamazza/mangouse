# Documentation

[← back to the project README](../README.md)

## Start here

| Page                           | For                                                                                |
| ------------------------------ | ---------------------------------------------------------------------------------- |
| [quickstart.md](quickstart.md) | First run: `doctor`, `desktop`, your first shot, and what to do when a check fails |

## Reference

| Page                                 | For                                                                                                                                        |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| [cli-reference.md](cli-reference.md) | Every command and flag, the MCP surface, and the DevTools path                                                                             |
| [json-contract.md](json-contract.md) | The `--json` envelope, per-action keys, error codes, and the rules a host must follow. **Authoritative** — no other page may contradict it |
| [configuration.md](configuration.md) | `config.toml` keys and every environment variable                                                                                          |

## Understanding

| Page                                   | For                                                                                    |
| -------------------------------------- | -------------------------------------------------------------------------------------- |
| [architecture.md](architecture.md)     | What problem this solves, the layers, the glossary, and the non-goals                  |
| [security-model.md](security-model.md) | The seat grant, what the core enforces, what it does not, and what counts as untrusted |

## Extending and maintaining

| Page                                     | For                                       |
| ---------------------------------------- | ----------------------------------------- |
| [backends/README.md](backends/README.md) | Writing an adapter for another compositor |
| [backends/mango.md](backends/mango.md)   | The first adapter, as a worked example    |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Dev loop, test suite, layout rules        |
| [releasing.md](releasing.md)             | Maintainer release checklist              |

## Conventions

Facts live in exactly one place and are linked from the others. If you find the
same rule stated twice, one of the copies is a bug — that is how the docs
drifted from the code before, and `tests/test_docs_alignment.py` now checks the
parts a test can check: flags, error codes, MCP tools, `doctor` keys,
environment variables, and every relative link on this page.
