# BarPrep v4.4

Commercial bar/kitchen prep label system for Brother QL printers.

## v4.4 changes

- Custom label page with icon/emoji/symbol field
- Compact custom label renderer
- Item database is collapsed by category
- Click into an item to edit
- Separate Add Item page
- User roles:
  - Bartender
  - Barback
  - Bar Prep
  - Manager
  - Admin
- Bartender and Barback currently share the same basic permission set
- Bar Prep, Manager, and Admin can add/edit items
- Manager and Admin can manage users
- PIN-only login
- Public QR URLs for `https://barprep.stewcloud.com`
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

For safe testing:

```text
PRINT_MODE=mock
```

## v4.4
- Placeholder BarPrep logo/wordmark
- Staff-only Scan Label page
- Camera QR scanning with manual fallback
- Scan label opens batch/service detail for reprint or bottling

## v4.4

- Replaces browser-native BarcodeDetector scanning with html5-qrcode
- Better camera support on iOS, Android, Windows Edge, and Chrome
- Keeps manual lookup fallback
- Adds clearer HTTPS/camera permission guidance
