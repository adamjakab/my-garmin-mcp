import pytest

from my_garmin_mcp.garmin.dates import InvalidRequest, days_in, parse_range
from my_garmin_mcp.garmin.extract import (
    activity_list_item,
    body_battery_days,
    bucket_details,
    flatten_activity,
    heart_rate_day,
    hrv_summary,
    respiration_day,
    resting_hr,
    sleep_summary,
    spo2_day,
    stress_day,
    training_readiness_day,
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


def test_sleep_summary_and_score_fallbacks():
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
            {"metricsIndex": 3, "key": "sumDistance"},
        ],
        "activityDetailMetrics": [
            {"metrics": [0, 100, 1000, 0]},
            {"metrics": [30, 110, 2000, 50]},
            {"metrics": [59, None, 3000, 90]},
            {"metrics": [60, 120, 4000, 99]},
        ],
        "geoPolylineDTO": {"huge": "dropped"},
    }
    out = bucket_details(details)
    assert out["columns"] == ["seconds_since_start", "min", "max", "avg", "count"]
    assert out["metrics"] == {"directHeartRate": [[0, 100, 110, 105.0, 2], [60, 120, 120, 120.0, 1]]}
    assert "geoPolylineDTO" not in out


HOUR = 3_600_000
# 2026-10-01 22:00 GMT; local is +2h, so the day starts at local midnight
GMT_START = 1_790_892_000_000


def _hr_payload(values, **extra):
    return {
        "calendarDate": "2026-10-02",
        "startTimestampGMT": GMT_START,
        "startTimestampLocal": GMT_START + 2 * HOUR,
        "heartRateValues": values,
        **extra,
    }


def test_heart_rate_day_buckets_in_local_time():
    values = [
        [GMT_START, 50],
        [GMT_START + 10 * 60_000, 60],
        [GMT_START + 40 * 60_000, 70],
        [GMT_START + 2 * HOUR, None],
    ]
    out = heart_rate_day("2026-10-02", _hr_payload(values, restingHeartRate=48, minHeartRate=45, maxHeartRate=120))
    assert out["columns"] == ["time", "min", "max", "avg"]
    assert out["readings"] == [["00:00", 50, 60, 55], ["00:30", 70, 70, 70]]
    assert (out["resting_hr"], out["min_hr"], out["max_hr"], out["avg_hr"]) == (48, 45, 120, 60.0)
    assert out["date"] == "2026-10-02"


def test_heart_rate_day_offset_crosses_the_gmt_day_boundary():
    out = heart_rate_day("2026-10-02", _hr_payload([[GMT_START + 90 * 60_000, 80]]))
    assert out["readings"] == [["01:30", 80, 80, 80]]


def test_heart_rate_day_without_timestamps_uses_offset_zero():
    payload = {"heartRateValues": [[GMT_START, 55]]}
    assert heart_rate_day("2026-10-02", payload)["readings"] == [["22:00", 55, 55, 55]]


def test_heart_rate_day_falls_back_to_reading_min_max_and_uses_day():
    out = heart_rate_day("2026-10-02", {"heartRateValues": [[GMT_START, 50], [GMT_START + 60_000, 70]]})
    assert (out["min_hr"], out["max_hr"], out["date"]) == (50, 70, "2026-10-02")
    assert "resting_hr" not in out


def test_heart_rate_day_bucket_minutes():
    values = [[GMT_START + i * 20 * 60_000, 60 + i] for i in range(6)]
    out = heart_rate_day("2026-10-02", _hr_payload(values), bucket_minutes=60)
    assert [r[0] for r in out["readings"]] == ["00:00", "01:00"]
    assert out["bucket_minutes"] == 60


@pytest.mark.parametrize("payload", [None, {}, {"heartRateValues": []}, {"heartRateValues": [[GMT_START, None]]}])
def test_heart_rate_day_none_without_readings(payload):
    assert heart_rate_day("2026-10-02", payload) is None


def _bb_day(rows, date="2026-10-01", descriptors=None, **extra):
    entry = {"date": date, "charged": 50, "drained": 40, "bodyBatteryValuesArray": rows, **extra}
    if descriptors is not None:
        entry["bodyBatteryValueDescriptorDTOList"] = [
            {"bodyBatteryValueDescriptorIndex": i, "bodyBatteryValueDescriptorKey": k}
            for i, k in enumerate(descriptors)
        ]
    return entry


HOUR = 3_600_000


