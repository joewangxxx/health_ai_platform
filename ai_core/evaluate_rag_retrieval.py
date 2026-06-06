"""Evaluate RAG retrieval with 100 synthetic medical questions.

The runtime RAG service depends on optional LangChain/embedding packages. This
script records runtime availability first, then evaluates an offline lexical
retrieval baseline over the existing Chroma SQLite document store so the
knowledge-base coverage can still be measured reproducibly.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.config import PROJECT_ROOT
from backend.services.rag_service import RAG_DEPENDENCIES_AVAILABLE, rag_service


DEFAULT_OUTPUT_DIR = Path(PROJECT_ROOT) / "docs" / "evaluation"
DEFAULT_VECTOR_DB = Path(PROJECT_ROOT) / "backend" / "rag" / "vector_store" / "chroma.sqlite3"

SOURCE_SPECS = [
    {
        "topic": "gout",
        "source": "成人高尿酸血症与痛风食养指南_2024.pdf",
        "keywords": ["高尿酸", "痛风", "嘌呤", "饮水", "果糖", "酒", "食养"],
        "questions": [
            "高尿酸血症患者为什么要限制高嘌呤食物？",
            "痛风急性发作期饮食上应该注意什么？",
            "高尿酸血症人群每天饮水有什么建议？",
            "痛风患者为什么需要限制含糖饮料和果糖摄入？",
            "无症状高尿酸血症和痛风间歇期怎么安排饮食？",
            "痛风患者可以喝酒吗，指南里如何解释？",
            "高尿酸血症患者选择肉类和海鲜时有什么原则？",
            "痛风人群食养方和食物选择应关注哪些方面？",
            "尿酸偏高但没有症状时是否还需要饮食干预？",
            "痛风慢性期如何做到吃动平衡和体重管理？",
            "高尿酸血症患者为什么要控制动物内脏和浓肉汤？",
            "痛风患者摄入奶类和蔬菜有什么建议？",
        ],
    },
    {
        "topic": "obesity",
        "source": "肥胖症诊疗指南_2024.pdf",
        "keywords": ["肥胖", "BMI", "腰围", "减重", "能量", "生活方式", "诊疗"],
        "questions": [
            "成人肥胖症通常如何根据 BMI 和腰围判断？",
            "肥胖症诊疗中生活方式干预包括哪些重点？",
            "减重治疗为什么要强调长期体重管理？",
            "肥胖相关代谢风险评估需要关注哪些指标？",
            "肥胖患者饮食控制应如何考虑能量摄入？",
            "肥胖症管理中运动干预有什么作用？",
            "中心性肥胖为什么需要关注腰围？",
            "肥胖症诊疗指南如何看待多学科综合管理？",
            "减重过程中为什么不建议极端节食？",
            "肥胖伴高血压或糖代谢异常时应如何综合评估？",
            "肥胖患者随访时需要记录哪些变化？",
        ],
    },
    {
        "topic": "ckd",
        "source": "慢性肾脏病早期筛查_诊断及防治指南_2022.pdf",
        "keywords": ["慢性肾脏病", "CKD", "eGFR", "尿白蛋白", "筛查", "诊断", "防治"],
        "questions": [
            "慢性肾脏病早期筛查为什么要同时看 eGFR 和尿白蛋白？",
            "CKD 高风险人群包括哪些人？",
            "糖尿病患者为什么需要定期筛查肾功能？",
            "尿白蛋白肌酐比异常提示什么风险？",
            "慢性肾脏病防治中血压控制有什么意义？",
            "eGFR 下降时为什么要评估肾脏损伤证据？",
            "CKD 早期管理应关注哪些生活方式因素？",
            "慢性肾脏病患者何时需要进一步转诊？",
            "肾功能筛查结果异常时为什么要复查确认？",
            "CKD 患者用药安全为什么需要关注肾功能？",
            "慢性肾脏病防治指南对高危人群筛查频率有什么启示？",
        ],
    },
    {
        "topic": "fatty_liver",
        "source": "脂肪性肝病诊疗规范化的专家建_2019.pdf",
        "keywords": ["脂肪性肝病", "脂肪肝", "肝酶", "ALT", "生活方式", "体重", "代谢"],
        "questions": [
            "脂肪性肝病为什么常和肥胖及代谢异常相关？",
            "脂肪肝患者为什么需要关注 ALT 和肝酶变化？",
            "脂肪性肝病管理中体重控制有什么作用？",
            "脂肪肝诊疗为什么强调生活方式干预？",
            "脂肪性肝病患者饮食上应注意哪些原则？",
            "代谢综合征人群为什么要筛查脂肪肝？",
            "脂肪肝患者运动干预的目标是什么？",
            "肝酶异常但症状不明显时为什么仍需随访？",
            "脂肪性肝病规范化诊疗需要评估哪些风险？",
            "脂肪肝和饮酒因素应如何区分评估？",
            "脂肪性肝病患者为什么要管理血脂和血糖？",
        ],
    },
    {
        "topic": "diabetes",
        "source": "中国2型糖尿病防治指_2020.pdf",
        "keywords": ["2型糖尿病", "HbA1c", "血糖", "诊断", "生活方式", "并发症", "筛查"],
        "questions": [
            "2型糖尿病诊断为什么要关注空腹血糖和 HbA1c？",
            "糖尿病前期人群如何进行生活方式干预？",
            "2型糖尿病患者为什么需要监测并发症风险？",
            "血糖控制目标制定时应考虑哪些个体因素？",
            "糖尿病患者饮食管理的核心原则是什么？",
            "2型糖尿病患者运动治疗有哪些注意点？",
            "HbA1c 在糖尿病长期管理中有什么意义？",
            "糖尿病高危人群筛查应关注哪些线索？",
            "2型糖尿病患者为什么要同时管理血压和血脂？",
            "糖尿病患者低血糖风险评估为什么重要？",
            "糖尿病慢病管理中随访和教育有什么价值？",
        ],
    },
    {
        "topic": "hypertension",
        "source": "中国高血压防治指南_2024.pdf",
        "keywords": ["高血压", "血压", "收缩压", "舒张压", "限盐", "降压", "心血管"],
        "questions": [
            "高血压诊断为什么需要规范测量血压？",
            "收缩压和舒张压升高分别提示什么风险？",
            "高血压患者为什么要限制盐摄入？",
            "家庭血压监测在高血压管理中有什么作用？",
            "高血压患者生活方式干预包括哪些内容？",
            "降压目标为什么需要结合心血管风险分层？",
            "高血压合并糖尿病时管理上要注意什么？",
            "高血压患者为什么要控制体重和增加运动？",
            "血压波动较大时为什么需要持续随访？",
            "高血压防治中戒烟限酒有什么意义？",
            "老年高血压患者制定目标时为什么要个体化？",
        ],
    },
    {
        "topic": "dietary_guideline",
        "source": "中国居民膳食指南_2022.pdf",
        "keywords": ["膳食指南", "食物多样", "谷类", "蔬菜", "水果", "奶类", "平衡膳食"],
        "questions": [
            "中国居民膳食指南为什么强调食物多样？",
            "平衡膳食宝塔对日常饮食有什么参考价值？",
            "成年人每天摄入蔬菜水果有什么建议？",
            "为什么建议适量摄入奶类和大豆制品？",
            "膳食指南如何看待全谷物和杂豆摄入？",
            "控制油盐糖摄入对慢病预防有什么意义？",
            "普通成年人如何理解吃动平衡？",
            "为什么要培养清淡饮食和规律进餐习惯？",
            "膳食指南对水和饮料选择有什么提示？",
            "家庭健康饮食为什么要关注合理烹调？",
            "居民膳食指南如何支持慢病风险管理？",
        ],
    },
    {
        "topic": "physical_activity",
        "source": "中国人群身体活动指南_2021.pdf",
        "keywords": ["身体活动", "运动", "久坐", "有氧", "肌肉力量", "活动指南", "健康"],
        "questions": [
            "成年人每周身体活动量应该如何安排？",
            "久坐行为为什么会增加健康风险？",
            "有氧运动和肌肉力量训练各有什么作用？",
            "慢病风险人群开始运动前应注意什么？",
            "身体活动指南为什么强调循序渐进？",
            "老年人进行身体活动时应关注哪些安全问题？",
            "儿童青少年身体活动建议与成年人有什么不同？",
            "办公室人群如何减少久坐带来的风险？",
            "运动干预为什么有助于体重和血糖管理？",
            "身体活动不足和心血管风险有什么关系？",
            "如何把日常生活活动纳入健康管理计划？",
        ],
    },
    {
        "topic": "lipid",
        "source": "中国血脂管理指南_2023.pdf",
        "keywords": ["血脂", "LDL", "HDL", "甘油三酯", "胆固醇", "动脉粥样硬化", "ASCVD"],
        "questions": [
            "血脂管理为什么特别关注 LDL-C 水平？",
            "甘油三酯升高时需要评估哪些生活方式因素？",
            "HDL-C 偏低对心血管风险有什么提示？",
            "血脂异常患者为什么要进行 ASCVD 风险评估？",
            "总胆固醇和低密度脂蛋白有什么区别？",
            "血脂管理中饮食干预应关注哪些方面？",
            "血脂异常合并糖尿病时为什么风险更高？",
            "动脉粥样硬化性心血管病预防与血脂有什么关系？",
            "血脂复查和随访为什么重要？",
            "高危人群血脂控制目标为什么更严格？",
            "血脂管理指南如何看待综合生活方式干预？",
        ],
    },
]


@dataclass(frozen=True)
class Chunk:
    chunk_id: int
    source: str
    page: int | None
    text: str


def normalize_source(value: Any) -> str:
    return os.path.basename(str(value or "")).replace("\\", "/").split("/")[-1]


def load_index_chunks(vector_db: Path) -> list[Chunk]:
    con = sqlite3.connect(vector_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT
            d.id AS chunk_id,
            d.c0 AS text,
            source_meta.string_value AS source,
            page_meta.int_value AS page
        FROM embedding_fulltext_search_content d
        LEFT JOIN embedding_metadata source_meta
          ON source_meta.id = d.id AND source_meta.key = 'source'
        LEFT JOIN embedding_metadata page_meta
          ON page_meta.id = d.id AND page_meta.key = 'page'
        WHERE d.c0 IS NOT NULL AND length(d.c0) > 0
        """
    ).fetchall()
    con.close()
    return [
        Chunk(
            chunk_id=int(row["chunk_id"]),
            source=normalize_source(row["source"]),
            page=int(row["page"]) if row["page"] is not None else None,
            text=str(row["text"] or ""),
        )
        for row in rows
    ]


