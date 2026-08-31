# Saiko Licence Control for Windows

This repository contains only the native Windows licence application. It has no
Flask/Vercel backend, no Neon integration, no database connection string, and no
browser interface.

The application connects directly to the secured licence API built into:

```text
https://saiko-inventory.vercel.app
```

Its login screen asks for only one fixed owner username and password. Those two
values are configured in the inventory Vercel project as
`LICENSE_ADMIN_USERNAME` and `LICENSE_ADMIN_PASSWORD`. The password is never
stored by the Windows application.

## Build the native Windows EXE with GitHub

1. Open this repository on GitHub.
2. Open **Actions → Build Windows Licence App**.
3. Choose **Run workflow**.
4. Open the completed run.
5. Download the `SaikoLicenceControl-Windows` artifact.
6. Extract `SaikoLicenceControl.exe` onto the dedicated Windows computer.

## Build directly on Windows

Install Python 3, then double-click:

```text
windows_app\build_windows.bat
```

The portable application will be created at:

```text
windows_app\dist\SaikoLicenceControl.exe
```

## Use the application

1. Run `SaikoLicenceControl.exe`.
2. Enter the fixed owner username.
3. Enter the fixed owner password.
4. Activate or pause inventory, change the total seat limit, or update the
   paused message.

The application requires internet access to reach Saiko Inventory. It stores a
signed login session for up to 30 days, but stores neither the owner password nor
any Neon credentials.

Windows may show a SmartScreen warning because the EXE is not commercially code
signed. Choose **More info → Run anyway** only for an EXE produced by your own
GitHub workflow.