def test_body_battery_days_summarises_and_downsamples():
    rows = [
        [0, "MEASURED", 30, 2.0],
        [HOUR, "MEASURED", 40, 2.0],
        [2 * HOUR, "MEASURED", 90, 2.0],
        [3 * HOUR, "MEASURED", 70, 2.0],
    ]
    [day] = body_battery_days([_bb_day(rows)])
    assert day == {
        "date": "2026-10-01",
        "highest": 90,
        "lowest": 30,
        "start": 30,
        "end": 70,
        "charged": 50,
        "drained": 40,
        "columns": ["time", "level"],
        "readings": [["00:00", 40], ["02:00", 70]],
    }


def test_body_battery_days_uses_descriptor_level_index():
    rows = [[0, 55, "MEASURED"], [HOUR, 65, "MEASURED"]]
    [day] = body_battery_days([_bb_day(rows, descriptors=["timestamp", "bodyBatteryLevel", "bodyBatteryStatus"])])
    assert (day["start"], day["end"]) == (55, 65)


def test_body_battery_days_two_wide_rows_fallback():
    [day] = body_battery_days([_bb_day([[0, 10], [HOUR, 20]])])
    assert (day["lowest"], day["highest"]) == (10, 20)


def test_body_battery_days_applies_local_offset():
    [day] = body_battery_days([_bb_day([[0, 10]], startTimestampGMT=0, startTimestampLocal=3 * HOUR)])
    assert day["readings"] == [["02:00", 10]]


GMT_4AM = 1_790_827_200_000  # 2026-10-01T04:00:00 UTC in epoch ms


def test_body_battery_days_applies_offset_from_iso_timestamps():
    day = _bb_day(
        [[GMT_4AM, 10]], startTimestampGMT="2026-10-01T04:00:00.0", startTimestampLocal="2026-10-01T06:00:00.0"
    )
    [result] = body_battery_days([day])
    assert result["readings"] == [["06:00", 10]]


def test_body_battery_days_iso_timestamps_with_explicit_offsets():
    day = _bb_day(
        [[GMT_4AM, 10]], startTimestampGMT="2026-10-01T04:00:00+00:00", startTimestampLocal="2026-10-01T06:00:00+00:00"
    )
    [result] = body_battery_days([day])
    assert result["readings"] == [["06:00", 10]]


def test_body_battery_days_unparseable_iso_timestamp_means_no_offset():
    day = _bb_day([[GMT_4AM, 10]], startTimestampGMT="not a date", startTimestampLocal="2026-10-01T06:00:00.0")
    [result] = body_battery_days([day])
    assert result["readings"] == [["04:00", 10]]


def test_body_battery_days_skips_malformed_rows_and_empty_days():
    rows = [
        [0, "M", None, 1],
        [HOUR, "M", True, 1],
        [2 * HOUR, "M", "x", 1],
        "junk",
        [3 * HOUR],
        ["t", "M", 5, 1],
        [4 * HOUR, "M", 44, 1],
    ]
    days = body_battery_days([_bb_day(rows), _bb_day([[0, "M", None, 1]], date="2026-10-02"), "junk"])
    assert [d["date"] for d in days] == ["2026-10-01"]
    assert days[0]["start"] == days[0]["end"] == 44


@pytest.mark.parametrize(
    "payload", [None, {}, [], "x", [{}], [{"bodyBatteryValuesArray": None}], [{"bodyBatteryValuesArray": []}]]
)
def test_body_battery_days_empty_payloads(payload):
    assert body_battery_days(payload) == []


def test_body_battery_days_keeps_date_order():
    days = body_battery_days(
        [_bb_day([[0, "M", 1, 1]], date="2026-10-02"), _bb_day([[0, "M", 2, 1]], date="2026-10-01")]
    )
    assert [d["date"] for d in days] == ["2026-10-01", "2026-10-02"]


def _stress_payload(**extra):
    return {
        "calendarDate": "2026-10-01",
        "startTimestampGMT": 0,
        "startTimestampLocal": 0,
        "stressValuesArray": [[0, 20], [60_000, 40], [1_800_000, 0]],
        **extra,
    }


def test_stress_day_summarises_and_buckets():
    day = stress_day(
        "2026-10-01",
        _stress_payload(
            avgStressLevel=33,
            maxStressLevel=90,
            restStressDuration=3600,
            lowStressDuration=1800,
            mediumStressDuration=600,
            highStressDuration=0,
        ),
    )
    assert day == {
        "date": "2026-10-01",
        "avg_stress": 33,
        "max_stress": 90,
        "rest_min": 60,
        "low_min": 30,
        "medium_min": 10,
        "high_min": 0,
        "bucket_minutes": 30,
        "columns": ["time", "level"],
        "readings": [["00:00", 30], ["00:30", 0]],
    }


