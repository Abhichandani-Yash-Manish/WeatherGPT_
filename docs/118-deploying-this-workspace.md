# 118 — Deploying this workspace

*20 September 2026.*

Hosting was on hold until today. It is here now for one reason beyond a shareable link: **the Web
Push API requires a secure context.** A phone on the same Wi-Fi, opening `http://192.168.1.x:8765`,
cannot register a service worker and cannot receive a push — so F4a (a live changed edition reaching
a real device), X3 (the alert climax), M1 (a touch journey) and M2 (installing as a PWA) are not
gated on code that is missing. They are gated on HTTPS. Everything else for them already exists:
VAPID keys, the outbox with its retry ladder, `POST /api/outbox/<id>/ack`, and since today the
service worker and manifest the app had always referenced but never shipped.

## What changed in the server

Three properties that were correct for a laptop are wrong for a deployment, and all three now take a
deliberate flag rather than a new default.

**It binds loopback.** `--host` defaults to `127.0.0.1` and stays there. A container passes
`--host 0.0.0.0` explicitly, and the server says so at startup — including a warning when no access
key is set, because at that point anyone who can reach the address can spend this workspace's
provider budget.

**It refuses a `Host` header it does not recognise.** That is a DNS-rebinding guard: without it, a
page on another origin could drive this server through a reader's own browser. A deployment names
its hostname with `--public-host`; loopback remains allowed. The same widening applies to the
`Origin` check on POST.

**Its token gates nothing on a public URL.** The workspace injects a random token into the page and
requires it on every API call, which stops another origin but not a person: anyone who can load the
page is handed one. So a deployment sets `WEATHERGPT_ACCESS_KEY`. A visitor opens `/?k=<key>` once;
the key moves into an HttpOnly cookie and out of the address bar, so it is not left in history or in
a screenshot.

**This is a door key, not user authentication.** Everyone holding it is the same anonymous visitor.
It exists to keep a public URL from spending the budget, and it should not be described as anything
more than that. Unset, the local experience is exactly what it was.

## What ships, and what does not

The image carries the code, the built React bundle, the registries, the geography database (the
thirty-six states, their districts and the place catalogue) and the published climate tables — about
158 MB before dependencies.

`data/runtime` does not ship. On a developer machine it holds roughly four gigabytes of accumulated
raw evidence, collected blobs and the document index, none of which is needed to start: the
workspace re-fetches what a question needs and writes new evidence beside it. It belongs on a
mounted volume so it survives a redeploy.

**A consequence worth stating plainly: a fresh deployment has no document corpus.** The indexed
bulletins live in `data/runtime/documents`, so on a cold volume every bulletin-backed answer will
correctly say it has nothing indexed until the corpus is rebuilt there. That is the honest behaviour
and not a regression, but it is not the behaviour of a laptop that has been collecting for a week.

## Deploying it

The image has not been built here — the Docker daemon was not running on this machine, so the
Dockerfile is written and its every `COPY` source verified to exist, but it is unproven. Expect the
first build to need a fix; the likely one is a missing system package for `pdfplumber`.

```bash
# 1. Build the frontend first: the image copies web/dist and does not run node.
cd frontend && npm ci && npm run build && cd ..

# 2. Install flyctl and sign in (this part is yours; it needs your account).
curl -L https://fly.io/install.sh | sh
fly auth login

# 3. Create the app and its volume. The region is Mumbai: the data, the readers
#    and the sources are all in India.
fly apps create weathergpt
fly volumes create weathergpt_runtime --region bom --size 10

# 4. Set the secrets. They are never in the repository and never in the image.
fly secrets set WEATHERGPT_ACCESS_KEY="$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')"
fly secrets set DEEPSEEK_API_KEY=...        # or OPENROUTER_API_KEY

# 5. Deploy, then read back the key you will hand to anyone who should get in.
fly deploy
fly secrets list
```

If the app is not called `weathergpt`, change `app` and `PUBLIC_HOST` in `fly.toml` together —
`PUBLIC_HOST` must match the hostname actually served or the rebinding guard refuses every request,
which looks like a total outage rather than a configuration error.

## After it is up

Open `https://<host>/?k=<key>` on a phone. The manifest and the service worker are served from the
root, so the browser will offer to install it, and a watch can subscribe to push. That is the
journey F4a, X3, M1 and M2 have been waiting for, and it can now be attempted — none of those rows
should be marked met until someone has actually done it and said what happened.

## One thing this does not solve

The stores are SQLite. Measured on 20 September 2026, running the 306-question atlas while the test
suite ran against the same files produced `database is locked` and thirty-three 503 responses. The
Fly concurrency limits are set low for that reason: they are the honest setting for this
architecture, not a throughput target it can meet. A workspace that needed to serve many readers at
once would need a different store, and that is a larger change than a deployment.
