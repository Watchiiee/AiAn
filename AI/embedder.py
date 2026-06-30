"""
임베딩 담당. 문서/질문을 숫자 벡터로 바꾼다.
llm.py 와 같은 이유로 따로 분리해 둔다 — 나중에 OpenAI 임베딩으로
바꾸고 싶으면 이 파일의 embed_texts() 내부만 갈아끼우면 된다.

지금은 로컬 모델(키 불필요, 무료, 오프라인).
모델은 처음 한 번만 인터넷에서 다운로드되고 이후 캐시된다.
"""
from typing import List

# 한국어 문장 임베딩 모델 (한국어 의미 유사도에 강함)
MODEL_NAME = "jhgan/ko-sroberta-multitask"

_model = None  # 최초 호출 때 한 번만 로드 (무거우니 재사용)


def _get_model():
    global _model
    if _model is None:
        # import 를 함수 안에 둬서, 임베딩을 안 쓰는 경로에선
        # 무거운 라이브러리 로딩을 피한다.
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """여러 문장을 한 번에 임베딩. 코사인 유사도를 쓰려고 정규화한다."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def embed_text(text: str) -> List[float]:
    """문장 하나 임베딩."""
    return embed_texts([text])[0]