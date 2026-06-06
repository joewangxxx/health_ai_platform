import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "platform_profile_import.v1"
SOURCE_TAGS_BASE = ["platform_profile_csv", "platform_demo_profiles.v1"]
INT_PROFILE_FIELDS = {"Age", "Gender", "SBP", "DBP"}
PROVENANCE_EXTRA_DATA_FIELDS = {
    "synthea_patient_id",
    "demo_role",
    "data_source_summary",
}
EMPTY_MARKERS = {"", "null", "none", "nan"}


class ProfileCsvImportError(ValueError):
    pass


def _load_profile_schema_fields() -> set[str]:
    schema_path = Path(__file__).resolve().parents[2] / "data" / "demo" / "platform_profile_schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "Age",
            "Gender",
            "Height",
            "Weight",
            "BMI",
            "WaistCircum",
            "SBP",
            "DBP",
            "Glucose_Fasting",
            "HbA1c",
            "Cholesterol_Total",
            "Triglycerides",
            "Cholesterol_HDL",
            "Cholesterol_LDL",
            "eGFR",
            "ALT",
            "WBC",
            "Platelet",
            "GGT",
            "ALP",
            "Creatinine",
            "Sleep_Hours",
            "extra_data",
        }

    fields = schema.get("fields")
    if not isinstance(fields, list):
        raise ProfileCsvImportError("Invalid platform profile schema.")
    return {field for field in fields if isinstance(field, str)}


PROFILE_SCHEMA_FIELDS = _load_profile_schema_fields()
WRITABLE_PROFILE_FIELDS = PROFILE_SCHEMA_FIELDS - {"extra_data"}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value.strip().lower() in EMPTY_MARKERS


def _parse_number(field_name: str, value: str) -> int | float | None:
    if _is_empty(value):
        return None
    text = value.strip()
    try:
        number = float(text)
    except ValueError as exc:
        raise ProfileCsvImportError(f"Invalid numeric value for {field_name}.") from exc

    if field_name in INT_PROFILE_FIELDS:
        if not number.is_integer():
            raise ProfileCsvImportError(f"Invalid integer value for {field_name}.")
        return int(number)
    return number


def _parse_extra_data_cell(value: str) -> dict[str, Any]:
    if _is_empty(value):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ProfileCsvImportError("Invalid JSON object in extra_data.") from exc
    if not isinstance(parsed, dict):
        raise ProfileCsvImportError("extra_data must be a JSON object.")
    return parsed


def _parse_extra_value(value: str) -> Any:
    if _is_empty(value):
        return None
    text = value.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _read_csv_rows(csv_text: str) -> tuple[list[dict[str, str]], list[str]]:
    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames:
        raise ProfileCsvImportError("CSV header is required.")
    if None in reader.fieldnames:
        raise ProfileCsvImportError("CSV header contains an invalid empty column.")

    rows = [row for row in reader]
    if not rows:
        raise ProfileCsvImportError("CSV must contain at least one data row.")
    return rows, list(reader.fieldnames)


def _select_row(rows: list[dict[str, str]], demo_patient_id: str | None) -> tuple[dict[str, str], int]:
    if len(rows) == 1 and not demo_patient_id:
        return rows[0], 0

    if not demo_patient_id:
        raise ProfileCsvImportError("Multi-row CSV files require demo_patient_id selection.")

    matches = [
        (index, row)
        for index, row in enumerate(rows)
        if (row.get("demo_patient_id") or "").strip() == demo_patient_id
    ]
    if not matches:
        raise ProfileCsvImportError(f"No row found for demo_patient_id '{demo_patient_id}'.")
    if len(matches) > 1:
        raise ProfileCsvImportError(f"Multiple rows found for demo_patient_id '{demo_patient_id}'.")
    return matches[0][1], matches[0][0]


def parse_platform_profile_csv(csv_bytes: bytes, demo_patient_id: str | None = None, filename: str | None = None) -> dict[str, Any]:
    try:
        csv_text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ProfileCsvImportError("CSV must be UTF-8 encoded.") from exc

    rows, fieldnames = _read_csv_rows(csv_text)
    row, row_index = _select_row(rows, demo_patient_id.strip() if demo_patient_id else None)
    selected_demo_patient_id = (row.get("demo_patient_id") or "").strip() or None

    profile: dict[str, Any] = {}
    extra_data: dict[str, Any] = {}
    ignored_columns: list[str] = []

    for field_name in fieldnames:
        raw_value = row.get(field_name)
        if field_name in WRITABLE_PROFILE_FIELDS:
            profile[field_name] = _parse_number(field_name, raw_value)
        elif field_name == "extra_data":
            extra_data.update(_parse_extra_data_cell(raw_value))
        elif field_name.startswith("extra_data."):
            extra_key = field_name.removeprefix("extra_data.")
            if extra_key:
                extra_data[extra_key] = _parse_extra_value(raw_value)
        elif field_name in PROVENANCE_EXTRA_DATA_FIELDS:
            parsed_value = _parse_extra_value(raw_value)
            if parsed_value is not None:
                extra_data[field_name] = parsed_value
        elif field_name != "demo_patient_id":
            ignored_columns.append(field_name)

    if extra_data:
        profile["extra_data"] = extra_data

    source_tags = SOURCE_TAGS_BASE.copy()
    if selected_demo_patient_id:
        source_tags.append(f"demo_patient:{selected_demo_patient_id}")

    return {
        "schema_version": SCHEMA_VERSION,
        "demo_patient_id": selected_demo_patient_id,
        "profile": profile,
        "source_tags": source_tags,
        "metadata": {
            "filename": filename,
            "row_count": len(rows),
            "selected_row_index": row_index,
            "profile_fields": sorted(profile.keys()),
            "ignored_columns": ignored_columns,
        },
    }
