from __future__ import annotations

from typing import Any

from backend.features import PM25_LABELS, category_payload


ACTIVITY_PROFILES: dict[str, dict[str, Any]] = {
    "light": {"label_vi": "Nhẹ", "factor": 1.0},
    "moderate": {"label_vi": "Vừa", "factor": 1.5},
    "intense": {"label_vi": "Cường độ cao", "factor": 2.2},
}

GROUP_LABELS = {
    "general": "Người trưởng thành khỏe mạnh",
    "sensitive": "Nhóm nhạy cảm",
}


def _risk_rank(value: float) -> int:
    key = category_payload(value)["category"]
    return PM25_LABELS.index(key)


def _relative_load(concentration: float, duration_minutes: int, activity_factor: float) -> float:
    """Concentration-time score; this is not an inhaled-dose estimate."""
    return round(concentration * (duration_minutes / 60.0) * activity_factor, 1)


def _timing_decision(
    current_pm25: float,
    forecast_pm25: float,
    forecast_lower: float,
    forecast_upper: float,
) -> tuple[str, str, list[str]]:
    change_pct = ((forecast_pm25 - current_pm25) / max(current_pm25, 1.0)) * 100.0
    lower_rank = _risk_rank(forecast_lower)
    upper_rank = _risk_rank(forecast_upper)
    band_span = upper_rank - lower_rank

    if forecast_upper < current_pm25:
        return (
            "after_24h",
            "high",
            [
                "Toàn bộ khoảng dự báo 90% thấp hơn mức PM2.5 hiện tại.",
                f"Trung tâm dự báo thay đổi {change_pct:+.0f}% so với hiện tại.",
            ],
        )
    if forecast_lower > current_pm25:
        return (
            "now",
            "high",
            [
                "Toàn bộ khoảng dự báo 90% cao hơn mức PM2.5 hiện tại.",
                f"Trung tâm dự báo thay đổi {change_pct:+.0f}% so với hiện tại.",
            ],
        )

    if abs(change_pct) >= 15.0 and band_span <= 2:
        preferred = "after_24h" if forecast_pm25 < current_pm25 else "now"
        return (
            preferred,
            "medium",
            [
                f"Trung tâm dự báo thay đổi {change_pct:+.0f}% so với hiện tại.",
                "Khoảng dự báo vẫn chồng lên mức hiện tại, nên lựa chọn này chưa hoàn toàn chắc chắn.",
            ],
        )

    return (
        "flexible",
        "low",
        [
            "Khoảng dự báo chồng lên mức hiện tại và chưa cho thấy thời điểm vượt trội rõ ràng.",
            f"Khoảng 90% đi qua {band_span + 1} dải tham chiếu PM2.5.",
        ],
    )


