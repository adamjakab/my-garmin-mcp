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


def _epoch_ms(value: Any) -> int | float | None:
    """Epoch milliseconds from a number or an ISO string (read as UTC when it has no offset); None otherwise."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.replace(tzinfo=parsed.tzinfo or UTC).timestamp() * 1000
    return None


def _body_battery_level_index(entry: dict[str, Any]) -> int | None:
    for descriptor in entry.get("bodyBatteryValueDescriptorDTOList") or []:
        if isinstance(descriptor, dict) and descriptor.get("bodyBatteryValueDescriptorKey") == "bodyBatteryLevel":
            index = descriptor.get("bodyBatteryValueDescriptorIndex")
            if isinstance(index, int) and not isinstance(index, bool) and index >= 0:
                return index
    return None


def body_battery_days(payload: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Body Battery per day: highest, lowest, first/last level, charged/drained and a 2-hourly series.

    `bodyBatteryValuesArray` holds [epoch ms GMT, status, level, version] rows (the level column is looked up in
    `bodyBatteryValueDescriptorDTOList`); they are shifted to local wall-clock time with the offset between the
    entry's local and GMT start timestamps and reduced to the last level per 2-hour bucket. Days without a valid
    reading are left out; odd payloads never raise.
    """
    if not isinstance(payload, list):
        return []
    out: list[dict[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        rows = entry.get("bodyBatteryValuesArray")
        if not isinstance(rows, list | tuple):
            continue
        level_index = _body_battery_level_index(entry)
        start_local, start_gmt = _epoch_ms(entry.get("startTimestampLocal")), _epoch_ms(entry.get("startTimestampGMT"))
        offset = start_local - start_gmt if start_local is not None and start_gmt is not None else 0
        readings: list[tuple[int | float, int | float]] = []
        for row in rows:
            if not isinstance(row, list | tuple):
                continue
            index = level_index if level_index is not None else (2 if len(row) >= 4 else 1)
            if index == 0 or len(row) <= index:
                continue
            ts, level = row[0], row[index]
            if isinstance(ts, bool) or not isinstance(ts, int | float):
                continue
            if isinstance(level, bool) or not isinstance(level, int | float):
                continue
            readings.append((ts, level))
        if not readings:
            continue
        readings.sort(key=lambda r: r[0])
        levels = [level for _, level in readings]
        buckets: dict[int, int | float] = {}
        for ts, level in readings:
            local = datetime.fromtimestamp((ts + offset) / 1000, UTC)
            buckets[local.hour // 2 * 120] = level
        out.append(
            _clean(
                {
                    "date": entry.get("date"),
                    "highest": max(levels),
                    "lowest": min(levels),
                    "start": levels[0],
                    "end": levels[-1],
                    "charged": entry.get("charged"),
                    "drained": entry.get("drained"),
                    "columns": ["time", "level"],
                    "readings": [
                        [f"{start // 60:02d}:{start % 60:02d}", level] for start, level in sorted(buckets.items())
                    ],
                }
            )
        )
    out.sort(key=lambda d: d.get("date") or "")
    return out


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


def _stress_level(value: Any) -> int | float | None:
    """A stress level 0-100; None for negatives (-1 unmeasurable, -2 too much motion), null and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 100:
        return None
    return value


def _stress_minutes(seconds: Any) -> int | None:
    if isinstance(seconds, bool) or not isinstance(seconds, int | float) or seconds < 0:
        return None
    return round(seconds / 60)


def stress_day(day: str, payload: dict[str, Any] | None, bucket_minutes: int = 30) -> dict[str, Any] | None:
    """All-day stress: average/max level, minutes per stress band and a mean level per local-time bucket.

    `stressValuesArray` holds [epoch ms GMT, level] pairs about every 3 minutes; they are shifted to local
    wall-clock time with the offset between the payload's local and GMT start timestamps before bucketing.
    Negative and null levels are no reading. None when there is neither a reading nor a summary value; odd
    payloads never raise.
    """
    if not isinstance(payload, dict):
        return None
    start_local, start_gmt = _epoch_ms(payload.get("startTimestampLocal")), _epoch_ms(payload.get("startTimestampGMT"))
    offset = start_local - start_gmt if start_local is not None and start_gmt is not None else 0
    rows = payload.get("stressValuesArray")
    buckets: dict[int, list[int | float]] = {}
    levels: list[int | float] = []
    for row in rows if isinstance(rows, list | tuple) else []:
        if not isinstance(row, list | tuple) or len(row) < 2:
            continue
        ts, level = row[0], _stress_level(row[1])
        if isinstance(ts, bool) or not isinstance(ts, int | float) or level is None:
            continue
        local = datetime.fromtimestamp((ts + offset) / 1000, UTC)
        start = (local.hour * 60 + local.minute) // bucket_minutes * bucket_minutes
        buckets.setdefault(start, []).append(level)
        levels.append(level)
    avg = next(
        (
            v
            for v in (_stress_level(payload.get("avgStressLevel")), _stress_level(payload.get("overallStressLevel")))
            if v is not None
        ),
        None,
    )
    if avg is None and levels:
        avg = round(sum(levels) / len(levels))
    peak = _stress_level(payload.get("maxStressLevel"))
    if peak is None and levels:
        peak = max(levels)
    durations = {
        "rest_min": _stress_minutes(payload.get("restStressDuration")),
        "low_min": _stress_minutes(payload.get("lowStressDuration")),
        "medium_min": _stress_minutes(payload.get("mediumStressDuration")),
        "high_min": _stress_minutes(payload.get("highStressDuration")),
    }
    if not levels and avg is None and peak is None:
        return None
    result = {
        "date": payload.get("calendarDate") or day,
        "avg_stress": avg,
        "max_stress": peak,
        **durations,
    }
    if levels:
        result.update(
            {
                "bucket_minutes": bucket_minutes,
                "columns": ["time", "level"],
                "readings": [
                    [f"{start // 60:02d}:{start % 60:02d}", round(sum(vals) / len(vals))]
                    for start, vals in sorted(buckets.items())
                ],
            }
        )
    return _clean(result)


def _in_range(value: Any, low: int | float, high: int | float) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not low <= value <= high:
        return None
    return value


def _local_buckets(
    payload: dict[str, Any], key: str, valid: Any, bucket_minutes: int, digits: int | None
) -> tuple[list[int | float], list[list[Any]]]:
    """Valid readings from `payload[key]` ([epoch ms GMT, value] rows) and their mean per local-time bucket."""
    start_local, start_gmt = _epoch_ms(payload.get("startTimestampLocal")), _epoch_ms(payload.get("startTimestampGMT"))
    offset = start_local - start_gmt if start_local is not None and start_gmt is not None else 0
    rows = payload.get(key)
    buckets: dict[int, list[int | float]] = {}
    values: list[int | float] = []
    for row in rows if isinstance(rows, list | tuple) else []:
        if not isinstance(row, list | tuple) or len(row) < 2:
            continue
        ts, value = row[0], valid(row[1])
        if isinstance(ts, bool) or not isinstance(ts, int | float) or value is None:
            continue
        local = datetime.fromtimestamp((ts + offset) / 1000, UTC)
        start = (local.hour * 60 + local.minute) // bucket_minutes * bucket_minutes
        buckets.setdefault(start, []).append(value)
        values.append(value)
    readings = [
        [f"{start // 60:02d}:{start % 60:02d}", round(sum(vals) / len(vals), digits)]
        for start, vals in sorted(buckets.items())
    ]
    return values, readings


def _spo2_value(value: Any) -> int | float | None:
    """A SpO2 percentage 1-100; None for 0, negatives, null and non-numbers."""
    return _in_range(value, 1, 100)


def spo2_day(day: str, payload: dict[str, Any] | None, bucket_minutes: int = 60) -> dict[str, Any] | None:
    """All-day SpO2: average/lowest/latest/sleep average and a mean per local-time bucket.

    `spO2HourlyAverages` holds [epoch ms GMT, percent] pairs; they are shifted to local wall-clock time with the
    offset between the payload's local and GMT start timestamps before bucketing. Zero, negative and null values
    are no reading. None when there is neither a reading nor a summary value; odd payloads never raise.
    """
    if not isinstance(payload, dict):
        return None
    values, readings = _local_buckets(payload, "spO2HourlyAverages", _spo2_value, bucket_minutes, None)
    avg = _spo2_value(payload.get("averageSpO2"))
    if avg is None and values:
        avg = round(sum(values) / len(values))
    lowest = _spo2_value(payload.get("lowestSpO2"))
    if lowest is None and values:
        lowest = min(values)
    latest = _spo2_value(payload.get("latestSpO2"))
    sleep_avg = _spo2_value(payload.get("avgSleepSpO2"))
    if not values and avg is None and lowest is None and latest is None and sleep_avg is None:
        return None
    result = {
        "date": payload.get("calendarDate") or day,
        "avg_spo2": avg,
        "lowest_spo2": lowest,
        "latest_spo2": latest,
        "avg_sleep_spo2": sleep_avg,
    }
    if readings:
        result.update({"bucket_minutes": bucket_minutes, "columns": ["time", "value"], "readings": readings})
    return _clean(result)


def _breaths(value: Any) -> int | float | None:
    """Breaths per minute above 0 and at most 100; None for 0, negatives (no reading), null and non-numbers."""
    value = _in_range(value, 0, 100)
    return value or None


def respiration_day(day: str, payload: dict[str, Any] | None, bucket_minutes: int = 30) -> dict[str, Any] | None:
    """All-day respiration: lowest/highest, waking and sleep averages and a mean rate per local-time bucket.

    `respirationValuesArray` holds [epoch ms GMT, breaths/min] pairs about every 2 minutes; they are shifted to
    local wall-clock time as in `stress_day`. Zero, negative and null values are no reading. None when there is
    neither a reading nor a summary value; odd payloads never raise.
    """
    if not isinstance(payload, dict):
        return None
    values, readings = _local_buckets(payload, "respirationValuesArray", _breaths, bucket_minutes, 1)
    lowest = _breaths(payload.get("lowestRespirationValue"))
    if lowest is None and values:
        lowest = min(values)
    highest = _breaths(payload.get("highestRespirationValue"))
    if highest is None and values:
        highest = max(values)
    waking = _breaths(payload.get("avgWakingRespirationValue"))
    sleeping = _breaths(payload.get("avgSleepRespirationValue"))
    if not values and lowest is None and highest is None and waking is None and sleeping is None:
        return None
    result = {
        "date": payload.get("calendarDate") or day,
        "lowest_respiration": lowest,
        "highest_respiration": highest,
        "avg_waking_respiration": waking,
        "avg_sleep_respiration": sleeping,
    }
    if readings:
        result.update({"bucket_minutes": bucket_minutes, "columns": ["time", "value"], "readings": readings})
    return _clean(result)


def _tr_number(value: Any) -> int | float | None:
    return None if isinstance(value, bool) or not isinstance(value, int | float) else value


def _tr_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _tr_time(value: Any) -> str | None:
    """Local HH:MM from an ISO string or epoch milliseconds; None when unparseable."""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            pass
    ms = _epoch_ms(value)
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, UTC).strftime("%H:%M")
    except (OverflowError, OSError, ValueError):
        return None


_TRAINING_READINESS_FACTORS = {
    "sleep": "sleepScoreFactor",
    "recovery": "recoveryTimeFactor",
    "load": "acwrFactor",
    "hrv": "hrvFactor",
    "stress": "stressHistoryFactor",
}


def training_readiness_day(day: str, payload: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, Any] | None:
    """Training readiness: score, level, short feedback and the contributing factors of the day's latest snapshot.

    Garmin returns a list of snapshots per day (wake-up reset, scheduled updates); the one with the greatest
    `timestamp` is used. None when there is neither a numeric score nor a level; odd payloads never raise.
    """
    if isinstance(payload, dict):
        payload = [payload]
    snapshots = [p for p in payload if isinstance(p, dict)] if isinstance(payload, list) else []
    if not snapshots:
        return None
    # Entries without a (string) timestamp sort lowest; max keeps the first of equals, so reverse for "later wins".
    latest = max(reversed(snapshots), key=lambda p: _tr_text(p.get("timestamp")) or "")
    score, level = _tr_number(latest.get("score")), _tr_text(latest.get("level"))
    if score is None and level is None:
        return None
    factors = {}
    for name, prefix in _TRAINING_READINESS_FACTORS.items():
        factor = _clean(
            {"pct": _tr_number(latest.get(f"{prefix}Percent")), "feedback": _tr_text(latest.get(f"{prefix}Feedback"))}
        )
        if factor:
            factors[name] = factor
    return _clean(
        {
            "date": _tr_text(latest.get("calendarDate")) or day,
            "score": score,
            "level": level,
            "feedback": _tr_text(latest.get("feedbackShort")),
            "time": _tr_time(latest.get("timestampLocal")),
            "sleep_score": _tr_number(latest.get("sleepScore")),
            "recovery_min": _tr_number(latest.get("recoveryTime")),
            "recovery_phase": _tr_text(latest.get("recoveryTimeChangePhrase")),
            "factors": factors or None,
        }
    )


_DAILY_SUMMARY_FIELDS = {
    "steps": "totalSteps",
    "distance_m": "totalDistanceMeters",
    "floors_climbed": "floorsAscended",
    "moderate_intensity_min": "moderateIntensityMinutes",
    "vigorous_intensity_min": "vigorousIntensityMinutes",
    "calories": "totalKilocalories",
    "active_calories": "activeKilocalories",
}
_DAILY_SUMMARY_GOALS = {
    "step_goal": ("dailyStepGoal",),
    "floors_goal": ("userFloorsAscendedGoal", "floorsAscendedGoal"),
    "intensity_goal_min": ("intensityMinutesGoal",),
}


def _summary_number(value: Any) -> int | float | None:
    """A non-negative number, whole values as int; None for bools, negatives, null and non-numbers."""
    number = _in_range(value, 0, 10_000_000)
    if isinstance(number, float):
        return int(number) if number.is_integer() else round(number, 1)
    return number


def daily_summary_day(day: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Garmin's daily activity summary: steps, distance, floors, intensity minutes, calories and their goals.

    Floors are rounded to a whole number. None when no activity value is present (goals alone mean the device was
    not worn); odd payloads never raise.
    """
    if not isinstance(payload, dict):
        return None
    values = {name: _summary_number(payload.get(key)) for name, key in _DAILY_SUMMARY_FIELDS.items()}
    if all(v is None for v in values.values()):
        return None
    if values["floors_climbed"] is not None:
        values["floors_climbed"] = round(values["floors_climbed"])
    goals = {
        name: next((n for n in map(_summary_number, map(payload.get, keys)) if n is not None), None)
        for name, keys in _DAILY_SUMMARY_GOALS.items()
    }
    date = payload.get("calendarDate")
    return _clean({"date": date if isinstance(date, str) and date else day, **values, **goals})
