# BarPrep v3

Commercial bar/kitchen prep label system for Brother QL printers.

## v3 changes
- Public QR URLs ready for `https://barprep.stewcloud.com`
- PIN-only login; no user dropdown
- Unique staff PINs identify the user
- PIN rate limiting and session timeout
- Public read-only QR pages: `/b/<batch_code>`, `/s/<service_code>`, `/label/*`
- Protected staff actions: create, bottle, print, admin
- Compact label format to save continuous label stock
- CSV export for items

## Recommended Unraid environment variables

```text
APP_HOST=0.0.0.0
APP_PORT=5055
APP_BASE_URL=https://barprep.stewcloud.com
DATABASE_PATH=/app/data/barprep.sqlite
PRINT_MODE=brother_ql
BROTHER_MODEL=QL-820NWB
BROTHER_PRINTER=tcp://192.168.1.156:9100
BROTHER_LABEL=62
SECRET_KEY=change-this-to-a-long-random-string
SESSION_HOURS=8
```
