import csv
import json
import re
from io import StringIO
from typing import Any

from backend.services.demo_behavior_scenarios import BehaviorScenarioRepository


MAX_BEHAVIOR_DAY_UPLOAD_BYTES = 1024 * 1024
EMPTY_MARKERS = {"", "null", "none", "nan"}
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


class BehaviorDayImportError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        error_code: str = "behavior_day_validation_failed",
        status_code: int = 400,
        path: str = "$",
        detail_code: str = "invalid_value",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = [{"path": path, "code": detail_code, "message": message}]

    def to_response_body(self) -> dict[str, Any]:
        return {
            "status": "error",
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            },
        }


def parse_behavior_day_upload(
    content: bytes,
    *,
    filename: str | None,
    content_type: str | None,
    patient_id: str | None = None,
    local_date: str | None = None,
) -> dict[str, Any]:
    if len(content) > MAX_BEHAVIOR_DAY_UPLOAD_BYTES:
        raise BehaviorDayImportError(
            "Behavior day upload must be 1 MB or smaller.",
            error_code="payload_too_large",
            status_code=413,
            path="file",
            detail_code="payload_too_large",
        )

    file_format = _detect_format(filename, content_type)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BehaviorDayImportError("Behavior day upload must be UTF-8 encoded.") from exc

    if file_format == "csv":
        parsed = _parse_csv_behavior_day(text)
        source_schema = "platform_behavior_day_csv.v1"
        source_label = "uploaded_csv"
    else:
        parsed = _parse_json_behavior_day(text)
        source_schema = "platform_behavior_day_json.v1"
        source_label = "uploaded_json"

    _validate_selector_assertions(parsed, patient_id=patient_id, local_date=local_date)

    behavior_day = _build_behavior_day(
        parsed,
        source_schema=source_schema,
        source_label=source_label,
        source_format=file_format,
        filename=filename,
    )
    lifestyle_context = _build_lifestyle_context(
        parsed,
        behavior_day,
        source_schema=source_schema,
        source_label=source_label,
        source_format=file_format,
        filename=filename,
    )
    behavior_day["lifestyle_context"] = lifestyle_context
    validation = {
        "ok": True,
        "patient_scope": "single",
        "date_scope": "single",
        "event_count": len(parsed["timeline"]),
        "max_events": 200,
        "warnings": [],
    }

    return {
        "status": "success",
        "import": {
            "schema_version": "platform_behavior_day_import_result.v1",
            "data_mode": "user_uploaded",
            "source_format": file_format,
            "filename": filename,
            "validation": {
                "event_count": len(parsed["timeline"]),
                "warnings": [],
            },
            "source_provenance": _source_provenance(source_schema, source_label, file_format, filename),
        },
        "metadata": {
            "filename": filename,
            "format": file_format,
            "byte_size": len(content),
            "patient_id": parsed["patient_id"],
            "local_date": parsed["local_date"],
        },
        "validation": validation,
        "behavior_day": behavior_day,
        "lifestyle_context": lifestyle_context,
    }


def _detect_format(filename: str | None, content_type: str | None) -> str:
    lowered_name = (filename or "").lower()
    lowered_type = (content_type or "").lower()
    if lowered_name.endswith(".csv") or lowered_type in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        return "csv"
    if lowered_name.endswith(".json") or lowered_type in {"application/json", "text/json"}:
        return "json"
    raise BehaviorDayImportError(
        "Only platform behavior CSV or JSON files are supported.",
        error_code="unsupported_media_type",
        status_code=415,
        path="file",
        detail_code="unsupported_media_type",
    )


def _parse_csv_behavior_day(text: str) -> dict[str, Any]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise BehaviorDayImportError("CSV header is required.")
    required = {"patient_id", "local_date", "time", "event_type"}
    missing = sorted(required - set(reader.fieldnames))
    if missing:
        raise BehaviorDayImportError(f"CSV missing required columns: {', '.join(missing)}.")

    rows = list(reader)
    if not rows:
        raise BehaviorDayImportError("CSV must contain at least one event row.")
    if len(rows) > 200:
        raise BehaviorDayImportError(
            "Behavior day upload may contain no more than 200 events.",
            path="timeline",
            detail_code="too_many_events",
        )

    patient_ids = {_required_text(row.get("patient_id"), "patient_id") for row in rows}
    local_dates = {_required_text(row.get("local_date"), "local_date") for row in rows}
    _validate_single_scope(patient_ids, local_dates)
    patient_id = next(iter(patient_ids))
    local_date = next(iter(local_dates))

    timeline = []
    for index, row in enumerate(rows):
        event_path = f"timeline[{index}]"
        event_type = _validate_event_type(row.get("event_type"), path=f"{event_path}.event_type")
        event = {
            "event_id": _optional_text(row.get("event_id")),
            "time": _validate_time(row.get("time"), path=f"{event_path}.time"),
            "event_type": event_type,
            "label": _optional_text(row.get("label")) or event_type.replace("_", " ").title(),
            "payload": _payload_from_csv_row(row, event_type),
        }
        timeline.append(event)

    return {
        "patient_id": _validate_patient_id(patient_id),
        "local_date": _validate_local_date(local_date),
        "timezone": None,
        "timeline": timeline,
        "summary": {},
    }


