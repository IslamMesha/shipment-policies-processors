import argparse
import base64
import getpass
import json
import uuid
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)


def canonical_payload(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def generate_keys(private_key_path: Path) -> None:
    if private_key_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing private key: {private_key_path}"
        )
    passphrase = getpass.getpass("Private-key passphrase: ")
    confirmation = getpass.getpass("Confirm passphrase: ")
    if not passphrase or passphrase != confirmation:
        raise ValueError("Passphrases must be non-empty and match.")

    private_key = Ed25519PrivateKey.generate()
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                passphrase.encode("utf-8")
            ),
        )
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    print("Embed this base64 Ed25519 public key in services/licensing.py:")
    print(base64.b64encode(public_key).decode("ascii"))
    print(f"Private signing key saved to: {private_key_path}")


def issue_license(
    private_key_path: Path,
    output_path: Path,
    customer: str,
    device_id: str,
    expires_on: str | None,
) -> None:
    if expires_on is not None:
        try:
            expiration_date = date.fromisoformat(expires_on)
        except ValueError as exc:
            raise ValueError("Expiration date must use YYYY-MM-DD.") from exc
        if expiration_date.isoformat() != expires_on:
            raise ValueError("Expiration date must use YYYY-MM-DD.")
        if expiration_date < date.today():
            raise ValueError("Expiration date must not be in the past.")

    passphrase = getpass.getpass("Private-key passphrase: ")
    private_key = serialization.load_pem_private_key(
        private_key_path.read_bytes(),
        password=passphrase.encode("utf-8"),
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("The private key must be an Ed25519 key.")

    payload = {
        "version": 1,
        "license_id": str(uuid.uuid4()),
        "customer": customer.strip(),
        "device_id": device_id.strip().lower(),
        "expires_on": expires_on,
    }
    if not payload["customer"] or not payload["device_id"]:
        raise ValueError("Customer and machine ID must not be empty.")
    try:
        if len(payload["device_id"]) != 64:
            raise ValueError
        bytes.fromhex(payload["device_id"])
    except ValueError as exc:
        raise ValueError("Machine ID must be a 64-character SHA-256 hex value.") from exc

    license_data = {
        "payload": payload,
        "signature": base64.b64encode(
            private_key.sign(canonical_payload(payload))
        ).decode("ascii"),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(license_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"License saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate signing keys and issue Shipment Policy Processor licenses."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    keys_parser = subparsers.add_parser(
        "generate-keys",
        help="Generate a vendor signing key and print its app public key.",
    )
    keys_parser.add_argument("--private-key", required=True, type=Path)

    issue_parser = subparsers.add_parser("issue", help="Issue a machine-bound license.")
    issue_parser.add_argument("--private-key", required=True, type=Path)
    issue_parser.add_argument("--customer", required=True)
    issue_parser.add_argument("--device-id", required=True)
    issue_parser.add_argument("--expires-on", help="Optional date in YYYY-MM-DD format.")
    issue_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "generate-keys":
        generate_keys(args.private_key)
    else:
        issue_license(
            args.private_key,
            args.output,
            args.customer,
            args.device_id,
            args.expires_on,
        )


if __name__ == "__main__":
    main()
