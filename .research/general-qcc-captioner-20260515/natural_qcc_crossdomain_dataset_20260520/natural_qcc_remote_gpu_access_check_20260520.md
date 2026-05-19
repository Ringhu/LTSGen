# Natural QCC Remote GPU Access Check（2026-05-20）

- local head: `532aaaa5cba52f33c6dcb094d95ded164b5cd9e3`
- any access pass: `False`

| profile | reachable | access pass | root | cuda | devices | stderr |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `a100` | `False` | `False` | `None` | `None` | `None` | `ssh: Could not resolve hostname a100: Temporary failure in name resolution` |
| `3090` | `False` | `False` | `None` | `None` | `None` | `Connection closed by 0.0.12.18 port 22` |

## Interpretation

This check is a blocker diagnostic only. It does not run training and must not be treated as generated-caption QA evidence.
