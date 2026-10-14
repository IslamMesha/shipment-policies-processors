import base64
import hashlib
import hmac
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

LICENSE_PUBLIC_KEY_B64 = "jLPIp9j7ZSV36yAb5V1SBqDBgspe+AFK9rQ+p5zW/To="
APP_NAME = "ShipmentPolicyProcessor"


class LicenseError(ValueError):
    pass


def get_device_id() -> str:
    if os.name != "nt":
        raise LicenseError("Machine-bound licenses are supported on Windows only.")

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
    except OSError as exc:
        raise LicenseError(
            "Could not read this computer's Windows machine ID."
        ) from exc

    if not isinstance(machine_guid, str) or not machine_guid.strip():
        raise LicenseError("This computer has no valid Windows machine ID.")

    return hashlib.sha256(machine_guid.strip().lower().encode("utf-8")).hexdigest()


def get_license_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise LicenseError(
            "Could not locate the Windows local application data folder."
        )

    return Path(local_app_data) / APP_NAME / "license.json"


def canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def validate_license_data(
    license_data: Any,
    *,
    public_key_b64: str = LICENSE_PUBLIC_KEY_B64,
    device_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    if not isinstance(license_data, dict) or set(license_data) != {
        "payload",
        "signature",
    }:
        raise LicenseError("The license file has an invalid structure.")

    payload = license_data["payload"]
    if not isinstance(payload, dict) or set(payload) != {
        "version",
        "license_id",
        "customer",
        "device_id",
        "expires_on",
    }:
        raise LicenseError("The license payload has an invalid structure.")

    if (
        type(payload["version"]) is not int
        or payload["version"] != 1
        or not isinstance(payload["license_id"], str)
        or not payload["license_id"].strip()
        or not isinstance(payload["customer"], str)
        or not payload["customer"].strip()
        or not isinstance(payload["device_id"], str)
        or not payload["device_id"].strip()
    ):
        raise LicenseError("The license details are invalid.")

    expires_on = payload["expires_on"]
    if expires_on is not None:
        if not isinstance(expires_on, str):
            raise LicenseError("The license expiration date is invalid.")
        try:
            expiration_date = date.fromisoformat(expires_on)
        except ValueError as exc:
            raise LicenseError("The license expiration date is invalid.") from exc
        if expiration_date.isoformat() != expires_on:
            raise LicenseError("The license expiration date is invalid.")

    signature = license_data["signature"]
    if not isinstance(signature, str):
        raise LicenseError("The license signature is invalid.")

    try:
        public_key_bytes = base64.b64decode(public_key_b64, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        signature_bytes = base64.b64decode(signature, validate=True)
        public_key.verify(signature_bytes, canonical_payload(payload))
    except (ValueError, InvalidSignature) as exc:
        raise LicenseError(
            "The license signature is invalid or the app signing key is not configured."
        ) from exc

    current_device_id = device_id if device_id is not None else get_device_id()
    if not hmac.compare_digest(payload["device_id"], current_device_id):
        raise LicenseError("This license was issued for a different computer.")

    if expires_on is not None and (today or date.today()) > expiration_date:
        raise LicenseError(f"This license expired on {expires_on}.")

    return payload


def validate_license_file(path: Path | None = None) -> dict[str, Any]:
    license_path = path if path is not None else get_license_path()
    try:
        license_data = json.loads(license_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LicenseError("No license file is installed.") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LicenseError("The license file could not be read.") from exc

    return validate_license_data(license_data)


def validate_installed_license() -> dict[str, Any]:
    return validate_license_file()