def test_stress_day_applies_local_offset():
    payload = _stress_payload(startTimestampLocal=3 * 3600_000)
    assert stress_day("d", payload)["readings"][0] == ["03:00", 30]


def test_stress_day_handles_iso_timestamps():
    payload = _stress_payload(startTimestampGMT="2026-10-01T00:00:00", startTimestampLocal="2026-10-01T03:00:00")
    assert stress_day("d", payload)["readings"][0][0] == "03:00"


def test_stress_day_drops_invalid_rows_and_falls_back_to_computed_summary():
    payload = {
        "startTimestampGMT": 0,
        "startTimestampLocal": 0,
        "stressValuesArray": [[0, -1], [1, -2], [2, None], [3, True], [4, 101], [True, 10], "x", [5], [6, 50], [7, 0]],
    }
    day = stress_day("2026-10-02", payload)
    assert day["date"] == "2026-10-02"
    assert (day["avg_stress"], day["max_stress"]) == (25, 50)
    assert day["readings"] == [["00:00", 25]]
    assert "rest_min" not in day


def test_stress_day_ignores_negative_summary_values():
    day = stress_day("d", _stress_payload(avgStressLevel=-1, overallStressLevel=28, maxStressLevel=-2))
    assert (day["avg_stress"], day["max_stress"]) == (28, 40)


def test_stress_day_custom_bucket_minutes():
    day = stress_day("d", _stress_payload(), bucket_minutes=60)
    assert day["bucket_minutes"] == 60
    assert day["readings"] == [["00:00", 20]]


def test_stress_day_summary_only():
    day = stress_day("d", {"avgStressLevel": 30, "maxStressLevel": 70})
    assert day == {"date": "d", "avg_stress": 30, "max_stress": 70}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [],
        "x",
        {"stressValuesArray": []},
        {"stressValuesArray": [[0, -1], [1, None]]},
        {"stressValuesArray": 5},
    ],
)
def test_stress_day_without_data_is_none(payload):
    assert stress_day("d", payload) is None


def _tr(**kw):
    return {"calendarDate": "2026-10-01", "timestamp": "2026-10-01T05:00:00.0", "score": 70, "level": "HIGH", **kw}


def test_training_readiness_picks_latest_snapshot_and_maps_factors():
    early = _tr(score=50, level="MODERATE")
    late = _tr(
        timestamp="2026-10-01T09:00:00.0",
        timestampLocal="2026-10-01T11:30:00.0",
        feedbackShort="GOOD_DAY",
        feedbackLong="long text",
        sleepScore=80,
        recoveryTime=120,
        recoveryTimeChangePhrase="PHRASE",
        sleepScoreFactorPercent=90,
        sleepScoreFactorFeedback="GOOD",
        hrvFactorPercent=70,
        acwrFactorFeedback="OK",
    )
    assert training_readiness_day("2026-10-01", [late, early]) == {
        "date": "2026-10-01",
        "score": 70,
        "level": "HIGH",
        "feedback": "GOOD_DAY",
        "time": "11:30",
        "sleep_score": 80,
        "recovery_min": 120,
        "recovery_phase": "PHRASE",
        "factors": {
            "sleep": {"pct": 90, "feedback": "GOOD"},
            "load": {"feedback": "OK"},
            "hrv": {"pct": 70},
        },
    }
    assert training_readiness_day("2026-10-01", [early, late])["score"] == 70


def test_training_readiness_accepts_single_dict_and_keeps_zero_score():
    result = training_readiness_day("2026-10-01", {"score": 0, "level": "POOR"})
    assert result == {"date": "2026-10-01", "score": 0, "level": "POOR"}


@pytest.mark.parametrize("payload", [None, [], {}, "x", 5, [None, "x"], [{"timestamp": "t"}], [{"score": True}]])
def test_training_readiness_empty_or_odd_payload_is_none(payload):
    assert training_readiness_day("2026-10-01", payload) is None


def test_training_readiness_odd_types_never_raise():
    result = training_readiness_day(
        "2026-10-01",
        [{"score": 60, "level": 5, "timestamp": 3, "timestampLocal": "garbage", "hrvFactorPercent": "90"}],
    )
    assert result == {"date": "2026-10-01", "score": 60}
    assert "time" not in training_readiness_day("2026-10-01", [_tr(timestampLocal=None)])


def _spo2_payload(**extra):
    return {
        "calendarDate": "2026-10-01",
        "startTimestampGMT": 0,
        "startTimestampLocal": 0,
        "spO2HourlyAverages": [[0, 96], [1_800_000, 94], [3_600_000, 98]],
        **extra,
    }


