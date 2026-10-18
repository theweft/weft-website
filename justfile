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

# Regenerate the brand set (public/brand, favicon) from brand/generate.py.
brand:
    python3 brand/generate.py "$INTER_FONT"

# The committed brand files and the logo in the pages must match the generator.
brand-check: brand
    git diff --exit-code -- public/brand public/favicon.svg brand/mark-inline.html brand/lockup-inline.html
    @for f in public/index.html public/security/index.html public/impressum/index.html public/404.html; do \
        grep -qF "$(cat brand/mark-inline.html)" "$f" || grep -qF "$(cat brand/lockup-inline.html)" "$f" || { echo "$f: logo differs from the generated inline logo"; exit 1; }; \
    done

# Spelling.
typos:
    typos

# Licence and copyright (REUSE).
licenses:
    reuse lint

# Everything CI checks.
ci: links security-txt brand-check typos licenses
