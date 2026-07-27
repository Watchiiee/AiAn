"""
CORS_ALLOWED_ORIGINS 환경변수 파싱 회귀테스트. 배포 시 origin을 추가할 때
쉼표구분 파싱이 깨지지 않는지 확인(11절 배포 아키텍처에서 실제로 사용).
"""
from BE.core.config import Settings


def test_default_origins():
    s = Settings(_env_file=None)
    assert "http://localhost:5173" in s.cors_origins_list
    assert "http://localhost:3000" in s.cors_origins_list


def test_custom_origins_comma_separated():
    s = Settings(_env_file=None, cors_allowed_origins="http://localhost:5173,http://1.2.3.4:80")
    origins = s.cors_origins_list
    assert origins == ["http://localhost:5173", "http://1.2.3.4:80"]


def test_extra_whitespace_stripped():
    s = Settings(_env_file=None, cors_allowed_origins=" http://a.com , http://b.com ")
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]


def test_empty_string_yields_empty_list():
    s = Settings(_env_file=None, cors_allowed_origins="")
    assert s.cors_origins_list == []