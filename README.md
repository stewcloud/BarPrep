# BarPrep

Commercial prep and bar labeling system for Brother QL printers.

## New in v2

- BarPrep branding
- Staff PIN login
- Public QR scan pages remain read-only
- Create/bottle/print/admin actions require PIN
- More compact labels to reduce continuous-roll waste
- GitHub Actions publishes `ghcr.io/stewcloud/barprep:latest`

## Default users

Change these immediately after first launch:

- Sean / 1234
- Cat / 2222

## Unraid variables

Mock mode:

```text
APP_HOST=0.0.0.0
APP_PORT=5055
APP_BASE_URL=http://192.168.1.149:5055
DATABASE_PATH=/app/data/barprep.sqlite
PRINT_MODE=mock
```

Real printing:

```text
PRINT_MODE=brother_ql
BROTHER_MODEL=QL-820NWB
BROTHER_PRINTER=tcp://192.168.1.156:9100
BROTHER_LABEL=62
```

## Notes on internet exposure

Do not expose this directly to the internet yet. Put it behind Cloudflare Access, Tailscale, or another authentication layer first. The app PIN is useful for staff workflow, but it is not a full internet security layer yet.
