"""
Langfuse Public API로 최근 트레이스를 조회하는 방식을 실제로 확인하는 스크립트.

[불확실성 명시] 우리는 지금까지 Langfuse를 대시보드로 눈으로만 봤지,
프로그래밍적으로 조회한 적이 없다. 아래는 Langfuse Public API의 알려진
방식(HTTP Basic Auth: public key를 username, secret key를 password로 사용해
GET {host}/api/public/traces 호출)을 가정한 것이며, 실제 응답을 보고
맞는지/필드가 무엇인지 확인해야 한다 - Upstage 모델명 문제 때와 같은 방식으로
원본 응답을 그대로 까본다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_langfuse_api
"""
import sys
import os
import json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.getcwd())

import requests  # noqa: E402
from BE.core.config import settings  # noqa: E402


def run():
    print(f"langfuse_public_key 설정 여부: {bool(settings.langfuse_public_key.strip())}")
    print(f"langfuse_secret_key 설정 여부: {bool(settings.langfuse_secret_key.strip())}")
    print(f"langfuse_host: {settings.langfuse_host}\n")

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    url = f"{settings.langfuse_host.rstrip('/')}/api/public/traces"
    params = {
        "limit": 5,
        "fromTimestamp": since.isoformat(),
    }

    print(f"요청 URL: {url}")
    print(f"쿼리 파라미터: {params}\n")

    try:
        resp = requests.get(
            url,
            params=params,
            auth=(settings.langfuse_public_key, settings.langfuse_secret_key),
            timeout=15,
        )
    except Exception as e:
        print(f"요청 실패: {type(e).__name__}: {e}")
        return

    print(f"HTTP 상태 코드: {resp.status_code}\n")

    try:
        data = resp.json()
    except Exception as e:
        print(f"JSON 파싱 실패: {e}")
        print("원본 텍스트:", resp.text[:1000])
        return

    print("=" * 70)
    print("응답 구조 (최대 2000자)")
    print("=" * 70)
    print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])

    print("\n해석 가이드:")
    print("- 200이면 인증·엔드포인트 방식이 맞다는 뜻 -> 이 구조로 집계 로직을 짜면 됨")
    print("- 401/403이면 인증 방식(Basic Auth 조합)이 다르다는 뜻 -> Langfuse 대시보드의")
    print("  Settings > API Keys 페이지에서 정확한 사용법 문서를 확인할 것")
    print("- 404면 엔드포인트 경로 자체가 바뀐 것일 수 있음 -> Langfuse 공식 API 문서 확인 필요")


if __name__ == "__main__":
    run()