def generate_questions() -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    counter = 1
    for spec in SOURCE_SPECS:
        for question in spec["questions"]:
            questions.append(
                {
                    "question_id": f"rag_q_{counter:03d}",
                    "question": question,
                    "topic": spec["topic"],
                    "expected_source": spec["source"],
                    "expected_keywords": spec["keywords"],
                }
            )
            counter += 1
    return questions


def tokenize(text: str) -> list[str]:
    lower = text.lower()
    latin = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+\-.]*", lower)
    chinese_terms = [
        term
        for term in [
            "高尿酸",
            "痛风",
            "嘌呤",
            "饮水",
            "果糖",
            "肥胖",
            "腰围",
            "减重",
            "慢性肾脏病",
            "尿白蛋白",
            "筛查",
            "脂肪性肝病",
            "脂肪肝",
            "肝酶",
            "糖尿病",
            "血糖",
            "诊断",
            "并发症",
            "高血压",
            "收缩压",
            "舒张压",
            "限盐",
            "膳食指南",
            "食物多样",
            "蔬菜",
            "水果",
            "奶类",
            "身体活动",
            "运动",
            "久坐",
            "有氧",
            "血脂",
            "胆固醇",
            "甘油三酯",
            "动脉粥样硬化",
            "生活方式",
            "风险",
            "管理",
            "随访",
        ]
        if term in text
    ]
    return latin + chinese_terms


