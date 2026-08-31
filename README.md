# Saiko Licence Control

This is the separate owner-only web interface for managing Saiko Inventory.
It is deployed independently from the inventory application and uses a fixed
owner login. It updates the shared Neon database directly, so you do not need to
issue a new licence key or redeploy the inventory app.

## Run locally

1. Open Terminal in this folder.
2. Create and activate the local Python environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`.
4. In `.env`, enter:
   - the same `DATABASE_URL` used by the inventory application;
   - a long random `SECRET_KEY`;
   - one fixed `LICENSE_ADMIN_USERNAME`; and
   - one fixed `LICENSE_ADMIN_PASSWORD`.
5. Start the portal:

   ```bash
   flask --app app run --debug --port 5001
   ```

6. Open `http://127.0.0.1:5001` and sign in.

The inventory database must already have been initialized. This licensing
project does not have or require its own `schema.sql`.

## Create the hosted web app on Vercel

1. Sign in to Vercel and choose **Add New → Project**.
2. Upload/import this licensing project separately from the inventory project.
3. Add the environment variables below under **Settings → Environment Variables**.
4. Apply them to Production (and Preview if you use previews).
5. Deploy the project and open its own Vercel URL.
6. Sign in with the one fixed owner login ID and password you configured.

Required environment variables:

- `DATABASE_URL` — exactly the same Neon PostgreSQL connection string used by
  `saiko_inventory_vercel`.
- `SECRET_KEY` — a long, random value used only by this licensing project.
- `LICENSE_ADMIN_USERNAME` — the fixed owner login ID.
- `LICENSE_ADMIN_PASSWORD` — the fixed owner password; use a strong value that
  is different from the inventory administrator password.

Recommended:

- `SESSION_COOKIE_SECURE=true`

The project targets Vercel's Singapore region (`sin1`). If the Neon database is
in another region, change `regions` in `vercel.json` to the nearest Vercel region.

## Install it as an app

The same Vercel deployment is an installable app; no App Store package is
required.

- **Android:** open the licensing URL in Chrome, open the browser menu, then
  choose **Install app** or **Add to Home screen**.
- **iPhone/iPad:** open the URL in Safari, tap **Share**, then choose
  **Add to Home Screen**.
- **Windows/macOS:** open the URL in Chrome or Edge and choose the install icon
  in the address bar.

The installed app still needs internet access before it can read or update a
licence. The offline page never exposes cached licence information.

## Connect the inventory app

In the inventory Vercel project, set:

```text
LICENSE_PORTAL_URL=https://your-licensing-project.vercel.app/
```

This optional setting adds a link from the inventory app's inactive screen to
the separate owner portal. The database connection—not this URL—is what makes
licence changes apply immediately. Keep the owner URL private where practical;
only the fixed owner credentials can open its controls.

## No separate database setup

This licensing project does not include or require a separate `schema.sql`.
Connect it to the same `DATABASE_URL` as the inventory project. It uses the
tables that were already created when the inventory database was initialized.

## Legacy files

`keys/private_key.pem`, `keys/public_key.pem`, `license.txt`, and
`license_new.txt` belong to the previous signed-token system. The new web portal
does not read or require them. They have deliberately been left untouched so no
key material is destroyed; after you confirm the new portal works, you can
archive or securely delete them manually.