def test_spo2_day_summarises_and_buckets():
    day = spo2_day("d", _spo2_payload(averageSpO2=95, lowestSpO2=88, latestSpO2=97, avgSleepSpO2=93))
    assert day == {
        "date": "2026-10-01",
        "avg_spo2": 95,
        "lowest_spo2": 88,
        "latest_spo2": 97,
        "avg_sleep_spo2": 93,
        "bucket_minutes": 60,
        "columns": ["time", "value"],
        "readings": [["00:00", 95], ["01:00", 98]],
    }


def test_spo2_day_applies_local_offset_across_midnight():
    payload = _spo2_payload(startTimestampLocal=-3600_000)
    assert spo2_day("d", payload)["readings"] == [["00:00", 98], ["23:00", 95]]


def test_spo2_day_handles_iso_timestamps():
    payload = _spo2_payload(startTimestampGMT="2026-10-01T00:00:00", startTimestampLocal="2026-10-01T03:00:00")
    assert spo2_day("d", payload)["readings"][0][0] == "03:00"


def test_spo2_day_drops_invalid_rows_and_falls_back_to_computed_summary():
    payload = {
        "spO2HourlyAverages": [[0, 0], [1, -1], [2, None], [3, True], [4, 101], [True, 90], "x", [5], [6, 90], [7, 94]],
        "averageSpO2": 0,
        "lowestSpO2": -1,
    }
    day = spo2_day("2026-10-02", payload)
    assert day["date"] == "2026-10-02"
    assert (day["avg_spo2"], day["lowest_spo2"]) == (92, 90)
    assert day["readings"] == [["00:00", 92]]
    assert "latest_spo2" not in day


def test_spo2_day_summary_only():
    assert spo2_day("d", {"averageSpO2": 95, "lowestSpO2": 90}) == {"date": "d", "avg_spo2": 95, "lowest_spo2": 90}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [],
        "x",
        {"spO2HourlyAverages": []},
        {"spO2HourlyAverages": [[0, 0], [1, None]], "averageSpO2": None},
        {"spO2HourlyAverages": 5},
    ],
)
def test_spo2_day_without_data_is_none(payload):
    assert spo2_day("d", payload) is None


def _respiration_payload(**extra):
    return {
        "calendarDate": "2026-10-01",
        "startTimestampGMT": 0,
        "startTimestampLocal": 0,
        "respirationValuesArray": [[0, 14], [120_000, 15], [1_800_000, 12.5]],
        **extra,
    }


def test_respiration_day_summarises_and_buckets():
    day = respiration_day(
        "d",
        _respiration_payload(
            lowestRespirationValue=9,
            highestRespirationValue=22,
            avgWakingRespirationValue=15,
            avgSleepRespirationValue=13,
        ),
    )
    assert day == {
        "date": "2026-10-01",
        "lowest_respiration": 9,
        "highest_respiration": 22,
        "avg_waking_respiration": 15,
        "avg_sleep_respiration": 13,
        "bucket_minutes": 30,
        "columns": ["time", "value"],
        "readings": [["00:00", 14.5], ["00:30", 12.5]],
    }


def test_respiration_day_applies_local_offset_and_iso():
    assert respiration_day("d", _respiration_payload(startTimestampLocal=3 * 3600_000))["readings"][0][0] == "03:00"
    iso = _respiration_payload(startTimestampGMT="2026-10-01T00:00:00", startTimestampLocal="2026-10-01T03:00:00")
    assert respiration_day("d", iso)["readings"][0][0] == "03:00"


def test_respiration_day_drops_invalid_rows_and_falls_back_to_computed_summary():
    payload = {
        "respirationValuesArray": [
            [0, -1],
            [1, 0],
            [2, None],
            [3, True],
            [4, 101],
            [True, 10],
            "x",
            [5],
            [6, 12],
            [7, 16],
        ],
        "lowestRespirationValue": -1,
    }
    day = respiration_day("2026-10-02", payload)
    assert (day["lowest_respiration"], day["highest_respiration"]) == (12, 16)
    assert day["readings"] == [["00:00", 14]]
    assert "avg_sleep_respiration" not in day


def test_respiration_day_summary_only():
    assert respiration_day("d", {"avgSleepRespirationValue": 13.5}) == {"date": "d", "avg_sleep_respiration": 13.5}


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [],
        "x",
        {"respirationValuesArray": []},
        {"respirationValuesArray": [[0, -1], [1, None], [2, 0]], "lowestRespirationValue": -1},
        {"respirationValuesArray": 5},
    ],
)
def test_respiration_day_without_data_is_none(payload):
    assert respiration_day("d", payload) is None
