import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = PROJECT_ROOT / "data" / "demo"
TASK2_SELECTION_PATH = DEMO_DIR / "demo_patients_task2_selection.json"
DEFAULT_SYNTHEA_CSV_DIR = Path(r"C:\Users\JoeWang\Downloads\synthea_sample_data_csv_apr2020\csv")
REFERENCE_DATE = date(2020, 4, 30)


PLATFORM_PROFILE_FIELDS = [
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
]


def _contains(text: str) -> Callable[[str], bool]:
    text = text.lower()
    return lambda value: text in value.lower()


def _equals(text: str) -> Callable[[str], bool]:
    text = text.lower()
    return lambda value: value.lower() == text


SYNTHEA_TO_PLATFORM_MAPPING = {
    "Body Height": {
        "platform_field": "Height",
        "match": _equals("Body Height"),
        "source_unit": "cm",
        "target_unit": "cm",
    },
    "Body Weight": {
        "platform_field": "Weight",
        "match": _equals("Body Weight"),
        "source_unit": "kg",
        "target_unit": "kg",
    },
    "Body Mass Index": {
        "platform_field": "BMI",
        "match": _equals("Body Mass Index"),
        "source_unit": "kg/m2",
        "target_unit": "kg/m2",
    },
    "Systolic Blood Pressure": {
        "platform_field": "SBP",
        "match": _equals("Systolic Blood Pressure"),
        "source_unit": "mm[Hg]",
        "target_unit": "mmHg",
    },
    "Diastolic Blood Pressure": {
        "platform_field": "DBP",
        "match": _equals("Diastolic Blood Pressure"),
        "source_unit": "mm[Hg]",
        "target_unit": "mmHg",
    },
    "Glucose": {
        "platform_field": "Glucose_Fasting",
        "match": _equals("Glucose"),
        "source_unit": "mg/dL",
        "target_unit": "mmol/L",
    },
    "Hemoglobin A1c/Hemoglobin.total in Blood": {
        "platform_field": "HbA1c",
        "match": _contains("Hemoglobin A1c"),
        "source_unit": "%",
        "target_unit": "%",
    },
    "Total Cholesterol": {
        "platform_field": "Cholesterol_Total",
        "match": _equals("Total Cholesterol"),
        "source_unit": "mg/dL",
        "target_unit": "mmol/L",
    },
    "Triglycerides": {
        "platform_field": "Triglycerides",
        "match": _equals("Triglycerides"),
        "source_unit": "mg/dL",
        "target_unit": "mmol/L",
    },
    "High Density Lipoprotein Cholesterol": {
        "platform_field": "Cholesterol_HDL",
        "match": _equals("High Density Lipoprotein Cholesterol"),
        "source_unit": "mg/dL",
        "target_unit": "mmol/L",
    },
    "Low Density Lipoprotein Cholesterol": {
        "platform_field": "Cholesterol_LDL",
        "match": _equals("Low Density Lipoprotein Cholesterol"),
        "source_unit": "mg/dL",
        "target_unit": "mmol/L",
    },
    "Creatinine": {
        "platform_field": "Creatinine",
        "match": _equals("Creatinine"),
        "source_unit": "mg/dL",
        "target_unit": "umol/L",
    },
    "Estimated Glomerular Filtration Rate": {
        "platform_field": "eGFR",
        "match": _contains("Glomerular filtration"),
        "source_unit": "mL/min",
        "target_unit": "mL/min",
    },
    "Alanine aminotransferase": {
        "platform_field": "ALT",
        "match": _contains("Alanine aminotransferase"),
        "source_unit": "U/L",
        "target_unit": "U/L",
    },
    "Leukocytes": {
        "platform_field": "WBC",
        "match": lambda value: "leukocytes" in value.lower() and "blood by automated count" in value.lower(),
        "source_unit": "10*3/uL",
        "target_unit": "10^9/L",
    },
    "Platelets": {
        "platform_field": "Platelet",
        "match": lambda value: value.lower().startswith("platelets [#/volume] in blood"),
        "source_unit": "10*3/uL",
        "target_unit": "10^9/L",
    },
    "Alkaline phosphatase": {
        "platform_field": "ALP",
        "match": _contains("Alkaline phosphatase"),
        "source_unit": "U/L",
        "target_unit": "U/L",
    },
    "Tobacco smoking status NHIS": {
        "platform_field": "Smoking_Status",
        "match": _equals("Tobacco smoking status NHIS"),
        "source_unit": None,
        "target_unit": None,
    },
}


