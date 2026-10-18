# Run `just` to list recipes. CI runs `just ci` inside `nix develop`.

default:
    @just --list

# Preview at http://localhost:8000 (plain file server; _headers only apply on Cloudflare).
serve:
    python3 -m http.server --directory public 8000

# Preview with Cloudflare's runtime, including _headers and the 404 page.
dev:
    wrangler dev

# Broken local links and missing files (offline; external links are not fetched).
links:
    lychee --offline --no-progress --root-dir "$PWD/public" 'public/**/*.html'

# security.txt must not expire within the next 60 days (RFC 9116: renew before expiry).
security-txt:
    @expires=$(sed -n 's/^Expires: //p' public/.well-known/security.txt); \
    left=$(( ( $(date -d "$expires" +%s) - $(date +%s) ) / 86400 )); \
    if [ "$left" -lt 60 ]; then echo "security.txt expires in $left days: update Expires"; exit 1; fi; \
    echo "security.txt valid for $left more days"

# Spelling.
typos:
    typos

# Licence and copyright (REUSE).
licenses:
    reuse lint

# Everything CI checks.
ci: links security-txt typos licenses