def build_document_frequencies(chunks: list[Chunk]) -> Counter[str]:
    dfs: Counter[str] = Counter()
    for chunk in chunks:
        dfs.update(set(tokenize(chunk.text)))
    return dfs


def lexical_search(query: str, chunks: list[Chunk], dfs: Counter[str], *, k: int) -> list[dict[str, Any]]:
    query_terms = tokenize(query)
    if not query_terms:
        query_terms = [query]

    n_docs = max(len(chunks), 1)
    scored: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        text_lower = chunk.text.lower()
        score = 0.0
        for term in query_terms:
            tf = text_lower.count(term.lower())
            if tf <= 0:
                continue
            idf = math.log((n_docs + 1) / (dfs.get(term, 0) + 1)) + 1.0
            score += (1.0 + math.log(tf)) * idf
        source_lower = chunk.source.lower()
        for term in query_terms:
            if term.lower() in source_lower:
                score += 0.75
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1].source, item[1].chunk_id))
    return [
        {
            "rank": rank,
            "score": round(score, 6),
            "chunk_id": chunk.chunk_id,
            "source": chunk.source,
            "page": chunk.page,
            "snippet": chunk.text[:180].replace("\n", " "),
        }
        for rank, (score, chunk) in enumerate(scored[:k], start=1)
    ]


