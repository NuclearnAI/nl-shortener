# nl-shortener

**Internal Nuclearn URL shortener.** Private repo, SSO-gated Pages.

Each `.html` file at the repo root is a redirect page. Requesting
`https://<pages-host>/<code>` loads a static redirect page and forwards
the browser to the target URL.

Access requires being a signed-in Nuclearn org member on GitHub. External
recipients (customers, partners) cannot follow these links — they will hit
GitHub's login wall. Use this only for URLs you'd share internally on
Discord, Slack, internal docs, or team calendars.

## Adding a redirect

```bash
python3 ~/.hermes/profiles/nuclearn/skills/productivity/url-shortener/scripts/shorten.py \
    --repo ~/code/nl-shortener \
    --pages-host <host> \
    "https://your-long-url.example.com/..."
```

Prints the resulting short URL. Commits and pushes automatically.

## Threat model

Nuclearn URLs (calendar template IDs, SharePoint tokens, deal IDs, session
tokens) must not be leaked to third-party shorteners. This repo is the
Nuclearn-owned replacement — Nuclearn controls the redirect data, the
mapping database, and the domain. See the `url-shortener` skill for the
full convention.
