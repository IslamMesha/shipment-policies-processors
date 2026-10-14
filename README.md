# Shipment Policy Processor

Shipment Policy Processor is a Windows desktop application for matching shipment data to policy PDF pages, validating COD amounts, and exporting updated PDFs and Excel reports.

It is designed for operations where a spreadsheet of customer shipment records must be checked against underlying policy documents and the correct serial number placed on the matching policy pages.

## Features

- Select a shipment data file in CSV or Excel format
- Select a policy PDF file
- Automatically detect the COD column from the shipment data
- Match phone numbers from shipment records to policy pages
- Flag mismatched COD values between shipment records and policy pages
- Apply serial numbers to matched PDF pages
- Export a complete Excel report with matched, unmatched, and COD-mismatch status
- Create a shipment policy PDF with serial numbers added in the correct positions
- Built-in presets for Bosta and J&T serial placement

## Project structure

- `main.py` – Qt desktop application entry point
- `services/` – data reading, PDF parsing, matching, export, and PDF writing logic
- `assets/` – application icon and related assets
- `build_windows.bat` – Windows build script for packaging the app
- `ShipmentPolicyProcessor.spec` – PyInstaller specification file

## Requirements

- Windows 10 or newer
- Python 3.x
- pip

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Running the app

From the project root:

```powershell
python main.py
```

Or on Windows with the Python launcher:

```powershell
py main.py
```

## Usage

1. Open the application.
2. Select the shipment data file (`.csv`, `.xlsx`, or `.xls`).
3. Select the policy PDF file.
4. Choose the serial placement preset or manually adjust the X/Y coordinates.
5. Click `Process PDF`.
6. Choose the output folder.
7. The app creates:
   - an Excel report containing processed shipment rows and status data
   - a shipment policy PDF with serial numbers added to matching pages when applicable

## Build for Windows

The recommended way to build the executable is:

```powershell
build_windows.bat
```

This creates an isolated build environment and packages the application with PyInstaller.

The output executable is generated in:

```text
dist\ShipmentPolicyProcessor.exe
```

For more detail, see [BUILDING_WINDOWS.md](BUILDING_WINDOWS.md).

## Licensing

The application requires a vendor-signed license tied to the Windows
computer. On first launch, copy the displayed machine ID and send it to the
software provider. Select the license file they return. The app stores it in
`%LOCALAPPDATA%\ShipmentPolicyProcessor\license.json`.

Before distributing a licensed build, generate an Ed25519 key pair using the
license administration tool. Keep the private key outside the project and
securely backed up; never ship it with the app. Embed the printed base64 public
key in `LICENSE_PUBLIC_KEY_B64` in `services/licensing.py`, then build and
distribute the app. The issuing tool is not included in the PyInstaller app.

```powershell
py tools\license_admin.py generate-keys --private-key "C:\secure\shipment-policy-private.pem"
```

The tool prompts for a passphrase to encrypt the private key. Back up the
private key and passphrase securely; losing them prevents issuing future
licenses for builds that use the corresponding public key.

Issue a machine-bound license using the machine ID provided by the customer.
Omit `--expires-on` for a perpetual license, or provide a date in `YYYY-MM-DD`
format:

```powershell
py tools\license_admin.py issue `
  --private-key "C:\secure\shipment-policy-private.pem" `
  --customer "Customer name" `
  --device-id "CUSTOMER-MACHINE-ID" `
  --expires-on 2027-10-14 `
  --output ".\customer-license.json"
```

This offline check detects forged or altered license files, but it cannot make
a client-side application crack-proof. A user with control of their computer
can patch the executable or change the system clock to bypass local expiry.
Machine binding is a deterrent, not foolproof hardware protection; reinstalling
or changing the computer may require issuing a replacement license. Periodic
online activation is needed for stronger expiry and revocation enforcement.

## Notes

- The app expects the shipment data to contain phone-number and serial-number columns.
- The PDF extraction and matching logic relies on the policy document containing recognizable phone numbers and COD totals.
- When no valid matches are found, the app still exports the Excel file but may not produce a stamped PDF.
