"""
RAG 준비 작업 (한 번만 실행).
data/knowledge_base/ 의 .md 문서들을 읽어
→ 제목 단위로 청크 분리
→ 로컬 임베딩으로 벡터화
→ data/vector_db/ 의 ChromaDB 에 저장한다.

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
COLLECTION_NAME = "minwon_kb"

# 청크가 너무 길면(이 글자수 초과) 잘라준다. 네 문서는 대부분 안 걸린다.
MAX_CHARS = 700
OVERLAP = 80


def _split_long(text: str) -> list[str]:
    """아주 긴 청크만 글자수 기준으로 겹치게 분할 (안전장치)."""
    if len(text) <= MAX_CHARS:
        return [text]
    parts, start = [], 0
    while start < len(text):
        end = start + MAX_CHARS
        parts.append(text[start:end])
        start = end - OVERLAP
    return parts


def parse_markdown(path: str) -> list[dict]:
    """
    마크다운 한 파일을 청크 리스트로 변환.
    제목(##, ###)을 만날 때마다 블록을 끊는다.
    → '### Q. 질문 / 답' 한 쌍이 청크 하나가 되어 검색에 잘 맞는다.
    각 청크에 (제목 계층 + 본문)을 넣어 맥락을 살린다.
    """
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
            return  # 제목만 있고 본문 없는 블록(예: FAQ 섹션 헤더)은 버림
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


def main():
    paths = sorted(glob.glob(os.path.join(KB_DIR, "*.md")))
    if not paths:
        print(f"[ingest] {KB_DIR} 에 .md 문서가 없습니다.")
        return

    all_chunks: list[dict] = []
    for p in paths:
        cs = parse_markdown(p)
        all_chunks.extend(cs)
        print(f"[ingest] {os.path.basename(p)} -> 청크 {len(cs)}개")

    print(f"[ingest] 총 청크 {len(all_chunks)}개. 임베딩 시작...")

    texts = [c["text"] for c in all_chunks]
    vectors = embed_texts(texts)

    client = chromadb.PersistentClient(path=VECTOR_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[f"chunk-{i}" for i in range(len(all_chunks))],
        embeddings=vectors,
        documents=texts,
        metadatas=[
            {"source": c["source"], "heading": c["heading"], "section": c["section"]}
            for c in all_chunks
        ],
    )

    print(f"[ingest] 완료! {len(all_chunks)}개 청크를 '{COLLECTION_NAME}' 컬렉션에 저장했습니다.")
    print(f"[ingest] 저장 위치: {VECTOR_DIR}/")


if __name__ == "__main__":
    main()