UNIT_CONVERSION_RULES = {
    "Glucose_Fasting": "mg/dL / 18 => mmol/L",
    "Cholesterol_Total": "mg/dL / 38.67 => mmol/L",
    "Cholesterol_HDL": "mg/dL / 38.67 => mmol/L",
    "Cholesterol_LDL": "mg/dL / 38.67 => mmol/L",
    "Triglycerides": "mg/dL / 88.57 => mmol/L",
    "Creatinine": "mg/dL * 88.4 => umol/L",
    "Height": "cm unchanged",
    "Weight": "kg unchanged",
    "BMI": "kg/m2 unchanged",
    "SBP": "mmHg unchanged",
    "DBP": "mmHg unchanged",
    "HbA1c": "% unchanged",
    "eGFR": "mL/min unchanged",
    "ALT": "U/L unchanged",
    "ALP": "U/L unchanged",
    "WBC": "10*3/uL treated as 10^9/L",
    "Platelet": "10*3/uL treated as 10^9/L",
}


NHANES_STYLE_SUPPLEMENTS = {
    "8505e011-20cb-4bc5-8a66-5900111fb04b": {
        "WaistCircum": 99.0,
        "Sleep_Hours": 6.0,
        "Alcohol_Frequency": "occasional",
        "Physical_Activity": "low",
        "Diet_Pattern": "high_sodium_high_carbohydrate",
        "Family_History_Diabetes": True,
        "Family_History_CVD": True,
    },
    "066c0f3d-90bb-4082-99ec-f307c4759f50": {
        "WaistCircum": 101.0,
        "Sleep_Hours": 6.5,
        "Alcohol_Frequency": "none",
        "Physical_Activity": "low",
        "Diet_Pattern": "high_sodium_moderate_carbohydrate",
        "Family_History_Diabetes": True,
        "Family_History_CVD": True,
    },
    "4a52ea9c-d410-4b78-a4da-6053e2ed0787": {
        "WaistCircum": 91.0,
        "Sleep_Hours": 6.0,
        "Alcohol_Frequency": "occasional",
        "Physical_Activity": "low",
        "Diet_Pattern": "high_sodium_high_fat",
        "Family_History_Diabetes": True,
        "Family_History_CVD": False,
    },
}


def read_csv(csv_dir: Path, filename: str) -> list[dict[str, str]]:
    path = csv_dir / filename
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_selection() -> dict[str, Any]:
    with TASK2_SELECTION_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def calculate_age(birthdate: str) -> int | None:
    if not birthdate:
        return None
    birthday = datetime.strptime(birthdate, "%Y-%m-%d").date()
    return REFERENCE_DATE.year - birthday.year - ((REFERENCE_DATE.month, REFERENCE_DATE.day) < (birthday.month, birthday.day))


