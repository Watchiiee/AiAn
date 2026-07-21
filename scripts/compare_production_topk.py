"""
"실제 서비스 기본값(고정 top_k=3)"과 "동적 top_k(엘보우+min_k)"를 직접 비교하는 스크립트.

eval_golden_set.py는 Hit@1~10 곡선을 그리려고 항상 top_k=10을 요청하기 때문에,
"고정 3개 vs 동적 개수"라는 원래 궁금했던 비교를 할 수 없다(우리 골든셋 정답이
전부 6등 이내라, min_k=6 밑에서는 고정10과 동적이 항상 똑같이 나옴). 이 스크립트는
그 대신 각 방식이 "실제로 몇 개를 반환하는지"와 "그 안에 정답이 있는지"를 직접
비교해서, doc_grade/generate가 실제로 보게 될 노이즈 양의 차이를 드러낸다.

실행 (레포 루트에서, venv 활성화 후. 이 스크립트 자체는 환경변수를 직접 다루므로
RAG_DYNAMIC_TOPK를 미리 설정하지 않아도 된다):
    python3 -m scripts.compare_production_topk
"""
import csv
import os
import sys

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


def load_golden_set(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        with open(path, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))
    return rows


def run():
    rows = load_golden_set(DEFAULT_CSVS)

    from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory

    def _dummy_cls(domain: str) -> Classification:
        return Classification(
            type=InquiryType.GENERAL, key_request="비교용", confidence=1.0,
            domain=Domain(domain), category=BusinessCategory.OTHER, is_relevant=True,
        )

    results = {"fixed3": [], "dynamic": []}

    for mode in ("fixed3", "dynamic"):
        os.environ["RAG_DYNAMIC_TOPK"] = "1" if mode == "dynamic" else "0"
        # retriever 모듈을 이 시점에 다시 불러와야 환경변수가 반영된다(모듈 최상단에서
        # 한 번만 읽는 값이라 캐시된 모듈이면 반영 안 됨 -> 매 모드마다 새로 임포트).
        import importlib
        if "AI.rag.retriever" in sys.modules:
            importlib.reload(sys.modules["AI.rag.retriever"])
        from AI.rag.retriever import retrieve

        print(f"\n=== 모드: {mode} ({'고정 top_k=3' if mode=='fixed3' else '동적(엘보우+min_k)'}) ===")
        for r in rows:
            cls = _dummy_cls(r["gold_domain"])
            # fixed3는 top_k=3 명시. dynamic은 top_k값 자체를 무시하므로 아무거나 넘겨도 됨.
            docs = retrieve(r["question"], cls, top_k=3)
            gold_pairs = _parse_gold_chunks(r["gold_chunk_id"])
            retrieved_pairs = [_parse_retrieved_source(d.source) for d in docs]
            found = sum(1 for gp in gold_pairs if gp in retrieved_pairs)
            recall = found / len(gold_pairs) if gold_pairs else 0.0
            results[mode].append({"id": r["id"], "n_returned": len(docs), "recall": recall, "found": found, "n_gold": len(gold_pairs)})

    print("\n" + "=" * 80)
    print(f"{'id':<8}{'고정3 개수':<10}{'고정3 recall':<14}{'동적 개수':<10}{'동적 recall':<12}")
    print("-" * 80)
    for f3, dy in zip(results["fixed3"], results["dynamic"]):
        mark = ""
        if f3["recall"] != dy["recall"]:
            mark = "  <-- 차이 있음"
        print(f"{f3['id']:<8}{f3['n_returned']:<10}{f3['recall']:<14.2f}{dy['n_returned']:<10}{dy['recall']:<12.2f}{mark}")

    n = len(rows)
    avg_n_fixed = sum(r["n_returned"] for r in results["fixed3"]) / n
    avg_n_dynamic = sum(r["n_returned"] for r in results["dynamic"]) / n
    avg_recall_fixed = sum(r["recall"] for r in results["fixed3"]) / n
    avg_recall_dynamic = sum(r["recall"] for r in results["dynamic"]) / n

    print("\n" + "=" * 80)
    print("요약")
    print("=" * 80)
    print(f"고정 top_k=3   : 평균 반환개수={avg_n_fixed:.1f}, 평균 recall={avg_recall_fixed:.1%}")
    print(f"동적(엘보우+min_k): 평균 반환개수={avg_n_dynamic:.1f}, 평균 recall={avg_recall_dynamic:.1%}")
    print("\n해석: 동적 방식의 recall이 고정3보다 높으면 '더 많이 찾아냄'을 의미하고,")
    print("      평균 반환개수가 3보다 크게 늘었다면 그만큼 generate가 더 많은(어쩌면 불필요한)")
    print("      문서를 보게 된다는 트레이드오프가 있다는 뜻 — 둘을 같이 봐야 함.")


if __name__ == "__main__":
    run()