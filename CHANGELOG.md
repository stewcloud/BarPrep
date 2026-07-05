# Changelog

## [5.5c] - 2026-07-05
### Fixed
- Restored missing QR code
- Fixed label scale/geometry regression
- Prevented SKU barcode from overlapping text

### Changed
- SKU barcode is now a compact footer overlay under the proven utility label layout


## [5.5b] - 2026-07-05
### Fixed
- Remaining Pillow `Image.ANTIALIAS` print failure from brother_ql dependency
- SKU barcode overlapping label text

### Changed
- SKU barcode now uses a dedicated bottom strip


## [5.5a] - 2026-07-05
### Fixed
- Pillow ANTIALIAS print failure
- Clipped SKU barcode preview layout


## [5.5] - 2026-05-27
### Added
- Numeric-only SKU field on Items
- Auto-generated SKU values
- Bottom Code 128 SKU barcode on labels
- SKU display on item/search pages

### Changed
- Label layout keeps QR in current position and adds SKU barcode as bottom line


## [5.4d] - 2026-05-27
### Added
- Search / Lookup page
- Quick reprint actions
- Recent item shortcuts
- Item archive/restore
- Startup deployment log

### Changed
- Default port changed from 5055 to 8540


## [5.4c] - 2026-05-27
### Added
- Hamburger navigation menu
- Floating plus create menu
- Grouped navigation sections

### Changed
- Simplified top bar
- Simplified dashboard quick actions


## [5.4b] - 2026-05-27
### Added
- Optional Emergency Admin PIN via `EMERGENCY_ADMIN_PIN`
- Admin Health page
- Friendly error pages

### Changed
- Admin role always has full permission fallback


## [5.4] - 2026-05-27
### Added
- Admin Role Permissions page
- Permission-aware navigation and route guards
- Infinite shelf-life option using ∞

### Changed
- Removed Sauces category
- Added Mixes category
- Moved Prep Workflow directly under Item Name
- Day of Prep disables Master Shelf Life

### Fixed
- Labels display NO EXPIRATION for infinite shelf life