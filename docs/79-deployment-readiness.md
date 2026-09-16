# Deployment readiness

16 September 2026. The question asked was "let's deploy it". This records what is running now, what the
standing record says about hosting, and exactly what each further path would require. **Nothing beyond the
local loopback service was deployed.**

## What is running now (measured on this machine)

```sh
python3 scripts/start_weather.py --port 8765     # project environment; preflight first, then serve
```

- Serving on `http://127.0.0.1:8765`, loopback only, with a per-process session token injected into the page.
- **Host guard:** `curl -H 'Host: weather.example.com' http://127.0.0.1:8765/` answers **403**
  `{"error": "Use the loopback URL printed by the server"}`. The server refuses to be reached under another
  name, so it cannot simply be put behind a proxy or a public DNS record.
- **Token guard:** `/api/overview` without the session token answers **403**; with it, **200**.
- **Preflight passes:** Python, registries, gazetteer, port, runtime store, providers (OpenRouter configured,
  7 free model ids), web push package. The document corpus was measured earlier in this session at 7,372
  passages in 588 documents.
- A running process serves what it started with: restart it after pulling changes (already in the README).

## The standing hold, quoted

- `docs/53-operations.md`: "hosting and sharing remain on hold at the user's request".
- `docs/72-integrated-status-and-ps-review.md`: the authorized batch "does not deploy or host the product",
  and "No force push, hosting, deployment or actual notification send" is part of it.
- Every batch registry entry records `hosting_performed: false`.
- `data/registry/source-review.json` policy: `review_decision: approved_local_prototype`,
  `redistribution: not_approved`, `production_approval: not_granted` — "Approval covers local prototype use
  of technically verified addresses only; it grants no redistribution right and no operational clearance."
  69 sources are registered; several are `blocked_access` behind credential or licence gates (S01, S02 …).

That hold is the user's decision to keep or lift. The source clause is not mine to override either way.

## Path A — local service (available now)

Nothing further is required; the command above is the deployment. It is single-user by construction: one
loopback process, one token per process, runtime sqlite stores, no accounts, no uptime supervision (it is a
foreground process; the plan watcher runs inside it), and all data stays in `data/runtime`. This is what the
evidence in this repository describes and what the acceptance screenshots were taken against.

## Path B — LAN, or one more person at the desk

Would need code and configuration changes, not just a command:
1. bind to a routable interface and replace the hard-coded `allowed_host()` loopback check;
2. TLS (a self-signed certificate at minimum) because the session token travels in a header;
3. an authentication story — today the "auth" is a per-process token printed to the operator's terminal;
4. per-person isolation of conversations, watches and plans (each is a single sqlite file with a single
   writer and no user column);
5. rate limits and backpressure, because source budgets and usage terms bound how often the products may be
   read, and one shared process would serve everyone's reads;
6. a decision on what the second person may see of the first person's stored conversations and briefs.

## Path C — public hosting

Everything in Path B, plus decisions that are yours rather than mine:
- **Lift the hold explicitly**, with the record updated (the hold is quoted above, from three places).
- **A host and a domain**, or "pick a PaaS and I will use it": the container must serve the workspace's own
  HTTP layer (the Host check and the token model move with it).
- **Secrets on the server**: the OpenRouter key (and the Sarvam key if voice is exposed) would live in the
  host's configuration, and both should be rotated before they are provisioned anywhere.
- **Source terms**: the redistribution clause above. Several connected families are published documents and
  official warning products; displaying them publicly is a redistribution question the ledger currently
  answers with `not_approved`.
- **Cost and quota**: the free-model tier has rate limits, source products have budgets, and the blocked
  families need credentials nobody has yet.
- **Privacy**: questions, coordinates and any recorded voice would leave this machine; conversations are
  currently a local sqlite file, and document bodies are pruned after seven days while passages and hashes
  are kept.
- **The capability statement a public page must carry**: no warning delivery, no origin authentication, no
  all-clear, and no operational clearance. A public page that looks like an official warning service is the
  precise risk this project has been engineered to avoid.

## What I need from you before going further

1. Which target: **local only**, **LAN**, or **public**.
2. If public or LAN: is the hosting hold lifted for this, and where should it run (a host you name, or a PaaS
   you want me to choose)?
3. Authentication: one shared password, or individual accounts?
4. Which source families may be displayed to other people, given the ledger's `redistribution: not_approved`.
5. Whether the model and voice keys may be provisioned as server secrets — and rotated first.

## What I will not do without those answers

Publish source documents or official warning text beyond the approved local-prototype scope, expose the
runtime stores (conversations, watches, briefs, evidence), or move the workspace off loopback.

