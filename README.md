# Kitchen Label System MVP

A tablet-friendly commercial prep label system for Brother QL printers.

Built for:
- Brother QL-820NWB
- Unraid Docker
- SQLite
- QR batch/service lookup
- Master batch labels
- Service / in-use bottle labels

## What works in this MVP

- Create users
- Create/edit item presets
- Create master batches
- Bottle existing batches into service instances
- Auto-calculate expiration dates
- Generate QR codes
- View batch/service detail pages from QR scans
- Reprint labels
- Preview labels in browser
- Optional direct Brother QL network printing

## Recommended first run

Start in mock mode first so you can test without wasting labels.

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://YOUR_UNRAID_IP:5055
```

## Printing modes

In `.env`:

```text
PRINT_MODE=mock
```

This only generates label images.

When ready to print directly:

```text
PRINT_MODE=brother_ql
BROTHER_MODEL=QL-820NWB
BROTHER_PRINTER=tcp://192.168.1.156:9100
BROTHER_LABEL=62
```

Then rebuild/restart:

```bash
docker compose up --build -d
```

## Unraid deployment

Option A: Docker Compose plugin

1. Create a new folder on Unraid:
   ```text
   /mnt/user/appdata/kitchen-label-system
   ```
2. Upload this project folder there.
3. Edit `.env`.
4. Run from Unraid terminal:
   ```bash
   cd /mnt/user/appdata/kitchen-label-system
   docker compose up --build -d
   ```

Option B: Add as a custom Docker container

Use this repo as a local build, or push to GitHub and use Unraid with a Dockerfile build workflow.

## GitHub setup

From your computer:

```bash
git init
git add .
git commit -m "Initial kitchen label system MVP"
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/kitchen-label-system.git
git push -u origin main
```

Keep `.env` private. It is ignored by Git.

## Default sample data

The app seeds:
- Users: Sean, Cat
- Items:
  - Passionfruit Puree
  - Lime Juice
  - Orgeat
  - Simple Syrup

## Label logic

### Master batch

Example:
- Sean makes Passionfruit Puree
- Master batch shelf life: 7 days refrigerated
- Label prints a batch QR

### Service bottle

Example:
- Cat bottles the batch two days later
- In-use shelf life: 24 hours
- Label prints a service QR
- Service expiration can be shorter than master batch expiration

The service expiration is calculated as:

```text
bottled_at + in_use_shelf_life_hours
```

But it will never exceed the parent batch expiration.

## Roadmap

Good next features:
- PIN protection for staff actions
- Admin-only item editing
- Mark discarded
- Print quantity
- Better Brother web fallback adapter
- CSV import/export for items
