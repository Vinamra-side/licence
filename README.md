# Saiko Licence Control

This project has two deliberately separate parts:

- a backend-only Flask API deployed on Vercel; and
- a native Windows desktop application (`SaikoLicenceControl.exe`).

There is no browser-based licence interface. The Windows program communicates
with Vercel over HTTPS, and only Vercel stores the Neon database connection.

## 1. Deploy the backend to Vercel

Import this repository as a separate Vercel project and configure:

- `DATABASE_URL` — the same Neon connection used by Saiko Inventory;
- `SECRET_KEY` — a new random secret used to sign Windows-app sessions;
- `LICENSE_ADMIN_USERNAME` — the one fixed owner login ID;
- `LICENSE_ADMIN_PASSWORD` — the one fixed owner password; and
- `OWNER_TOKEN_MAX_AGE=2592000` — optional, defaults to 30 days.

The inventory database must already have been initialized. This licence project
does not include or require a separate `schema.sql`.

After deployment, opening the Vercel URL only returns API status JSON. Licence
controls are available only through authenticated `/api/*` calls made by the
Windows application.

## 2. Build the native Windows application

### Automatic GitHub build

The workflow `.github/workflows/build-windows-app.yml` creates the Windows EXE.

1. Push this repository to GitHub.
2. Open **Actions → Build Windows Licence App**.
3. Choose **Run workflow**.
4. Open the completed run and download the
   `SaikoLicenceControl-Windows` artifact.
5. Extract `SaikoLicenceControl.exe` onto the dedicated Windows device.

### Build directly on Windows

Install Python 3, then double-click `windows_app/build_windows.bat`. The finished
program will be at:

```text
windows_app\dist\SaikoLicenceControl.exe
```

The EXE is portable and does not require Python on the destination device.

## 3. Connect the dedicated device

1. Run `SaikoLicenceControl.exe`.
2. Enter the Vercel backend URL, for example
   `https://your-licence-backend.vercel.app`.
3. Enter the fixed owner login ID and password configured in Vercel.
4. The app remembers the signed session for up to 30 days. It never stores the
   owner password or Neon database password.
5. Use the native window to activate/pause inventory, change the seat limit, or
   update the paused message.

Windows may show a SmartScreen warning for an unsigned EXE. Choose **More info →
Run anyway** only when the file came from your own GitHub build. Removing this
warning for other users requires purchasing and applying a Windows code-signing
certificate.

## API endpoints

- `GET /api/health` — backend health check.
- `POST /api/login` — fixed owner authentication.
- `GET /api/license` — current licence and seat usage.
- `PUT /api/license` — update licence controls.

Failed owner logins are rate-limited in the shared PostgreSQL database. API
responses are marked `no-store`, and the desktop application does not contain
database credentials.

## Legacy files

The ignored `keys/`, `license.txt`, and `license_new.txt` files belong to the old
signed-token system. The API and Windows app do not use them.
