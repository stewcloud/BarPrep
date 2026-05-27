# BarPrep v5.3

Commercial bar/kitchen prep label system for Brother QL printers.

## v5.3 changes

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

## v5.3
- Placeholder BarPrep logo/wordmark
- Staff-only Scan Label page
- Camera QR scanning with manual fallback
- Scan label opens batch/service detail for reprint or bottling

## v5.3

- Replaces browser-native BarcodeDetector scanning with html5-qrcode
- Better camera support on iOS, Android, Windows Edge, and Chrome
- Keeps manual lookup fallback
- Adds clearer HTTPS/camera permission guidance

## v5.3
- Cleaner custom label page
- Compact recent lists on home screen
- Dedicated Bottle Existing Batch page
- Lookup supports item names and abbreviations like LJ for Lime Juice

## v5.3
- Adds Prep Workflow per item: Batch + Bottle or Direct Service
- Adds Create Service Prep workflow
- Direct service labels do not require a parent batch
- Direct service labels support QR lookup and reprint

## v5.3
- Renames prep workflows: Master Batch and Day of Prep
- Updates main action buttons with descriptions
- Makes Scan Label double-wide
- Create Master Batch now selects category before item
- Day of Prep page now handles missing item setup more safely

## v5.3
- Day of Prep disables Master Shelf Life on item add/edit
- Master Shelf ignored for Day of Prep items
- Fixes Day of Prep service label internal server error

## v5.3

- Fixes internal server errors when bottling existing master batches
- Fixes internal server errors when creating Day of Prep labels
- Rebuilds service_instances table safely when schema is from an older version
- Uses one shared safe query for all service label detail/preview/print paths


## v5.3a
- Adds visible build/version number under BarPrep logo

## v5.3b
- Fixes Day of Prep label creation TypeError in make_service_code
- Fixes Bottle Existing Batch SQL binding mismatch
- Build number updated to v5.3b
