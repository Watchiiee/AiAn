"""
doc_grade 모드(all_or_nothing vs individual)를 89개 골든셋 전체로 재검증.

test_doc_grade_modes.py(17개 소규모)에서 이상신호가 없었으므로, 이제 전체
파이프라인(_graph.invoke)을 89개 전부에 대해 두 모드로 돌려 recall(정답청크가
graded_docs에 실제로 들어갔는지)·confidence 분포·재시도횟수를 종합 비교한다.

주의: 89개 x 2모드 x (재시도 포함 시 문항당 여러 번의 LLM 호출) 이라 실행에
시간이 오래 걸리고 비용이 크다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.eval_pipeline_doc_grade
"""
import csv
import os
import sys
import importlib
from collections import Counter

sys.path.insert(0, os.getcwd())

DEFAULT_CSVS = ["data/golden_dataset_phase1.csv", "data/golden_dataset_phase2.csv", "data/golden_dataset_bias_probe.csv"]


def _parse_gold_chunks(gold_chunk_id: str) -> list[tuple[str, str]]:
    parts = [p.strip() for p in gold_chunk_id.split(" + ")]
    result = []
    for p in parts:
        segs = [s.strip() for s in p.split(">")]
        result.append((segs[0], segs[-1]))
    return result


def _parse_retrieved_source(source: str) -> tuple[str, str]:
    if " > " in source:
        filename, heading = source.split(" > ", 1)
        return filename.strip(), heading.strip()
    return source.strip(), ""


def load_golden_set() -> list[dict]:
    rows = []
    for path in DEFAULT_CSVS:
        with open(path, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))
    return rows


def run_mode(mode: str, rows: list[dict]) -> list[dict]:
    os.environ["RAG_DOC_GRADE_MODE"] = mode
    import BE.api.pipeline as pipeline
    importlib.reload(pipeline)

    print(f"\n{'='*70}\n모드: {mode} ({len(rows)}개 문항)\n{'='*70}")
    results = []
    for r in rows:
        init = {
            "text": r["question"], "search_query": r["question"], "cls": None, "rule": None,
            "docs": None, "graded_docs": None, "answer": None, "answer_confidence": None,
            "llm_error": None, "route": "", "is_urgent": False, "urgent_reason": None,
            "doc_relevant": False, "rewrite_count": 0, "hallucination_ok": True,
            "answer_ok": True, "regenerate_count": 0,
        }
        result = pipeline._graph.invoke(init)

        graded = result.get("graded_docs") or []
        graded_pairs = [_parse_retrieved_source(d.source) for d in graded]
        gold_pairs = _parse_gold_chunks(r["gold_chunk_id"])
        found = sum(1 for gp in gold_pairs if gp in graded_pairs)
        recall = found / len(gold_pairs) if gold_pairs else 0.0

        conf = result.get("answer_confidence")
        conf_val = conf.value if hasattr(conf, "value") else conf

        row = {
            "id": r["id"], "n_full": len(result.get("docs") or []), "n_graded": len(graded),
            "recall": recall, "rewrite_count": result.get("rewrite_count", 0),
            "regenerate_count": result.get("regenerate_count", 0), "confidence": conf_val,
        }
        results.append(row)
        print(f"[{r['id']}] 전체={row['n_full']} 선택={row['n_graded']} recall={recall:.1f} "
              f"재검색={row['rewrite_count']} 재생성={row['regenerate_count']} conf={conf_val}")
    return results


def _summarize(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "avg_recall": sum(r["recall"] for r in rows) / n,
        "avg_n_graded": sum(r["n_graded"] for r in rows) / n,
        "avg_rewrite": sum(r["rewrite_count"] for r in rows) / n,
        "avg_regenerate": sum(r["regenerate_count"] for r in rows) / n,
        "confidence_dist": dict(Counter(r["confidence"] for r in rows)),
    }


def run():
    rows = load_golden_set()
    print(f"골든셋 총 {len(rows)}개 문항으로 전체 파이프라인 비교 시작 (시간이 오래 걸릴 수 있음)")

    all_results = run_mode("all_or_nothing", rows)
    ind_results = run_mode("individual", rows)

    print("\n" + "=" * 70)
    print("항목별 차이 (recall이 다르거나 confidence가 바뀐 경우만)")
    print("=" * 70)
    for a, i in zip(all_results, ind_results):
        if a["recall"] != i["recall"] or a["confidence"] != i["confidence"]:
            print(f"[{a['id']}] all: recall={a['recall']:.1f} conf={a['confidence']} | "
                  f"ind: recall={i['recall']:.1f} conf={i['confidence']}")

    s_all = _summarize(all_results)
    s_ind = _summarize(ind_results)

    print("\n" + "=" * 70)
    print("전체 요약")
    print("=" * 70)
    print(f"{'':<20}{'all_or_nothing':<20}{'individual':<20}")
    print(f"{'평균 recall':<20}{s_all['avg_recall']:<20.1%}{s_ind['avg_recall']:<20.1%}")
    print(f"{'평균 선택개수':<20}{s_all['avg_n_graded']:<20.1f}{s_ind['avg_n_graded']:<20.1f}")
    print(f"{'평균 재검색횟수':<20}{s_all['avg_rewrite']:<20.2f}{s_ind['avg_rewrite']:<20.2f}")
    print(f"{'평균 재생성횟수':<20}{s_all['avg_regenerate']:<20.2f}{s_ind['avg_regenerate']:<20.2f}")
    print(f"\nconfidence 분포 (all_or_nothing): {s_all['confidence_dist']}")
    print(f"confidence 분포 (individual)    : {s_ind['confidence_dist']}")


if __name__ == "__main__":
    run()