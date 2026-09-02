# Inventory Licence Control

Saiko Licence and Saiko Inventory are separate, interconnected software systems.

```text
Windows Licence App
        ↓ owner username/password
Saiko Licence Service on Vercel (this repository, no Neon)
        ↓ private integration key
Saiko Inventory on Vercel
        ↓
Inventory's Neon database
```

The licence service never connects to Neon and contains no inventory database
credentials. The Windows application shows only username and password fields.

## Deploy this licence service separately

Create a new Vercel project from this repository and configure:

```text
SECRET_KEY=<new random secret for signed owner sessions>
LICENSE_ADMIN_USERNAME=<one fixed owner username>
LICENSE_ADMIN_PASSWORD=<one fixed owner password>
OWNER_TOKEN_MAX_AGE=2592000
INVENTORY_API_URL=https://saiko-inventory.vercel.app
LICENSING_INTEGRATION_KEY=<same random integration key used by inventory Vercel>
```

Do not add `DATABASE_URL`, Neon variables, or run `schema.sql` in this project.

After deployment, verify `https://YOUR-LICENCE-PROJECT.vercel.app/api/health`
returns `{"status":"ok"}`.

## Configure the connection in inventory

The inventory Vercel project needs only the matching machine key:

```text
LICENSING_INTEGRATION_KEY=<same value as the licence Vercel project>
```

The owner username/password belong only to this licence project. They are not
configured in inventory.

## Build the native Windows application

The executable is a WebView2 desktop shell around the deployed licence app.
Normal interface updates arrive from Vercel without replacing the executable.

1. In this GitHub repository, open **Settings → Secrets and variables → Actions
   → Variables**.
2. Create `LICENCE_API_URL` with the final licence Vercel URL.
3. Open **Actions → Build Inventory Licence Control → Run workflow**.
4. Download the `InventoryLicenceControl-Windows` artifact.
5. Extract `InventoryLicenceControl.exe` onto the dedicated Windows device.

The build inserts the service URL into the EXE. The user sees only owner username
and password when signing in.

To build directly on Windows, first update `windows_app/backend_config.py` with
the final licence Vercel URL, then run `windows_app/build_windows.bat`.

## Security boundary

- Owner credentials exist only in the licence Vercel environment.
- Neon credentials exist only in the inventory Vercel environment.
- The private integration key exists in both Vercel projects but is never stored
  in the Windows application.
- Licence changes are validated and written by inventory, not by the licence
  service.
