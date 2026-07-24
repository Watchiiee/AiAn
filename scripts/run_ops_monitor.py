"""
Ops 모니터링 에이전트 - 실제 운영용 진입점. GitHub Actions 스케줄(cron)로
매일 실행된다(.github/workflows/ops-monitor.yml).

흐름: Langfuse에서 최근 24시간 트레이스 조회 -> 집계(코드가 패턴 판정까지
결정론적으로 확정) -> LLM이 설명 붙인 리포트 생성 -> 이메일 발송.
이메일 설정이 없으면 콘솔에 리포트만 출력하고 정상 종료(실패로 취급 안 함).
"""
import sys
import os
import datetime as _dt

sys.path.insert(0, os.getcwd())

from AI.ops_monitor import fetch_recent_traces, aggregate_stats, generate_ops_report, send_email_report  # noqa: E402


def run():
    print("[ops_monitor] 최근 24시간 트레이스 조회 중...")
    traces = fetch_recent_traces(hours=24)
    print(f"[ops_monitor] {len(traces)}건 조회됨")

    stats = aggregate_stats(traces)
    if stats["total"] == 0:
        print("[ops_monitor] 최근 24시간 동안 처리된 문의가 없어 리포트를 생성하지 않습니다.")
        return

    print(f"[ops_monitor] 사전 판정: {stats['pattern_verdict']}")
    report = generate_ops_report(stats)

    date_str = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    subject = f"[AiAn Ops 리포트] {date_str} {stats['pattern_label']}"

    print("\n" + "=" * 70)
    print(subject)
    print("=" * 70)
    print(report)

    sent = send_email_report(subject, report)
    if sent:
        print("\n[ops_monitor] 이메일 발송 완료")
    else:
        print("\n[ops_monitor] 이메일 설정이 없어 발송을 건너뜀 (위 콘솔 출력이 리포트 전체입니다)")


if __name__ == "__main__":
    run()