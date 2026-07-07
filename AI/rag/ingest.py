"""
RAG 준비 작업 (한 번만 실행).
data/knowledge_base/<도메인>/ 의 .md 문서들을 읽어
→ 제목 단위로 청크 분리 → 로컬 임베딩 → data/vector_db/ 의 ChromaDB 에 저장.

★ 도메인별로 별도 컬렉션을 만든다 (라우팅용) ★
    data/knowledge_base/admin/     → 컬렉션 minwon_admin      (행정·절차 문의)
    data/knowledge_base/technical/ → 컬렉션 minwon_technical  (기술 질의)

실행 (레포 루트에서):
    python -m AI.rag.ingest
문서를 고치거나 추가한 뒤 다시 실행하면 컬렉션을 새로 만든다.
"""
import os
import glob
import chromadb

from AI.embedder import embed_texts

# 경로 (레포 루트 기준)
KB_DIR = "data/knowledge_base"
VECTOR_DIR = "data/vector_db"

# 도메인(하위폴더) → 컬렉션 이름 매핑
DOMAIN_COLLECTIONS = {
    "admin": "minwon_admin",          # 행정·절차 (기존 12개 카테고리)
    "technical": "minwon_technical",  # 기술 질의 (발전기·변압기 등, 추후 채움)
}

MAX_CHARS = 700
OVERLAP = 80


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    parts, start = [], 0
    while start < len(text):
        end = start + MAX_CHARS
        parts.append(text[start:end])
        start = end - OVERLAP
    return parts


def parse_markdown(path: str) -> list[dict]:
    """마크다운 한 파일을 제목(##,###) 단위 청크 리스트로 변환. (기존 로직 유지)"""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    source = os.path.basename(path)
    doc_title = source
    parent_h2 = ""

    chunks: list[dict] = []
    cur_heading = ""
    cur_body: list[str] = []

    def flush():
        body = "\n".join(cur_body).strip()
        if not cur_heading or not body:
            return
        path_parts = [p for p in [doc_title, parent_h2, cur_heading] if p]
        header_line = " > ".join(path_parts)
        full = f"{header_line}\n{body}"
        for piece in _split_long(full):
            chunks.append({
                "text": piece,
                "source": source,
                "heading": cur_heading,
                "section": parent_h2,
            })

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            doc_title = line[2:].strip()
            continue
        if line.startswith(">") or line.strip() == "---":
            continue
        if line.startswith("### "):
            flush()
            cur_heading = line[4:].strip()
            cur_body = []
            continue
        if line.startswith("## "):
            flush()
            parent_h2 = line[3:].strip()
            cur_heading = line[3:].strip()
            cur_body = []
            continue
        cur_body.append(line)

    flush()
    return chunks


def _ingest_domain(client, domain: str, collection_name: str) -> int:
    """한 도메인 폴더를 읽어 해당 컬렉션으로 저장. 저장한 청크 수 반환."""
    domain_dir = os.path.join(KB_DIR, domain)
    paths = sorted(glob.glob(os.path.join(domain_dir, "*.md")))

    # 컬렉션은 항상 새로 만든다 (기존 것 삭제 후 재생성)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    if not paths:
        print(f"[ingest] ({domain}) 문서 없음 → 빈 컬렉션 '{collection_name}' 생성")
        return 0

    all_chunks: list[dict] = []
    for p in paths:
        cs = parse_markdown(p)
        all_chunks.extend(cs)
        print(f"[ingest] ({domain}) {os.path.basename(p)} -> 청크 {len(cs)}개")

    texts = [c["text"] for c in all_chunks]
    vectors = embed_texts(texts)
    collection.add(
        ids=[f"{domain}-chunk-{i}" for i in range(len(all_chunks))],
        embeddings=vectors,
        documents=texts,
        metadatas=[
            {"source": c["source"], "heading": c["heading"],
             "section": c["section"], "domain": domain}
            for c in all_chunks
        ],
    )
    print(f"[ingest] ({domain}) 총 {len(all_chunks)}개 → '{collection_name}' 저장 완료")
    return len(all_chunks)


def main():
    client = chromadb.PersistentClient(path=VECTOR_DIR)
    total = 0
    for domain, coll in DOMAIN_COLLECTIONS.items():
        total += _ingest_domain(client, domain, coll)
    print(f"[ingest] 전체 완료! 총 {total}개 청크. 저장 위치: {VECTOR_DIR}/")


if __name__ == "__main__":
    main()