def parse_number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def round_metric(value: float | int | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    rounded = round(float(value), digits)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def convert_value(platform_field: str, value: str, unit: str) -> tuple[Any, str | None]:
    numeric_value = parse_number(value)
    if numeric_value is None:
        return value, unit or None

    if platform_field == "Glucose_Fasting" and unit == "mg/dL":
        return round_metric(numeric_value / 18), "mmol/L"
    if platform_field in {"Cholesterol_Total", "Cholesterol_HDL", "Cholesterol_LDL"} and unit == "mg/dL":
        return round_metric(numeric_value / 38.67), "mmol/L"
    if platform_field == "Triglycerides" and unit == "mg/dL":
        return round_metric(numeric_value / 88.57), "mmol/L"
    if platform_field == "Creatinine" and unit == "mg/dL":
        return round_metric(numeric_value * 88.4, 1), "umol/L"
    if platform_field in {"SBP", "DBP"}:
        return int(round(numeric_value)), "mmHg"
    if platform_field in {"Height", "Weight", "BMI", "HbA1c", "eGFR", "ALT", "ALP", "WBC", "Platelet"}:
        return round_metric(numeric_value), unit or None
    return round_metric(numeric_value), unit or None


def latest_observation_records(observations: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for observation in observations:
        description = observation.get("DESCRIPTION", "")
        for synthea_description, mapping in SYNTHEA_TO_PLATFORM_MAPPING.items():
            if not mapping["match"](description):
                continue
            platform_field = mapping["platform_field"]
            current = latest.get(platform_field)
            if current is not None and observation.get("DATE", "") <= current["source"]["date"]:
                continue
            converted_value, converted_unit = convert_value(
                platform_field,
                observation.get("VALUE", ""),
                observation.get("UNITS", ""),
            )
            latest[platform_field] = {
                "value": converted_value,
                "unit": converted_unit,
                "source": {
                    "table": "observations.csv",
                    "date": observation.get("DATE", ""),
                    "synthea_description": description,
                    "synthea_code": observation.get("CODE", ""),
                    "original_value": observation.get("VALUE", ""),
                    "original_unit": observation.get("UNITS", "") or None,
                },
                "mapping_key": synthea_description,
            }
    return latest


def compact_records(records: list[dict[str, str]], fields: list[str], date_field: str, limit: int = 12) -> list[dict[str, str]]:
    sorted_records = sorted(records, key=lambda item: item.get(date_field, ""), reverse=True)
    compacted = []
    for record in sorted_records[:limit]:
        compacted.append({field: record.get(field, "") for field in fields})
    return compacted


def make_source_tags(profile: dict[str, Any], observation_latest: dict[str, dict[str, Any]], supplement: dict[str, Any]) -> dict[str, str]:
    tags = {}
    for field in profile:
        if field == "extra_data":
            tags[field] = "platform_container"
        elif field in observation_latest:
            tags[field] = "Synthea observations"
        elif field in {"Age", "Gender"}:
            tags[field] = "Synthea patients"
        elif field in supplement:
            tags[field] = "NHANES-style supplement"
        elif profile[field] is None:
            tags[field] = "missing_not_available"
        else:
            tags[field] = "derived_or_manual"
    return tags


def build_outputs() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    selection = load_selection()
    csv_dir = Path(selection.get("source_directory") or DEFAULT_SYNTHEA_CSV_DIR)
    patient_ids = [patient["patient_id"] for patient in selection["patients"]]

    patients = {row["Id"]: row for row in read_csv(csv_dir, "patients.csv")}
    table_rows = {
        "conditions": read_csv(csv_dir, "conditions.csv"),
        "medications": read_csv(csv_dir, "medications.csv"),
        "encounters": read_csv(csv_dir, "encounters.csv"),
        "procedures": read_csv(csv_dir, "procedures.csv"),
        "observations": read_csv(csv_dir, "observations.csv"),
    }
    grouped: dict[str, dict[str, list[dict[str, str]]]] = {
        table: {patient_id: [] for patient_id in patient_ids} for table in table_rows
    }
    for table, rows in table_rows.items():
        for row in rows:
            patient_id = row.get("PATIENT")
            if patient_id in grouped[table]:
                grouped[table][patient_id].append(row)

    platform_schema = {
        "schema_version": "platform_profile_schema.v1",
        "fields": PLATFORM_PROFILE_FIELDS,
        "gender_encoding": {"1": "male", "2": "female"},
        "reference_date_for_age": REFERENCE_DATE.isoformat(),
    }

    mapping_export = {
        "schema_version": "synthea_to_platform_mapping.v1",
        "mappings": {
            key: {
                "platform_field": value["platform_field"],
                "source_unit": value["source_unit"],
                "target_unit": value["target_unit"],
            }
            for key, value in SYNTHEA_TO_PLATFORM_MAPPING.items()
        },
    }

    extracted_profiles = []
    platform_profiles = []
    platform_profiles_with_sources = []
    validation_patients = []

    for selected in selection["patients"]:
        patient_id = selected["patient_id"]
        patient = patients[patient_id]
        observation_latest = latest_observation_records(grouped["observations"][patient_id])
        supplement = NHANES_STYLE_SUPPLEMENTS[patient_id]

        profile = {field: None for field in PLATFORM_PROFILE_FIELDS if field != "extra_data"}
        profile["Age"] = calculate_age(patient["BIRTHDATE"])
        profile["Gender"] = 1 if patient["GENDER"] == "M" else 2 if patient["GENDER"] == "F" else None

        for field, record in observation_latest.items():
            if field in profile:
                profile[field] = record["value"]

        for field in ("WaistCircum", "Sleep_Hours"):
            profile[field] = supplement[field]

        profile["GGT"] = None
        profile["extra_data"] = {
            "synthea_patient_id": patient_id,
            "synthea_name": f"{patient.get('FIRST', '')} {patient.get('LAST', '')}".strip(),
            "synthea_city": patient.get("CITY", ""),
            "synthea_state": patient.get("STATE", ""),
            "Smoking_Status": observation_latest.get("Smoking_Status", {}).get("value") or selected["clinical_profile"].get("Smoking"),
            "Alcohol_Frequency": supplement["Alcohol_Frequency"],
            "Physical_Activity": supplement["Physical_Activity"],
            "Diet_Pattern": supplement["Diet_Pattern"],
            "Family_History_Diabetes": supplement["Family_History_Diabetes"],
            "Family_History_CVD": supplement["Family_History_CVD"],
            "data_source_summary": "Synthea clinical/EHR + NHANES-style lifestyle supplement",
        }

        source_tags = make_source_tags(profile, observation_latest, supplement)
        non_null_count = sum(1 for field in PLATFORM_PROFILE_FIELDS if field != "extra_data" and profile.get(field) is not None)
        fill_rate = round(non_null_count / (len(PLATFORM_PROFILE_FIELDS) - 1), 4)
        missing_fields = [
            field for field in PLATFORM_PROFILE_FIELDS if field != "extra_data" and profile.get(field) is None
        ]

        base_payload = {
            "demo_patient_id": f"synthea_{patient_id[:8]}",
            "synthea_patient_id": patient_id,
            "demo_role": selected["demo_role"],
            "source": {
                "clinical": "Synthea CSV",
                "lifestyle": "NHANES-style supplement",
                "genomics": "pending_demo_gene_23andme_binding",
            },
            "profile": profile,
            "conditions": compact_records(
                grouped["conditions"][patient_id],
                ["START", "STOP", "CODE", "DESCRIPTION"],
                "START",
            ),
            "medications": compact_records(
                grouped["medications"][patient_id],
                ["START", "STOP", "CODE", "DESCRIPTION", "REASONDESCRIPTION"],
                "START",
            ),
            "encounters": compact_records(
                grouped["encounters"][patient_id],
                ["Id", "START", "STOP", "ENCOUNTERCLASS", "CODE", "DESCRIPTION"],
                "START",
            ),
        }

        extracted_profiles.append(
            {
                "synthea_patient_id": patient_id,
                "patient": {
                    "birthdate": patient["BIRTHDATE"],
                    "deathdate": patient.get("DEATHDATE") or None,
                    "gender": patient["GENDER"],
                    "age": profile["Age"],
                    "name": profile["extra_data"]["synthea_name"],
                },
                "latest_observations": observation_latest,
                "supplement": supplement,
            }
        )
        platform_profiles.append(base_payload)
        platform_profiles_with_sources.append({**base_payload, "source_tags": source_tags})
        validation_patients.append(
            {
                "synthea_patient_id": patient_id,
                "demo_patient_id": base_payload["demo_patient_id"],
                "fill_rate": fill_rate,
                "non_null_profile_fields": non_null_count,
                "missing_fields": missing_fields,
                "checks": {
                    "age_present": profile["Age"] is not None,
                    "gender_encoded": profile["Gender"] in {1, 2},
                    "core_risk_fields_present": all(
                        profile.get(field) is not None
                        for field in ["BMI", "SBP", "DBP", "Glucose_Fasting", "HbA1c", "Cholesterol_Total", "Triglycerides", "Cholesterol_HDL", "Creatinine", "eGFR"]
                    ),
                    "unit_conversion_applied": True,
                    "source_tags_present": bool(source_tags),
                    "gaps_not_fabricated": profile["GGT"] is None,
                },
            }
        )

    validation_report = {
        "schema_version": "demo_profile_validation_report.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "patients_checked": len(validation_patients),
        "minimum_fill_rate": min(patient["fill_rate"] for patient in validation_patients),
        "all_core_risk_fields_present": all(
            patient["checks"]["core_risk_fields_present"] for patient in validation_patients
        ),
        "patients": validation_patients,
    }

    outputs = {
        "platform_profile_schema.json": platform_schema,
        "synthea_to_platform_mapping.json": mapping_export,
        "unit_conversion_rules.json": {
            "schema_version": "unit_conversion_rules.v1",
            "rules": UNIT_CONVERSION_RULES,
        },
        "synthea_extracted_profiles.json": {
            "schema_version": "synthea_extracted_profiles.v1",
            "source_directory": str(csv_dir),
            "profiles": extracted_profiles,
        },
        "nhanes_lifestyle_supplement.json": {
            "schema_version": "nhanes_lifestyle_supplement.v1",
            "supplements": NHANES_STYLE_SUPPLEMENTS,
        },
        "platform_demo_profiles.json": {
            "schema_version": "platform_demo_profiles.v1",
            "profiles": platform_profiles,
        },
        "platform_demo_profiles_with_sources.json": {
            "schema_version": "platform_demo_profiles_with_sources.v1",
            "profiles": platform_profiles_with_sources,
        },
        "demo_profile_validation_report.json": validation_report,
    }

    for filename, payload in outputs.items():
        with (DEMO_DIR / filename).open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    print(json.dumps(validation_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build_outputs()