def keyword_coverage(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    hits = sum(1 for keyword in keywords if keyword.lower() in text.lower())
    return hits / len(keywords)


def source_rank(results: list[dict[str, Any]], expected_source: str) -> int | None:
    expected = normalize_source(expected_source)
    for result in results:
        if normalize_source(result["source"]) == expected:
            return int(result["rank"])
    return None


def probe_runtime_rag_status() -> dict[str, Any]:
    result = rag_service.search_context_with_quality("2型糖尿病 HbA1c 生活方式干预", k=3)
    quality = result.get("rag_quality_summary") or {}
    return {
        "dependencies_available": bool(RAG_DEPENDENCIES_AVAILABLE),
        "retrieval_status": quality.get("retrieval_status"),
        "hit_count": quality.get("hit_count", 0),
        "chunk_quality": quality.get("chunk_quality"),
        "context_chars": len(result.get("context") or ""),
    }


def evaluate(questions: list[dict[str, Any]], chunks: list[Chunk], *, k: int) -> dict[str, Any]:
    dfs = build_document_frequencies(chunks)
    rows: list[dict[str, Any]] = []
    for item in questions:
        results = lexical_search(item["question"], chunks, dfs, k=k)
        rank = source_rank(results, item["expected_source"])
        joined_text = " ".join(result["snippet"] for result in results[:5])
        coverage = keyword_coverage(joined_text, item["expected_keywords"])
        rows.append(
            {
                "question_id": item["question_id"],
                "topic": item["topic"],
                "question": item["question"],
                "expected_source": item["expected_source"],
                "top1_source": results[0]["source"] if results else "",
                "source_rank": rank or "",
                "hit_at_1": bool(rank and rank <= 1),
                "hit_at_3": bool(rank and rank <= 3),
                "hit_at_5": bool(rank and rank <= 5),
                "hit_at_10": bool(rank and rank <= 10),
                "reciprocal_rank": (1 / rank) if rank else 0.0,
                "keyword_coverage_top5": coverage,
                "top5_keyword_pass": coverage >= 0.5,
                "top_results_json": json.dumps(results[:5], ensure_ascii=False),
            }
        )
    return {"rows": rows, "summary": summarize_rows(rows, chunks)}


def summarize_rows(rows: list[dict[str, Any]], chunks: list[Chunk]) -> dict[str, Any]:
    count = len(rows)
    topic_rows: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        topic_rows.setdefault(row["topic"], []).append(row)

    indexed_sources = {chunk.source for chunk in chunks}
    expected_sources = {spec["source"] for spec in SOURCE_SPECS}
    indexed_rows = [
        row for row in rows if normalize_source(row["expected_source"]) in indexed_sources
    ]
    summary = {
        "question_count": count,
        "chunk_count": len(chunks),
        "expected_source_count": len(expected_sources),
        "unique_source_count": len(indexed_sources),
        "missing_expected_sources": sorted(expected_sources - indexed_sources),
        "source_hit_at_1": mean_bool(rows, "hit_at_1"),
        "source_hit_at_3": mean_bool(rows, "hit_at_3"),
        "source_hit_at_5": mean_bool(rows, "hit_at_5"),
        "source_hit_at_10": mean_bool(rows, "hit_at_10"),
        "mrr": sum(float(row["reciprocal_rank"]) for row in rows) / count if count else 0.0,
        "mean_keyword_coverage_top5": sum(float(row["keyword_coverage_top5"]) for row in rows) / count if count else 0.0,
        "top5_keyword_pass_rate": mean_bool(rows, "top5_keyword_pass"),
        "indexed_subset_question_count": len(indexed_rows),
        "indexed_subset_source_hit_at_5": mean_bool(indexed_rows, "hit_at_5"),
        "indexed_subset_mrr": sum(float(row["reciprocal_rank"]) for row in indexed_rows) / len(indexed_rows)
        if indexed_rows
        else 0.0,
        "topic_metrics": [],
    }
    for topic, topic_items in sorted(topic_rows.items()):
        topic_count = len(topic_items)
        summary["topic_metrics"].append(
            {
                "topic": topic,
                "question_count": topic_count,
                "hit_at_1": mean_bool(topic_items, "hit_at_1"),
                "hit_at_3": mean_bool(topic_items, "hit_at_3"),
                "hit_at_5": mean_bool(topic_items, "hit_at_5"),
                "mrr": sum(float(row["reciprocal_rank"]) for row in topic_items) / topic_count if topic_count else 0.0,
                "mean_keyword_coverage_top5": sum(float(row["keyword_coverage_top5"]) for row in topic_items) / topic_count if topic_count else 0.0,
            }
        )
    return summary


def mean_bool(rows: list[dict[str, Any]], key: str) -> float:
    return sum(1 for row in rows if row.get(key)) / len(rows) if rows else 0.0


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_markdown_report(
    *,
    metadata: dict[str, Any],
    runtime_status: dict[str, Any],
    summary: dict[str, Any],
    output_paths: dict[str, Path],
) -> str:
    runtime_ok = runtime_status.get("retrieval_status") == "ok"
    missing_sources = summary["missing_expected_sources"]
    if runtime_ok:
        runtime_boundary = (
            "The runtime RAG service is recorded exactly as observed. In this environment the optional "
            "LangChain/embedding packages are available and live vector retrieval returned `ok`."
        )
        resume_boundary = (
            "Live vector retrieval was available during this run; the reported Hit@k/MRR values still describe "
            "retrieval-source matching, not final LLM answer correctness."
        )
        blocker_line = "- Blockers: none for live vector RAG startup and expected-source index coverage in this run."
    else:
        runtime_boundary = (
            "The runtime RAG service is recorded exactly as observed. In this environment the optional "
            "LangChain/embedding packages are unavailable, so live vector retrieval returns `unavailable`."
        )
        resume_boundary = (
            "Do not describe this as live vector retrieval quality until the embedding runtime is available and rerun."
        )
        blocker_line = (
            "- Blockers: live vector RAG retrieval is unavailable in the current Python environment because optional "
            "RAG dependencies are missing."
        )

    if missing_sources:
        source_boundary = (
            "Missing expected sources are counted as misses in all-question metrics: "
            f"`{', '.join(missing_sources)}`."
        )
    else:
        source_boundary = "All expected sources are present in the current Chroma index."

    if runtime_ok and not missing_sources:
        suggested_wording = (
            f"- Suggested: `Built a 100-question medical RAG retrieval benchmark over {summary['chunk_count']} "
            f"Chroma chunks from {summary['unique_source_count']} indexed guideline sources; live vector retrieval "
            f"returned ok, offline source Hit@5 reached {fmt(summary['source_hit_at_5'])}, and MRR reached "
            f"{fmt(summary['mrr'])}.`"
        )
    else:
        suggested_wording = (
            f"- Suggested: `Built a 100-question medical RAG retrieval benchmark; offline source Hit@5 reached "
            f"{fmt(summary['source_hit_at_5'])}, MRR reached {fmt(summary['mrr'])}, and remaining runtime/index "
            f"blockers were explicitly documented.`"
        )
    avoid_wording = (
        "- Avoid: `LLM medical-answer correctness` or `clinical-grade RAG`, unless answer-level human/expert "
        "annotation is added."
    )

    topic_lines = [
        "| Topic | Questions | Hit@1 | Hit@3 | Hit@5 | MRR | Keyword Coverage@5 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for topic in summary["topic_metrics"]:
        topic_lines.append(
            f"| {topic['topic']} | {topic['question_count']} | {fmt(topic['hit_at_1'])} | "
            f"{fmt(topic['hit_at_3'])} | {fmt(topic['hit_at_5'])} | {fmt(topic['mrr'])} | "
            f"{fmt(topic['mean_keyword_coverage_top5'])} |"
        )

    return "\n".join(
        [
            "# RAG Retrieval Evaluation Report",
            "",
            f"- Generated at: {metadata['generated_at']}",
            f"- Question count: `{summary['question_count']}`",
            f"- Indexed chunks read from Chroma SQLite: `{summary['chunk_count']}`",
            f"- Expected sources: `{summary['expected_source_count']}`",
            f"- Unique indexed sources: `{summary['unique_source_count']}`",
            f"- Missing expected sources: `{', '.join(summary['missing_expected_sources']) if summary['missing_expected_sources'] else 'none'}`",
            f"- Evaluation mode: `{metadata['evaluation_mode']}`",
            "",
            "## Runtime RAG Service Probe",
            "",
            f"- LangChain/embedding dependencies available: `{runtime_status['dependencies_available']}`",
            f"- Runtime retrieval status: `{runtime_status['retrieval_status']}`",
            f"- Runtime hit count: `{runtime_status['hit_count']}`",
            f"- Runtime chunk quality: `{runtime_status['chunk_quality']}`",
            "",
            "## Offline Retrieval Metrics",
            "",
            f"- Source Hit@1: `{fmt(summary['source_hit_at_1'])}`",
            f"- Source Hit@3: `{fmt(summary['source_hit_at_3'])}`",
            f"- Source Hit@5: `{fmt(summary['source_hit_at_5'])}`",
            f"- Source Hit@10: `{fmt(summary['source_hit_at_10'])}`",
            f"- MRR: `{fmt(summary['mrr'])}`",
            f"- Indexed-source subset questions: `{summary['indexed_subset_question_count']}`",
            f"- Indexed-source subset Hit@5: `{fmt(summary['indexed_subset_source_hit_at_5'])}`",
            f"- Indexed-source subset MRR: `{fmt(summary['indexed_subset_mrr'])}`",
            f"- Mean keyword coverage@5: `{fmt(summary['mean_keyword_coverage_top5'])}`",
            f"- Top5 keyword pass rate: `{fmt(summary['top5_keyword_pass_rate'])}`",
            "",
            "## Topic Breakdown",
            "",
            *topic_lines,
            "",
            "## Interpretation Boundary",
            "",
            runtime_boundary,
            "The offline metrics are a reproducible lexical retrieval baseline over the existing Chroma SQLite text/index content. They measure knowledge-base source coverage for 100 synthetic medical questions, not live embedding semantic retrieval quality.",
            source_boundary,
            resume_boundary,
            "",
            "## Output Files",
            "",
            f"- Question set: `{output_paths['questions']}`",
            f"- Per-query metrics: `{output_paths['per_query']}`",
            f"- Summary JSON: `{output_paths['summary_json']}`",
            f"- Markdown report: `{output_paths['report']}`",
            "",
            "## Suggested Resume Wording",
            "",
            suggested_wording,
            avoid_wording,
            "",
            "## Phase Handoff",
            "",
            "- Current stage: Phase 4 - RAG retrieval evaluation",
            "- Updated artifacts: `ai_core/evaluate_rag_retrieval.py`, `docs/evaluation/rag-questions.json`, `docs/evaluation/rag-retrieval-metrics.csv`, `docs/evaluation/rag-retrieval-summary.json`, `docs/evaluation/rag-evaluation-report.md`",
            blocker_line,
            "- Next stage: Phase 5 - Agent behavior and safety evaluation.",
        ]
    ) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector-db", type=Path, default=DEFAULT_VECTOR_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    questions = generate_questions()
    chunks = load_index_chunks(args.vector_db)
    runtime_status = probe_runtime_rag_status()
    evaluation = evaluate(questions, chunks, k=args.top_k)

    questions_path = args.output_dir / "rag-questions.json"
    per_query_path = args.output_dir / "rag-retrieval-metrics.csv"
    summary_path = args.output_dir / "rag-retrieval-summary.json"
    report_path = args.output_dir / "rag-evaluation-report.md"

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_mode": "runtime_probe_plus_chroma_sqlite_lexical_baseline",
        "vector_db": str(args.vector_db),
        "top_k": args.top_k,
    }

    questions_path.write_text(
        json.dumps(
            {
                "schema_version": "rag_question_set.v1",
                "generated_at": metadata["generated_at"],
                "question_count": len(questions),
                "questions": questions,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_csv(per_query_path, evaluation["rows"])
    summary_payload = {
        "metadata": metadata,
        "runtime_rag_service": runtime_status,
        "summary": evaluation["summary"],
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(
        make_markdown_report(
            metadata=metadata,
            runtime_status=runtime_status,
            summary=evaluation["summary"],
            output_paths={
                "questions": questions_path,
                "per_query": per_query_path,
                "summary_json": summary_path,
                "report": report_path,
            },
        ),
        encoding="utf-8",
    )

    print(f"Generated/evaluated {len(questions)} RAG questions.")
    print(f"Runtime RAG status: {runtime_status['retrieval_status']}")
    print(f"Offline source Hit@5: {fmt(evaluation['summary']['source_hit_at_5'])}")
    print(f"Offline MRR: {fmt(evaluation['summary']['mrr'])}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