def _action_plan(
    decision_value: float,
    group: str,
    activity: str,
    duration_minutes: int,
) -> tuple[int, str]:
    rank = _risk_rank(decision_value)
    sensitive = group == "sensitive"
    ratios_general = [1.0, 1.0, 0.75, 0.5, 0.25, 0.0]
    ratios_sensitive = [1.0, 0.75, 0.5, 0.25, 0.0, 0.0]
    ratio = (ratios_sensitive if sensitive else ratios_general)[rank]
    if activity == "intense" and rank >= 1:
        ratio *= 0.75
    suggested = int((duration_minutes * ratio) // 5 * 5)

    if suggested <= 0:
        action = "Nên hoãn hoạt động ngoài trời hoặc chuyển sang không gian trong nhà có không khí sạch hơn."
    elif suggested < duration_minutes:
        action = (
            f"Giảm thời lượng xuống khoảng {suggested} phút và ưu tiên cường độ nhẹ hơn; "
            "dừng lại nếu xuất hiện triệu chứng bất thường."
        )
    else:
        action = "Có thể giữ kế hoạch, đồng thời theo dõi cập nhật PM2.5 trước khi bắt đầu."
    return suggested, action


def build_activity_plan(
    *,
    city: str,
    horizon_hours: int = 24,
    current_pm25: float,
    forecast_pm25: float,
    forecast_lower: float,
    forecast_upper: float,
    group: str,
    activity: str,
    duration_minutes: int,
) -> dict[str, Any]:
    if not 1 <= int(horizon_hours) <= 24:
        raise ValueError("Horizon must be between 1 and 24 hours.")
    if group not in GROUP_LABELS:
        raise ValueError(f"Unsupported health group: {group}")
    if activity not in ACTIVITY_PROFILES:
        raise ValueError(f"Unsupported activity: {activity}")
    if not 0.0 <= forecast_lower <= forecast_pm25 <= forecast_upper:
        raise ValueError("Forecast interval must satisfy lower <= prediction <= upper.")

    activity_profile = ACTIVITY_PROFILES[activity]
    factor = float(activity_profile["factor"])
    timing, confidence, reasons = _timing_decision(
        current_pm25,
        forecast_pm25,
        forecast_lower,
        forecast_upper,
    )

    if timing == "now":
        decision_value = current_pm25
    elif timing == "after_24h":
        decision_value = forecast_upper
    else:
        decision_value = max(current_pm25, forecast_upper)

    suggested_duration, action = _action_plan(
        decision_value,
        group,
        activity,
        duration_minutes,
    )
    current_load = _relative_load(current_pm25, duration_minutes, factor)
    forecast_load = _relative_load(forecast_pm25, duration_minutes, factor)
    reduction = None
    if timing == "now" and forecast_load > 0:
        reduction = round((forecast_load - current_load) / forecast_load * 100.0, 1)
    elif timing == "after_24h" and current_load > 0:
        reduction = round((current_load - forecast_load) / current_load * 100.0, 1)

    timing_labels = {
        "now": "Ưu tiên thời điểm hiện tại",
        "after_24h": f"Cân nhắc sau {horizon_hours} giờ",
        "flexible": "Chưa có thời điểm vượt trội",
    }
    confidence_labels = {
        "high": "Độ chắc chắn cao",
        "medium": "Độ chắc chắn vừa",
        "low": "Độ chắc chắn thấp",
    }

    reasons.append(
        f"Hồ sơ: {GROUP_LABELS[group]}, hoạt động {activity_profile['label_vi'].lower()} trong {duration_minutes} phút."
    )
    return {
        "city": city,
        "horizon_hours": int(horizon_hours),
        "timing": timing,
        "timing_label": timing_labels[timing],
        "confidence": confidence,
        "confidence_label": confidence_labels[confidence],
        "group": {"key": group, "label_vi": GROUP_LABELS[group]},
        "activity": {
            "key": activity,
            "label_vi": activity_profile["label_vi"],
            "relative_intensity_factor": factor,
        },
        "duration_minutes": duration_minutes,
        "suggested_duration_minutes": suggested_duration,
        "action": action,
        "reasons": reasons,
        "expected_load_reduction_pct": reduction,
        "options": {
            "now": {
                "pm25": round(current_pm25, 1),
                "category": category_payload(current_pm25),
                "relative_exposure_load": current_load,
            },
            "after_24h": {
                "pm25": round(forecast_pm25, 1),
                "lower": round(forecast_lower, 1),
                "upper": round(forecast_upper, 1),
                "category": category_payload(forecast_pm25),
                "conservative_category": category_payload(forecast_upper),
                "relative_exposure_load": forecast_load,
                "relative_exposure_load_lower": _relative_load(forecast_lower, duration_minutes, factor),
                "relative_exposure_load_upper": _relative_load(forecast_upper, duration_minutes, factor),
            },
        },
        "method": {
            "name": "uncertainty_aware_activity_planner_v1",
            "load_definition": "PM2.5 concentration x duration in hours x relative activity intensity",
            "decision_basis": (
                f"Current PM2.5 versus the city-and-horizon-conditioned 90% conformal "
                f"forecast interval at t+{horizon_hours}"
            ),
            "limitations": (
                "Công cụ hỗ trợ lập kế hoạch, không phải ước tính liều hít vào, chẩn đoán y khoa "
                "hoặc khuyến cáo của cơ quan quản lý."
            ),
        },
    }
