import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = new URL('..', import.meta.url)
const kbDir = new URL('../data_warehouse/processed_data/knowledge_base/', import.meta.url)
const outDir = new URL('../data/demo/', import.meta.url)
const SNP_COUNT = Number(process.argv[2] || 50000)

const patients = [
  {
    id: 'synthea_8505e011',
    role: 'primary_metabolic_syndrome_diabetes_management',
    title: 'Metabolic and diabetes high-risk demo patient',
    seed: 8505011,
    emphasis: {
      T2D: 'high',
      Obesity: 'high',
      Glucose: 'high',
      SystolicBP: 'high',
      HighCholesterol: 'high',
      InsulinResist: 'high',
      Coronary: 'medium',
      CKD: 'medium',
      ALT: 'medium',
    },
  },
  {
    id: 'synthea_066c0f3d',
    role: 'cardiovascular_heart_failure_multimodal_risk',
    title: 'Cardiovascular and heart-failure demo patient',
    seed: 6603,
    emphasis: {
      SystolicBP: 'high',
      Coronary: 'high',
      HeartFailure: 'high',
      HighCholesterol: 'high',
      Stroke: 'medium',
      CKD: 'medium',
      T2D: 'medium',
      Obesity: 'medium',
    },
  },
  {
    id: 'synthea_4a52ea9c',
    role: 'younger_cardiometabolic_respiratory_risk',
    title: 'Younger cardiometabolic and respiratory demo patient',
    seed: 4529,
    emphasis: {
      Asthma: 'medium',
      'C-ReactiveProtein': 'medium',
      Obesity: 'medium',
      Glucose: 'medium',
      T2D: 'low',
      SystolicBP: 'low',
      HighCholesterol: 'low',
      Coronary: 'low',
    },
  },
]

const diseasePriority = [
  'T2D',
  'Obesity',
  'Glucose',
  'SystolicBP',
  'HighCholesterol',
  'InsulinResist',
  'Coronary',
  'HeartFailure',
  'Stroke',
  'CKD',
  'Asthma',
  'C-ReactiveProtein',
  'ALT',
]

const alleleAlphabet = ['A', 'C', 'G', 'T']

