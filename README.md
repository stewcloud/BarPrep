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

## v5.3c
- Correctly patches make_service_code to support Day of Prep labels
- Correctly patches Bottle Existing Batch insert values
- Build number updated to v5.3c

## v5.3d
- Adds missing get_service_record helper
- Fixes Day of Prep detail page after successful label creation
- Ensures service detail, preview, and print paths use one safe service lookup
- Build number updated to v5.3d

## v5.4
- Removes Sauces category
- Moves Prep Workflow under Item Name
- Adds infinite shelf-life option
- Adds Admin Role Permissions page
- Adds permission-aware navigation and route protection
- Build number updated to v5.4

## v5.4a
- Fixes startup failure caused by permission decorator loading before helper definition
- Build number updated to v5.4a

## v5.4b
- Adds optional Emergency Admin PIN via `EMERGENCY_ADMIN_PIN`
- Adds Admin Health page at `/admin/health`
- Adds friendlier 403/404/500 error pages
- Admin role now always has full permission fallback
- Build number updated to v5.4b

## v5.4c
- Replaces cluttered top navigation with hamburger menu
- Adds floating plus create menu
- Groups navigation into Production, Management, and Account
- Simplifies dashboard actions
- Build number updated to v5.4c

## v5.4d
- Changes default port from 5055 to 8540
- Adds startup log with version, port, base URL, and print mode
- Adds Search / Lookup page with item, batch, service, and abbreviation search
- Adds quick reprint actions from lookup results
- Adds recent item shortcuts on creation pages
- Adds item archive/restore actions
- Build number updated to v5.4d

## v5.5
- Adds numeric-only SKU field to Items
- Auto-generates numeric SKU values for existing and new items
- Adds Code 128 SKU barcode to the bottom line of master and service labels
- Keeps QR code in the approved current position for public label lookup
- SKU can be used by external inventory systems without vendor prefixes
- Build number updated to v5.5

## v5.5a
- Fixes Pillow ANTIALIAS print failure
- Fixes clipped SKU label preview layout
- Keeps QR top-right and SKU barcode on bottom line
- Build number updated to v5.5a

## v5.5b
- Adds Pillow ANTIALIAS compatibility monkeypatch for brother_ql printing
- Moves SKU barcode into a dedicated bottom zone
- Increases label canvas height to prevent barcode/text overlap
- Build number updated to v5.5b

## v5.5c
- Restores QR code to the proven top-right utility label position
- Restores compact v5.4-style label geometry
- Adds SKU barcode as a small isolated footer instead of overlapping content
- Keeps Pillow/brother_ql print compatibility
- Build number updated to v5.5c

## v5.5d
- Polishes label scale and cut length
- Uses dynamic compact label height, targeting roughly 1.25–1.5 inches when possible
- Uses full roll width more efficiently
- Keeps QR code visible and right-positioned
- Keeps SKU barcode compact in the bottom footer
- Build number updated to v5.5d

## v5.6
- Rewrites label renderer around layout regions instead of fixed coordinates
- Keeps title readable while reserving QR region
- Uses full label width for detail lines below QR area
- Adds dedicated full-width SKU footer
- Preserves compact 62mm continuous-roll utility label style
- Build number updated to v5.6

## v7.0
- Production Label Engine
- Adds region-based label renderer with wrapping title
- Only header content avoids QR; body details use full width below QR
- Shorter readable date format on labels
- Dedicated full-width SKU footer
- Build number updated to v7.0

## v6.0a
- Fixes missing make_qr helper
- Fixes label preview and printing HTTP 500 errors
- Corrects displayed build numbering from v7.0 to v6.0a
