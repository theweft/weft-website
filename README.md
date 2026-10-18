<h1><img src="https://theweft.org/brand/repos/weft-website.svg" alt="" width="44" height="44" align="absmiddle"> weft-website</h1>

The [theweft.org](https://theweft.org) website: a static placeholder for now. Plain HTML and CSS in
[public/](public/), no build step, no external resources, no tracking.

| Path | Content |
|---|---|
| `/` | What weft is, status, links |
| `/security/` | How to report vulnerabilities (GitHub private reporting first, then security@theweft.org) |
| `/.well-known/security.txt` | Machine-readable security contact ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)) |
| `/brand/` | Logo, wordmark, lockups, icons and social preview; see [brand/README.md](brand/README.md) |
| `_headers` | Strict Content-Security-Policy and other security headers, applied by Cloudflare |

## Deploy on Cloudflare

Cloudflare builds from this GitHub repository on every push to `main`; nothing to build.

1. Push this repository to `github.com/theweft/weft-website`.
2. Cloudflare dashboard: **Workers & Pages** > **Create** > **Import a repository**, pick
   `weft-website`. [wrangler.jsonc](wrangler.jsonc) tells Cloudflare to serve `public/`. Leave the
   build command empty; the deploy command is `npx wrangler deploy`.
3. In the new Worker: **Settings** > **Domains & Routes** > **Add** > **Custom domain**:
   `theweft.org` and `www.theweft.org`. Cloudflare creates the DNS records and certificate
   (the zone is already on Cloudflare).
4. Check `https://theweft.org/.well-known/security.txt` returns the file as plain text.
5. Optional: redirect the other domains (theweft.dev, weftfleet.org/.dev/.com) to theweft.org
   with a **Redirect Rule** or **Bulk Redirects** in each zone.

Alternative: a Cloudflare Pages project with build output directory `public` serves the same
files, including `_headers`.

## Development

`nix develop` (or direnv) provides `just`, `wrangler` and the checks.

- `just serve`: preview with a plain file server.
- `just dev`: preview with Cloudflare's runtime (applies `_headers`).
- `just ci`: link check, security.txt expiry, spelling, licences.

`security.txt` carries an `Expires` date; CI fails 60 days before it, and runs weekly so this
is noticed. Update the date (at most a year ahead) when it does.

## Licence

MIT. See [LICENSE](LICENSE).