function mulberry32(seed) {
  let state = seed >>> 0
  return function next() {
    state += 0x6d2b79f5
    let t = state
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function hashString(input) {
  let hash = 2166136261
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

function parseCsvLine(line) {
  const values = []
  let value = ''
  let quoted = false
  for (const char of line) {
    if (char === '"') {
      quoted = !quoted
    } else if (char === ',' && !quoted) {
      values.push(value)
      value = ''
    } else {
      value += char
    }
  }
  values.push(value)
  return values
}

function parseVariantLocation(rsid) {
  const colonMatch = rsid.match(/^(\d+|X|Y|MT):(\d+)/i)
  if (colonMatch) {
    return { chrom: colonMatch[1].toUpperCase(), pos: Number(colonMatch[2]) }
  }
  const hash = hashString(rsid)
  return {
    chrom: String((hash % 22) + 1),
    pos: 100000 + (hash % 240000000),
  }
}

function allelesFromRsid(rsid, riskAllele) {
  const risk = String(riskAllele || '').toUpperCase()
  const candidates = new Set()
  const colonAlleles = rsid.match(/[:_](A|C|G|T)[:/_](A|C|G|T)$/i)
  if (colonAlleles) {
    candidates.add(colonAlleles[1].toUpperCase())
    candidates.add(colonAlleles[2].toUpperCase())
  }
  if (alleleAlphabet.includes(risk)) candidates.add(risk)
  for (const allele of alleleAlphabet) {
    if (allele !== risk) candidates.add(allele)
    if (candidates.size >= 2) break
  }
  return Array.from(candidates).slice(0, 2)
}

function genotypeForVariant(variant, level, rng) {
  const [a, b] = allelesFromRsid(variant.rsid, variant.riskAllele)
  const risk = String(variant.riskAllele || a).toUpperCase()
  const other = a === risk ? b : a
  const positiveWeight = variant.weight >= 0
  const roll = rng()
  if (roll < 0.002) return '--'

  const doseRoll = (thresholds) => {
    if (roll < thresholds[2]) return 2
    if (roll < thresholds[1]) return 1
    return 0
  }
  const dose = (() => {
    if (positiveWeight) {
      if (level === 'high') return doseRoll({ 2: 0.62, 1: 0.92 })
      if (level === 'medium') return doseRoll({ 2: 0.22, 1: 0.66 })
      if (level === 'low') return doseRoll({ 2: 0.02, 1: 0.14 })
      return doseRoll({ 2: 0.015, 1: 0.12 })
    }
    if (level === 'high') return doseRoll({ 2: 0.01, 1: 0.06 })
    if (level === 'medium') return doseRoll({ 2: 0.08, 1: 0.36 })
    if (level === 'low') return doseRoll({ 2: 0.68, 1: 0.92 })
    return doseRoll({ 2: 0.06, 1: 0.24 })
  })()

  if (dose === 2) return `${risk}${risk}`
  if (dose === 1) return `${risk}${other}`
  return `${other}${other}`
}

function readGwasVariants() {
  const variants = []
  for (const disease of diseasePriority) {
    const file = new URL(`GWAS_${disease}_weights.csv`, kbDir)
    let text = ''
    try {
      text = readFileSync(file, 'utf8')
    } catch {
      continue
    }
    const rows = text.trim().split(/\r?\n/)
    const header = parseCsvLine(rows.shift() || '')
    const idx = Object.fromEntries(header.map((name, index) => [name, index]))
    for (const row of rows) {
      const parts = parseCsvLine(row)
      const rsid = parts[idx.rsid]
      const riskAllele = parts[idx.risk_allele]
      const weight = Number(parts[idx.weight])
      const pValue = Number(parts[idx.p_value])
      if (!rsid || !riskAllele || !Number.isFinite(weight)) continue
      const { chrom, pos } = parseVariantLocation(rsid)
      variants.push({
        rsid,
        chrom,
        pos,
        disease,
        riskAllele: riskAllele.toUpperCase(),
        weight,
        pValue: Number.isFinite(pValue) ? pValue : null,
        priority: Math.abs(weight) * (Number.isFinite(pValue) && pValue > 0 ? -Math.log10(pValue) : 320),
      })
    }
  }
  variants.sort((a, b) => b.priority - a.priority)
  const byRsid = new Map()
  for (const variant of variants) {
    if (!byRsid.has(variant.rsid)) byRsid.set(variant.rsid, variant)
  }
  return Array.from(byRsid.values())
}

function makeBackgroundVariant(index, rng, used) {
  let rsid = ''
  do {
    rsid = `rs${100000000 + Math.floor(rng() * 899999999)}`
  } while (used.has(rsid))
  const chrom = String(1 + Math.floor(rng() * 22))
  const pos = 100000 + Math.floor(rng() * 240000000)
  const a = alleleAlphabet[Math.floor(rng() * alleleAlphabet.length)]
  let b = alleleAlphabet[Math.floor(rng() * alleleAlphabet.length)]
  if (b === a) b = alleleAlphabet[(alleleAlphabet.indexOf(a) + 1 + (index % 3)) % alleleAlphabet.length]
  const roll = rng()
  const genotype = roll < 0.003 ? '--' : roll < 0.48 ? `${a}${a}` : roll < 0.88 ? `${a}${b}` : `${b}${b}`
  return { rsid, chrom, pos, genotype }
}

function selectPatientVariants(allVariants, patient) {
  const selected = []
  const seen = new Set()
  const perDiseaseTarget = Math.max(550, Math.floor(SNP_COUNT * 0.055))
  for (const disease of diseasePriority) {
    const variants = allVariants.filter((variant) => variant.disease === disease)
    const level = patient.emphasis[disease] || 'neutral'
    const diseaseTake = level === 'high'
      ? perDiseaseTarget
      : level === 'medium'
        ? Math.floor(perDiseaseTarget * 0.75)
        : level === 'low'
          ? Math.floor(perDiseaseTarget * 0.45)
          : Math.floor(perDiseaseTarget * 0.30)
    for (const variant of variants.slice(0, diseaseTake)) {
      if (seen.has(variant.rsid)) continue
      selected.push(variant)
      seen.add(variant.rsid)
    }
  }
  for (const variant of allVariants) {
    if (selected.length >= Math.floor(SNP_COUNT * 0.72)) break
    if (seen.has(variant.rsid)) continue
    selected.push(variant)
    seen.add(variant.rsid)
  }
  return selected
}

function writePatientFile(patient, allVariants) {
  const rng = mulberry32(patient.seed)
  const selected = selectPatientVariants(allVariants, patient)
  const used = new Set(selected.map((variant) => variant.rsid))
  const lines = [
    `# ${patient.id} synthetic 23andMe-style genotype file`,
    '# Generated for HealthAI Platform defense/demo workflows.',
    '# This is not a real person, not a real Synthea genome, and not clinical-grade evidence.',
    '# Public/local GWAS variant identifiers are used for plausibility; individual genotypes are synthetic.',
    '# Format: rsid<TAB>chromosome<TAB>position<TAB>genotype',
    '# Bound clinical CSV: data/demo/platform_demo_profile_' + patient.id + '.csv',
    '# Bound behavior scenario: data/demo/behavior_day_scenarios.json',
    `# demo_patient_id: ${patient.id}`,
    `# demo_role: ${patient.role}`,
    '',
  ]
  const diseaseCounts = {}
  for (const variant of selected) {
    const level = patient.emphasis[variant.disease] || 'neutral'
    const genotype = genotypeForVariant(variant, level, rng)
    lines.push(`${variant.rsid}\t${variant.chrom}\t${variant.pos}\t${genotype}`)
    diseaseCounts[variant.disease] = (diseaseCounts[variant.disease] || 0) + 1
  }
  let backgroundCount = 0
  for (let i = selected.length; i < SNP_COUNT; i += 1) {
    const variant = makeBackgroundVariant(i, rng, used)
    used.add(variant.rsid)
    backgroundCount += 1
    lines.push(`${variant.rsid}\t${variant.chrom}\t${variant.pos}\t${variant.genotype}`)
  }
  const path = new URL(`../data/demo/demo_gene_${patient.id}.txt`, import.meta.url)
  writeFileSync(path, `${lines.join('\n')}\n`, 'utf8')
  return {
    demo_patient_id: patient.id,
    role: patient.role,
    title: patient.title,
    file: `data/demo/${basename(path.pathname)}`,
    snp_count: SNP_COUNT,
    gwas_weighted_variant_count: selected.length,
    background_variant_count: backgroundCount,
    emphasized_models: patient.emphasis,
    gwas_model_variant_counts: diseaseCounts,
  }
}

mkdirSync(outDir, { recursive: true })
const allVariants = readGwasVariants()
if (!allVariants.length) {
  throw new Error(`No GWAS variants loaded from ${kbDir.pathname}`)
}

const manifest = {
  schema_version: 'demo_gene_files.v1',
  generated_at: new Date().toISOString(),
  data_mode: 'synthetic_demo',
  target_snp_count_per_patient: SNP_COUNT,
  generation_method: 'Local GWAS weight files provide plausible variant identifiers/effect alleles; per-patient genotypes are synthetic and tuned for defense-demo narratives.',
  source_provenance: {
    local_gwas_dir: join(fileURLToPath(ROOT), 'data_warehouse', 'processed_data', 'knowledge_base'),
    public_context: [
      'GWAS Catalog/PGS Catalog style association data, not real personal genomes',
      '23andMe-style four-column raw genotype text format',
    ],
  },
  files: patients.map((patient) => writePatientFile(patient, allVariants)),
}

writeFileSync(new URL('../data/demo/demo_gene_files_manifest.json', import.meta.url), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
console.log(JSON.stringify(manifest, null, 2))
