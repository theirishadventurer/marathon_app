from garmin_agent.api_client import build_payload


def test_build_payload_shape():
    p = build_payload([{"activityId": 1}], [{"calendarDate": "2026-06-10"}])
    assert p == {"activities": [{"activityId": 1}], "metrics": [{"calendarDate": "2026-06-10"}]}


def test_build_payload_defaults_empty():
    assert build_payload(None, None) == {"activities": [], "metrics": []}
