# Task 2: Synthea Demo Patient Selection

## Selection Goal

Select three Synthea patients that can support a stable graduation-defense demo for HealthAI Platform:

- enough clinical fields to fill the clinical profile page;
- clear chronic-disease storyline;
- medication and encounter history for Dr. AI and pharmacy explanation;
- distinct demo value, so the three patients do not tell the same story.

Source directory:

`C:\Users\JoeWang\Downloads\synthea_sample_data_csv_apr2020\csv`

## Screening Rules

The full scan used these filters:

- age preferably between 40 and 75 for a relatable adult chronic-disease demo;
- patient is alive in `patients.csv`;
- at least 15 target clinical fields available from `observations.csv`;
- diagnosis history includes at least two useful chronic-risk themes;
- recent observations and medications are not too sparse;
- avoid patients whose values are too extreme or difficult to explain in a short defense.

Target clinical fields checked:

`Height`, `Weight`, `BMI`, `SBP`, `DBP`, `Glucose`, `HbA1c`, `Total Cholesterol`, `Triglycerides`, `HDL`, `LDL`, `Creatinine`, `eGFR`, `ALT`, `ALP`, `WBC`, `Platelet`, `Smoking`.

## Recommended Patient 1: Primary Demo Patient

Patient ID: `8505e011-20cb-4bc5-8a66-5900111fb04b`

Identity:

- Name: Belinda283 Kilback373
- Age: 60
- Gender: Female
- Status: alive
- City: Fairhaven

Why this patient is the best primary demo:

- Strongest complete chronic-disease story.
- Has diabetes, metabolic syndrome, hypertriglyceridemia, hyperglycemia, hyperlipidemia, obesity history, and hypertension.
- Has active chronic medications: metformin, simvastatin, and amlodipine/hydrochlorothiazide/olmesartan.
- Clinical fields are very complete: 18 target fields found.
- Ideal for showing OCR/clinical filling, CKM staging, diabetes risk, blood pressure warning, medication explanation, and Dr. AI reasoning.

Key values:

| Field | Value |
| --- | --- |
| Height | 162.5 cm |
| Weight | 77.9 kg |
| BMI | 29.5 kg/m2 |
| SBP / DBP | 188 / 116 mmHg |
| Glucose | 4.46 mmol/L |
| HbA1c | 5.9% |
| Total Cholesterol | 4.39 mmol/L |
| Triglycerides | 1.62 mmol/L |
| HDL | 1.62 mmol/L |
| Creatinine | 61.9 umol/L |
| eGFR | 148.5 mL/min/1.73m2 |
| ALT | 59 U/L |
| Smoking | Never smoker |

Recommended demo role:

`Primary metabolic syndrome / diabetes management patient`

## Recommended Patient 2: Cardiovascular And Heart Failure Demo

Patient ID: `066c0f3d-90bb-4082-99ec-f307c4759f50`

Identity:

- Name: Floyd420 Conroy74
- Age: 63
- Gender: Male
- Status: alive
- City: Uxbridge

Why this patient is useful:

- Distinct cardiovascular storyline: chronic congestive heart failure plus long-term hypertension.
- Also has prediabetes, hyperlipidemia, obesity history, and mild kidney-function signal.
- Medication history supports a good pharmacy/Dr. AI explanation: furosemide, metoprolol, hydrochlorothiazide, simvastatin.
- Clinical fields are complete: 18 target fields found.
- Suitable for explaining how clinical risk, cardiac history, renal function, and medication safety are fused.

Key values:

| Field | Value |
| --- | --- |
| Height | 172.9 cm |
| Weight | 84.0 kg |
| BMI | 28.1 kg/m2 |
| SBP / DBP | 133 / 82 mmHg |
| Glucose | 4.74 mmol/L |
| HbA1c | 6.4% |
| Total Cholesterol | 4.27 mmol/L |
| Triglycerides | 1.62 mmol/L |
| LDL | 3.18 mmol/L |
| Creatinine | 79.6 umol/L |
| eGFR | 67.8 mL/min |
| ALT | 59.7 U/L |
| Smoking | Never smoker |

Recommended demo role:

`Cardiovascular / heart failure multimodal risk patient`

## Recommended Patient 3: Younger Multi-System Risk Demo

Patient ID: `4a52ea9c-d410-4b78-a4da-6053e2ed0787`

Identity:

- Name: Aundrea980 Mertz280
- Age: 45
- Gender: Female
- Status: alive
- City: Waltham

Why this patient is useful:

- Younger and more relatable than many high-risk Synthea samples.
- Has hypertension, prediabetes, hyperlipidemia, pulmonary emphysema, and former smoking status.
- Medication history includes antihypertensive combination therapy, simvastatin, and inhaled fluticasone/salmeterol.
- Clinical fields are complete: 18 target fields found.
- Good for showing that the platform is not only for elderly patients; it can explain cardiometabolic and respiratory risk together.

Key values:

| Field | Value |
| --- | --- |
| Height | 155.7 cm |
| Weight | 68.5 kg |
| BMI | 28.2 kg/m2 |
| SBP / DBP | 148 / 110 mmHg |
| Glucose | 3.92 mmol/L |
| HbA1c | 6.1% |
| Total Cholesterol | 5.16 mmol/L |
| Triglycerides | 1.38 mmol/L |
| LDL | 2.96 mmol/L |
| Creatinine | 70.7 umol/L |
| eGFR | 71.9 mL/min |
| ALT | 54.7 U/L |
| Smoking | Former smoker |

Recommended demo role:

`Younger cardiometabolic + respiratory risk patient`

## Final Recommendation

Use `8505e011-20cb-4bc5-8a66-5900111fb04b` as the main defense demo patient.

Keep `066c0f3d-90bb-4082-99ec-f307c4759f50` and `4a52ea9c-d410-4b78-a4da-6053e2ed0787` as alternate demo patients:

- `066c0f3d...` is best when you want to demonstrate cardiovascular risk, heart failure context, and medication reasoning.
- `4a52ea9c...` is best when you want to demonstrate a younger patient, smoking/respiratory context, and multi-system risk.

## Data Gaps To Fill Later

These Synthea patients are strong for clinical/EHR demonstration, but still need supplements for the full platform story:

- lifestyle fields such as sleep hours, diet pattern, alcohol, exercise;
- waist circumference;
- genetic data;
- optional Chinese-localized display names if needed for the defense script.

These should be filled in Task 3 or Task 4 through NHANES-style lifestyle supplementation and the existing demo genetic file.