def _parse_json_behavior_day(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BehaviorDayImportError(
            f"JSON upload is not valid JSON: {exc.msg}.",
            path="$",
            detail_code="malformed_json",
        ) from exc
    if not isinstance(payload, dict):
        raise BehaviorDayImportError("JSON upload must be an object.")
    if payload.get("schema_version") != "platform_behavior_day_json.v1":
        raise BehaviorDayImportError("JSON schema_version must be platform_behavior_day_json.v1.")
    if payload.get("data_mode") == "real_device":
        raise BehaviorDayImportError("JSON upload must not claim real_device data_mode.")

    patient_id = _validate_patient_id(_required_text(payload.get("patient_id"), "patient_id"))
    local_date = _validate_local_date(_required_text(payload.get("local_date"), "local_date"))
    raw_timeline = payload.get("timeline")
    if not isinstance(raw_timeline, list) or not raw_timeline:
        raise BehaviorDayImportError("JSON timeline must contain at least one event.")
    if len(raw_timeline) > 200:
        raise BehaviorDayImportError(
            "Behavior day upload may contain no more than 200 events.",
            path="timeline",
            detail_code="too_many_events",
        )

    timeline = []
    for index, raw_event in enumerate(raw_timeline):
        event_path = f"timeline[{index}]"
        if not isinstance(raw_event, dict):
            raise BehaviorDayImportError("JSON timeline events must be objects.", path=event_path)
        if raw_event.get("data_mode") == "real_device":
            raise BehaviorDayImportError(
                "JSON timeline events must not claim real_device data_mode.",
                path=f"{event_path}.data_mode",
                detail_code="real_device_not_allowed",
            )
        event_type = _validate_event_type(raw_event.get("event_type"), path=f"{event_path}.event_type")
        raw_payload = raw_event.get("payload") or {}
        if not isinstance(raw_payload, dict):
            raise BehaviorDayImportError(
                "JSON event payload must be an object when present.",
                path=f"{event_path}.payload",
            )
        timeline.append(
            {
                "event_id": _optional_text(raw_event.get("event_id")),
                "time": _validate_time(raw_event.get("time"), path=f"{event_path}.time"),
                "event_type": event_type,
                "label": _optional_text(raw_event.get("label")) or event_type.replace("_", " ").title(),
                "payload": raw_payload,
            }
        )

    summary = payload.get("summary") or {}
    if not isinstance(summary, dict):
        raise BehaviorDayImportError("JSON summary must be an object when present.")

    return {
        "patient_id": patient_id,
        "local_date": local_date,
        "timezone": _optional_text(payload.get("timezone")),
        "timeline": timeline,
        "summary": summary,
    }


def _build_behavior_day(
    parsed: dict[str, Any],
    *,
    source_schema: str,
    source_label: str,
    source_format: str,
    filename: str | None,
) -> dict[str, Any]:
    provenance = _source_provenance(source_schema, source_label, source_format, filename)
    timeline = []
    for index, event in enumerate(parsed["timeline"], start=1):
        event_id = event["event_id"] or _generated_event_id(event["time"], event["event_type"], index)
        event_payload = _normalize_event_payload(event["event_type"], event["payload"])
        timeline.append(
            {
                "schema_version": "behavior_timeline_event.v1",
                "event_id": event_id,
                "time": event["time"],
                "event_type": event["event_type"],
                "label": event["label"],
                "data_mode": "user_uploaded",
                "payload": event_payload,
                "source_provenance": provenance,
            }
        )

    return {
        "schema_version": "behavior_day_scenario.v1",
        "scenario_id": f"uploaded_{parsed['local_date']}_{_safe_identifier(parsed['patient_id'])}",
        "patient_id": parsed["patient_id"],
        "local_date": parsed["local_date"],
        "title": "Uploaded behavior day",
        "data_mode": "user_uploaded",
        "timeline": timeline,
        "lifestyle_context": {},
        "source_provenance": provenance,
    }


def _build_lifestyle_context(
    parsed: dict[str, Any],
    behavior_day: dict[str, Any],
    *,
    source_schema: str,
    source_label: str,
    source_format: str,
    filename: str | None,
) -> dict[str, Any]:
    summary = _derive_summary(parsed)
    return {
        "schema_version": "lifestyle_context.v1",
        "data_mode": "user_uploaded",
        "scenario_id": behavior_day["scenario_id"],
        "summary": summary,
        "modifier_inputs": _derive_modifier_inputs(summary),
        "source_provenance": _source_provenance(source_schema, source_label, source_format, filename),
    }


def _payload_from_csv_row(row: dict[str, str], event_type: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    payload_json = _optional_text(row.get("payload_json"))
    if payload_json:
        try:
            parsed = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise BehaviorDayImportError("payload_json must be a JSON object.") from exc
        if not isinstance(parsed, dict):
            raise BehaviorDayImportError("payload_json must be a JSON object.")
        payload.update(parsed)

    for field in (
        "steps",
        "active_minutes",
        "sedentary_minutes",
        "sleep_hours",
        "systolic_bp",
        "diastolic_bp",
        "heart_rate",
        "summary_value",
    ):
        number = _optional_number(row.get(field), field)
        if number is not None:
            payload[field] = number
    for field in ("symptom_text", "medication_name", "summary_key", "source_note"):
        value = _optional_text(row.get(field))
        if value:
            payload[field] = value

    if event_type == "diet_vision":
        nutrition = {}
        for field in ("calories", "carbs", "protein", "fat", "sodium_mg"):
            number = _optional_number(row.get(field), field)
            if number is not None:
                nutrition[field] = number
        return {
            "schema_version": "diet_vision_event.v1",
            "meal_type": _optional_text(row.get("meal_type")) or payload.get("meal_type") or "unspecified",
            "food_items": _parse_food_items(row.get("food_items")) or payload.get("food_items") or [],
            "nutrition": nutrition,
            "vision_provenance": {
                "source_type": "user_uploaded",
                "image_ref": None,
                "model_name": None,
                "confidence": None,
            },
            **{key: value for key, value in payload.items() if key not in {"meal_type", "food_items", "nutrition"}},
        }
    return payload


def _normalize_event_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if event_type != "diet_vision":
        return normalized

    nutrition = normalized.get("nutrition")
    if not isinstance(nutrition, dict):
        nutrition = {}
    food_items = normalized.get("food_items")
    if isinstance(food_items, str):
        food_items = _parse_food_items(food_items)
    elif not isinstance(food_items, list):
        food_items = []

    return {
        **normalized,
        "schema_version": "diet_vision_event.v1",
        "meal_type": normalized.get("meal_type") or "unspecified",
        "food_items": food_items,
        "nutrition": nutrition,
        "vision_provenance": {
            "source_type": "user_uploaded",
            "image_ref": None,
            "model_name": None,
            "confidence": None,
        },
    }


def _derive_summary(parsed: dict[str, Any]) -> dict[str, Any]:
    summary = {key: value for key, value in parsed.get("summary", {}).items() if value is not None}
    totals: dict[str, float] = {}

    for event in parsed["timeline"]:
        payload = _normalize_event_payload(event["event_type"], event["payload"])
        nutrition = payload.get("nutrition") if isinstance(payload.get("nutrition"), dict) else {}
        _add_total(totals, "steps", payload.get("steps"))
        _add_total(totals, "active_minutes", payload.get("active_minutes"))
        _add_total(totals, "sedentary_minutes", payload.get("sedentary_minutes"))
        _add_total(totals, "estimated_calories", nutrition.get("calories"))
        _add_total(totals, "estimated_sodium_mg", nutrition.get("sodium_mg"))
        if "sleep_hours" not in summary and payload.get("sleep_hours") is not None:
            summary["sleep_hours"] = payload["sleep_hours"]

    for key, value in totals.items():
        summary.setdefault(key, int(value) if float(value).is_integer() else value)
    return summary


def _derive_modifier_inputs(summary: dict[str, Any]) -> dict[str, str]:
    modifiers: dict[str, str] = {}
    steps = _coerce_number(summary.get("steps"))
    active = _coerce_number(summary.get("active_minutes"))
    sleep = _coerce_number(summary.get("sleep_hours"))
    sodium = _coerce_number(summary.get("estimated_sodium_mg"))

    activity_basis = steps if steps is not None else active
    if activity_basis is not None:
        if activity_basis >= 8000 or (active is not None and active >= 45):
            modifiers["activity_level"] = "moderate"
        elif activity_basis >= 1500 or (active is not None and active > 0):
            modifiers["activity_level"] = "light"
        else:
            modifiers["activity_level"] = "low"
    if sleep is not None:
        modifiers["sleep_quality"] = "short" if sleep < 6 else "adequate"
    if sodium is not None:
        modifiers["diet_quality"] = "high_sodium" if sodium >= 2300 else "not_high_sodium"
    return modifiers


def _validate_single_scope(patient_ids: set[str], local_dates: set[str]) -> None:
    if len(patient_ids) != 1:
        raise BehaviorDayImportError(
            "Behavior day upload must contain exactly one patient.",
            path="patient_id",
            detail_code="multiple_patients",
        )
    if len(local_dates) != 1:
        raise BehaviorDayImportError(
            "Behavior day upload must contain exactly one local date.",
            path="local_date",
            detail_code="multiple_dates",
        )


def _validate_selector_assertions(
    parsed: dict[str, Any],
    *,
    patient_id: str | None,
    local_date: str | None,
) -> None:
    expected_patient_id = _optional_text(patient_id)
    if expected_patient_id and expected_patient_id != parsed["patient_id"]:
        raise BehaviorDayImportError(
            "patient_id selector does not match behavior file.",
            path="patient_id",
            detail_code="selector_mismatch",
        )

    expected_local_date = _optional_text(local_date)
    if expected_local_date:
        expected_local_date = _validate_local_date(expected_local_date, path="local_date")
        if expected_local_date != parsed["local_date"]:
            raise BehaviorDayImportError(
                "local_date selector does not match behavior file.",
                path="local_date",
                detail_code="selector_mismatch",
            )


def _validate_event_type(value: Any, *, path: str = "event_type") -> str:
    event_type = _required_text(value, "event_type", path=path)
    if event_type not in BehaviorScenarioRepository.EVENT_TYPES:
        raise BehaviorDayImportError(
            f"Unsupported event_type: {event_type}.",
            path=path,
            detail_code="unsupported_event_type",
        )
    return event_type


def _validate_patient_id(value: str) -> str:
    if not value:
        raise BehaviorDayImportError("patient_id is required.", path="patient_id", detail_code="required")
    return value


def _validate_local_date(value: str, *, path: str = "local_date") -> str:
    if not DATE_PATTERN.match(value):
        raise BehaviorDayImportError("local_date must use YYYY-MM-DD.", path=path, detail_code="invalid_date")
    return value


def _validate_time(value: Any, *, path: str = "time") -> str:
    text = _required_text(value, "time", path=path)
    if not TIME_PATTERN.match(text):
        raise BehaviorDayImportError("time must use HH:MM.", path=path, detail_code="invalid_time")
    hour, minute = [int(part) for part in text.split(":")]
    if hour > 23 or minute > 59:
        raise BehaviorDayImportError("time must be a valid HH:MM local time.", path=path, detail_code="invalid_time")
    return text


def _required_text(value: Any, field_name: str, *, path: str | None = None) -> str:
    text = _optional_text(value)
    if not text:
        raise BehaviorDayImportError(f"{field_name} is required.", path=path or field_name, detail_code="required")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in EMPTY_MARKERS:
        return None
    return text


def _optional_number(value: Any, field_name: str) -> int | float | None:
    text = _optional_text(value)
    if text is None:
        return None
    number = _coerce_number(text)
    if number is None:
        raise BehaviorDayImportError(f"Invalid numeric value for {field_name}.")
    return int(number) if float(number).is_integer() else number


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_food_items(value: Any) -> list[Any]:
    text = _optional_text(value)
    if text is None:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [item.strip() for item in text.split(";") if item.strip()]
    if isinstance(parsed, list):
        return parsed
    return []


def _add_total(totals: dict[str, float], key: str, value: Any) -> None:
    number = _coerce_number(value)
    if number is not None:
        totals[key] = totals.get(key, 0.0) + number


def _source_provenance(
    source_schema: str,
    source_label: str,
    source_format: str,
    filename: str | None,
) -> dict[str, Any]:
    provenance = {
        "source_type": "user_uploaded",
        "source_label": source_label,
        "source_format": source_format,
        "artifact_schema": source_schema,
    }
    if filename:
        provenance["filename"] = filename
    return provenance


def _generated_event_id(time_value: str, event_type: str, index: int) -> str:
    return f"evt_{time_value.replace(':', '')}_{event_type}_{index:03d}"


def _safe_identifier(value: str) -> str:
    return SAFE_ID_PATTERN.sub("_", value).strip("_") or "patient"
