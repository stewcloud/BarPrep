# BarPrep v4.2

Commercial bar/kitchen prep label system for Brother QL printers.

## v4.2 changes

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
