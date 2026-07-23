# Changelog

## [6.1b] - 2026-07-23
### Added
- Explicit Edge pairing contract endpoint
- API v1 aliases for registration and pairing status

### Changed
- Standardized pairing codes as six numeric digits
- Standardized flow as register, approve, then poll


## [6.1a] - 2026-07-23
### Added
- Pending-device approval workflow
- Approve and reject controls in Edge administration
- Private pairing claim tokens
- `/api/edge/pair-status` polling endpoint
- One-time API-key delivery after approval

### Changed
- Edge appliances now own their UUID and self-register
- Manual UUID matching is no longer required
- Legacy `/api/edge/pair` returns migration guidance


## [6.1] - 2026-07-23
### Added
- Edge device management
- Secure pairing codes and hashed API keys
- Heartbeats and device status
- Basic Edge print-job queue


## [6.0a] - 2026-07-15
### Fixed
- Restored missing `make_qr()` helper
- Fixed label preview/print HTTP 500 errors
- Corrected build numbering from v7.0 to v6.0a


## [7.0] - 2026-07-05
### Added
- Production Label Engine
- Region-based label rendering
- Wrapping item titles
- Full-width body details below QR
- Compact readable date formatting
- Dedicated SKU barcode footer

### Fixed
- Over-truncated titles
- QR region stealing body text width
- SKU barcode footer placement issues


## [5.6] - 2026-07-05
### Changed
- Rewrote label renderer with Header, QR, Details, and SKU Footer regions
- Improved compact label sizing
- SKU barcode now owns a full-width footer

### Fixed
- Text truncation caused by QR stealing layout width
- SKU barcode being squeezed to the lower-right


## [5.5d] - 2026-07-05
### Changed
- Dynamic compact label height
- Better use of full 62mm roll width
- Smaller right-positioned QR code
- Smaller centered SKU barcode footer

### Fixed
- Labels printing too tall after SKU barcode addition


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