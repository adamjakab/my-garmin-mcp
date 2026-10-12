import pytest

from my_garmin_mcp.garmin.dates import InvalidRequest, days_in, parse_range
from my_garmin_mcp.garmin.extract import (
    activity_list_item,
    bucket_details,
    flatten_activity,
    hrv_summary,
    resting_hr,
    sleep_summary,
    vo2max_entries,
    weight_entries,
)


def test_parse_range_validates():
    start, end = parse_range("2026-10-01", "2026-10-03", 31)
    assert [d.isoformat() for d in days_in(start, end)] == ["2026-10-01", "2026-10-02", "2026-10-03"]
    with pytest.raises(InvalidRequest, match="YYYY-MM-DD"):
        parse_range("10/01/2026", "2026-10-03", 31)
    with pytest.raises(InvalidRequest, match="on or after"):
        parse_range("2026-10-03", "2026-10-01", 31)
    with pytest.raises(InvalidRequest, match="at most 31"):
        parse_range("2026-01-01", "2026-03-01", 31)


def test_sleep_summary_and_legacy_fallbacks():
    payload = {
        "dailySleepDTO": {
            "sleepTimeSeconds": 20400,
            "deepSleepSeconds": 4020,
            "sleepScores": {"overall": {"value": 81}},
            "sleepStartTimestampLocal": 1791596875000,
        },
        "restingHeartRate": 53,
    }
    s = sleep_summary("2026-10-10", payload)
    assert s["score"] == 81 and s["duration_seconds"] == 20400 and s["deep_seconds"] == 4020
    assert s["start_local"] == "2026-10-10T01:47" and s["resting_heart_rate"] == 53
    assert "rem_seconds" not in s  # missing values are dropped
    assert sleep_summary("d", {"dailySleepDTO": {"sleepScore": {"overallScore": 70}}})["score"] == 70
    assert sleep_summary("d", {"dailySleepDTO": {}}) is None
    assert sleep_summary("d", None) is None


def test_hrv_drops_raw_readings():
    payload = {
        "hrvSummary": {"calendarDate": "2026-10-10", "lastNightAvg": 44, "status": "BALANCED"},
        "hrvReadings": [1] * 50,
    }
    assert hrv_summary("d", payload) == {"date": "2026-10-10", "last_night_avg": 44, "status": "BALANCED"}
    assert hrv_summary("d", {"hrvSummary": None}) is None


def test_resting_hr():
    payload = {
        "allMetrics": {"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [{"value": 53.0, "calendarDate": "2026-10-10"}]}}
    }
    assert resting_hr("d", payload) == {"date": "2026-10-10", "resting_hr": 53.0}
    assert resting_hr("d", {"allMetrics": {"metricsMap": {}}}) is None


def test_vo2max_entries_skip_empty_and_sort():
    payload = [
        {"generic": {"calendarDate": "2026-08-20", "vo2MaxPreciseValue": 42.5}, "cycling": None},
        {
            "generic": {"calendarDate": "2026-08-17", "vo2MaxPreciseValue": 42.1},
            "cycling": {"calendarDate": "2026-08-17", "vo2MaxValue": 50},
        },
        {"generic": {"calendarDate": "2026-08-18"}, "cycling": None},
    ]
    assert vo2max_entries(payload) == [
        {"date": "2026-08-17", "vo2max": 42.1, "vo2max_cycling": 50},
        {"date": "2026-08-20", "vo2max": 42.5},
    ]


def test_weight_converts_grams():
    payload = {
        "dateWeightList": [{"calendarDate": "2026-10-01", "weight": 80500.0, "bodyFat": 18.2, "muscleMass": 35000}]
    }
    assert weight_entries(payload) == [
        {"date": "2026-10-01", "weight_kg": 80.5, "body_fat_pct": 18.2, "muscle_mass_kg": 35.0}
    ]
    assert weight_entries({"dateWeightList": []}) == []


def test_activity_list_item_is_curated():
    item = activity_list_item(
        {
            "activityId": 1,
            "activityName": "Run",
            "distance": 5000.0,
            "activityType": {"typeKey": "running"},
            "ownerProfileImageUrlLarge": "x",
            "userRoles": ["a"],
            "avgPower": None,
        }
    )
    assert item == {"activity_id": 1, "name": "Run", "distance_m": 5000.0, "type": "running"}


def test_flatten_activity():
    flat = flatten_activity(
        {
            "activityId": 1,
            "activityTypeDTO": {"typeKey": "running"},
            "metadataDTO": {"big": 1},
            "summaryDTO": {"distance": 10.0, "averageHR": 150},
        }
    )
    assert flat == {"activityId": 1, "activityType": {"typeKey": "running"}, "distance": 10.0, "averageHR": 150}


def test_bucket_details_groups_by_minute():
    details = {
        "metricDescriptors": [
            {"metricsIndex": 0, "key": "sumDuration"},
            {"metricsIndex": 1, "key": "directHeartRate"},
            {"metricsIndex": 2, "key": "directTimestamp"},
        ],
        "activityDetailMetrics": [
            {"metrics": [0, 100, 1000]},
            {"metrics": [30, 110, 2000]},
            {"metrics": [59, None, 3000]},
            {"metrics": [60, 120, 4000]},
        ],
        "geoPolylineDTO": {"huge": "dropped"},
    }
    out = bucket_details(details)
    assert out["columns"] == ["seconds_since_start", "min", "max", "avg", "count"]
    assert out["metrics"] == {"directHeartRate": [[0, 100, 110, 105.0, 2], [60, 120, 120, 120.0, 1]]}
    assert "geoPolylineDTO" not in out
