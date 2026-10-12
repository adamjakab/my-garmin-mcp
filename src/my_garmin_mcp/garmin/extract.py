"""Pure functions that cut Garmin's bulky payloads down to what is useful in a chat context."""

from datetime import UTC, datetime
from typing import Any


def _clean(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _local_iso(ms: int | float | None) -> str | None:
    """Garmin's '...Local' timestamps are epoch milliseconds shifted to local wall-clock time."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%dT%H:%M")


def sleep_summary(day: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Score, duration, stages and a few vitals for one night. None when Garmin has no sleep for that day."""
    if not payload:
        return None
    dto = payload.get("dailySleepDTO") or {}
    scores = dto.get("sleepScores") or {}
    score = (
        (scores.get("overall") or {}).get("value")
        or (dto.get("sleepScore") or {}).get("overallScore")
        or (payload.get("sleepScore") or {}).get("overallScore")
    )
    duration = dto.get("sleepTimeSeconds") or payload.get("sleepTimeSeconds")
    if score is None and duration is None:
        return None
    return _clean(
        {
            "date": day,
            "score": score,
            "duration_seconds": duration,
            "deep_seconds": dto.get("deepSleepSeconds"),
            "light_seconds": dto.get("lightSleepSeconds"),
            "rem_seconds": dto.get("remSleepSeconds"),
            "awake_seconds": dto.get("awakeSleepSeconds"),
            "awake_count": dto.get("awakeCount"),
            "start_local": _local_iso(dto.get("sleepStartTimestampLocal")),
            "end_local": _local_iso(dto.get("sleepEndTimestampLocal")),
            "avg_heart_rate": dto.get("avgHeartRate"),
            "resting_heart_rate": payload.get("restingHeartRate"),
            "avg_overnight_hrv": payload.get("avgOvernightHrv"),
            "hrv_status": payload.get("hrvStatus"),
            "avg_spo2": dto.get("averageSpO2Value"),
            "lowest_spo2": dto.get("lowestSpO2Value"),
            "avg_respiration": dto.get("averageRespirationValue"),
            "avg_sleep_stress": dto.get("avgSleepStress"),
            "body_battery_change": payload.get("bodyBatteryChange"),
            "feedback": dto.get("sleepScoreFeedback"),
        }
    )


def hrv_summary(day: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Nightly HRV summary and baseline, without the bulky raw readings."""
    if not payload or not payload.get("hrvSummary"):
        return None
    summary = payload["hrvSummary"]
    return _clean(
        {
            "date": summary.get("calendarDate") or day,
            "last_night_avg": summary.get("lastNightAvg"),
            "last_night_5min_high": summary.get("lastNight5MinHigh"),
            "weekly_avg": summary.get("weeklyAvg"),
            "status": summary.get("status"),
            "baseline": summary.get("baseline"),
        }
    )


def resting_hr(day: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    metrics = ((payload or {}).get("allMetrics") or {}).get("metricsMap") or {}
    for item in metrics.get("WELLNESS_RESTING_HEART_RATE") or []:
        if item.get("value") is not None:
            return {"date": item.get("calendarDate") or day, "resting_hr": item["value"]}
    return None


def heart_rate_day(day: str, payload: dict[str, Any] | None, bucket_minutes: int = 30) -> dict[str, Any] | None:
    """All-day heart rate reduced to min/max/avg per local-time bucket. None when there is no reading that day.

    `heartRateValues` holds [epoch ms GMT, bpm or null] pairs about every 2 minutes; they are shifted to local
    wall-clock time with the offset between the payload's local and GMT start timestamps before bucketing.
    Rows are compact lists in the order given by `columns`.
    """
    if not payload:
        return None
    start_local, start_gmt = payload.get("startTimestampLocal"), payload.get("startTimestampGMT")
    offset = (
        start_local - start_gmt if isinstance(start_local, int | float) and isinstance(start_gmt, int | float) else 0
    )
    buckets: dict[int, list[float]] = {}
    readings: list[float] = []
    for pair in payload.get("heartRateValues") or []:
        if not isinstance(pair, list | tuple) or len(pair) < 2:
            continue
        ts, bpm = pair[0], pair[1]
        if not isinstance(ts, int | float) or isinstance(bpm, bool) or not isinstance(bpm, int | float):
            continue
        local = datetime.fromtimestamp((ts + offset) / 1000, UTC)
        start = (local.hour * 60 + local.minute) // bucket_minutes * bucket_minutes
        buckets.setdefault(start, []).append(bpm)
        readings.append(bpm)
    if not readings:
        return None
    rows = [
        [f"{start // 60:02d}:{start % 60:02d}", min(vals), max(vals), round(sum(vals) / len(vals))]
        for start, vals in sorted(buckets.items())
    ]
    return _clean(
        {
            "date": payload.get("calendarDate") or day,
            "resting_hr": payload.get("restingHeartRate"),
            "min_hr": payload.get("minHeartRate") if payload.get("minHeartRate") is not None else min(readings),
            "max_hr": payload.get("maxHeartRate") if payload.get("maxHeartRate") is not None else max(readings),
            "avg_hr": round(sum(readings) / len(readings), 1),
            "bucket_minutes": bucket_minutes,
            "columns": ["time", "min", "max", "avg"],
            "readings": rows,
        }
    )


def vo2max_entries(payload: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """One entry per date that has a VO2 max value: running/generic and, when present, cycling."""
    out: list[dict[str, Any]] = []
    for item in payload or []:
        generic, cycling = item.get("generic") or {}, item.get("cycling") or {}
        entry = _clean(
            {
                "date": generic.get("calendarDate") or cycling.get("calendarDate"),
                "vo2max": generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue"),
                "vo2max_cycling": cycling.get("vo2MaxPreciseValue") or cycling.get("vo2MaxValue"),
            }
        )
        if entry.get("date") and ("vo2max" in entry or "vo2max_cycling" in entry):
            out.append(entry)
    return sorted(out, key=lambda e: e["date"])


def _kg(grams: float | None) -> float | None:
    return None if grams is None else round(grams / 1000, 2)


def weight_entries(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Weigh-ins with body composition. Garmin reports masses in grams; these are converted to kg."""
    out = []
    for item in (payload or {}).get("dateWeightList") or []:
        out.append(
            _clean(
                {
                    "date": item.get("calendarDate"),
                    "weight_kg": _kg(item.get("weight")),
                    "bmi": item.get("bmi"),
                    "body_fat_pct": item.get("bodyFat"),
                    "body_water_pct": item.get("bodyWater"),
                    "muscle_mass_kg": _kg(item.get("muscleMass")),
                    "bone_mass_kg": _kg(item.get("boneMass")),
                    "visceral_fat": item.get("visceralFat"),
                    "metabolic_age": item.get("metabolicAge"),
                }
            )
        )
    return sorted(out, key=lambda e: e.get("date") or "")


_ACTIVITY_LIST_FIELDS = {
    "activityId": "activity_id",
    "activityName": "name",
    "startTimeLocal": "start_local",
    "distance": "distance_m",
    "duration": "duration_s",
    "movingDuration": "moving_duration_s",
    "elevationGain": "elevation_gain_m",
    "averageSpeed": "avg_speed_mps",
    "maxSpeed": "max_speed_mps",
    "calories": "calories",
    "averageHR": "avg_hr",
    "maxHR": "max_hr",
    "avgPower": "avg_power",
    "maxPower": "max_power",
    "normPower": "norm_power",
    "averageRunningCadenceInStepsPerMinute": "avg_run_cadence",
    "steps": "steps",
    "aerobicTrainingEffect": "aerobic_training_effect",
    "anaerobicTrainingEffect": "anaerobic_training_effect",
    "trainingEffectLabel": "training_effect_label",
    "activityTrainingLoad": "training_load",
    "vO2MaxValue": "vo2max",
    "locationName": "location",
    "lapCount": "laps",
}


def activity_list_item(activity: dict[str, Any]) -> dict[str, Any]:
    item = {new: activity.get(old) for old, new in _ACTIVITY_LIST_FIELDS.items()}
    item["type"] = (activity.get("activityType") or {}).get("typeKey")
    return _clean(item)


_ACTIVITY_DROP = {"accessControlRuleDTO", "timeZoneUnitDTO", "metadataDTO", "userProfileId", "activityUUID"}


def flatten_activity(activity: dict[str, Any]) -> dict[str, Any]:
    """Merge summaryDTO into the top level, rename activityTypeDTO and drop bookkeeping fields."""
    flat = {k: v for k, v in activity.items() if k not in _ACTIVITY_DROP and k != "summaryDTO"}
    if "activityTypeDTO" in flat:
        flat["activityType"] = flat.pop("activityTypeDTO")
    flat.update(activity.get("summaryDTO") or {})
    return _clean(flat)


def bucket_details(details: dict[str, Any], bucket_seconds: int = 60) -> dict[str, Any]:
    """Reduce per-second activity metrics to min/max/avg/count per time bucket (the raw payload is ~1 MB).

    Buckets are keyed by elapsed seconds since the start (sumDuration), falling back to the sample index.
    Rows are compact lists in the order given by `columns`; GPS coordinates and running totals are left out.
    """
    descriptors = {d["metricsIndex"]: d["key"] for d in details.get("metricDescriptors") or []}
    rows = [r.get("metrics") or [] for r in details.get("activityDetailMetrics") or []]
    time_index = next((i for i, k in descriptors.items() if k == "sumDuration"), None)
    # Time axis, GPS and the running totals (sum*) say little per bucket; distance and duration are in the summary.
    skip = {"directTimestamp", "directLatitude", "directLongitude"}
    buckets: dict[str, dict[int, list[float]]] = {}
    for n, row in enumerate(rows):
        elapsed = row[time_index] if time_index is not None and time_index < len(row) else n
        if elapsed is None:
            continue
        start = int(elapsed // bucket_seconds) * bucket_seconds
        for i, key in descriptors.items():
            if key in skip or key.startswith("sum") or i >= len(row) or row[i] is None:
                continue
            buckets.setdefault(key, {}).setdefault(start, []).append(row[i])
    metrics = {
        key: [
            [start, round(min(vals), 2), round(max(vals), 2), round(sum(vals) / len(vals), 2), len(vals)]
            for start, vals in sorted(by_start.items())
        ]
        for key, by_start in buckets.items()
    }
    return {
        "bucket_seconds": bucket_seconds,
        "columns": ["seconds_since_start", "min", "max", "avg", "count"],
        "metrics": metrics,
    }
