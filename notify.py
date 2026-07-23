import os
import requests

_POOR = {"lcp": 4.0, "inp": 500, "cls": 0.25}


def _is_poor(val, metric: str) -> bool:
    if not isinstance(val, (int, float)):
        return False
    return val > _POOR[metric]


def _is_regressing(curr, prev, metric: str) -> bool:
    if not isinstance(curr, (int, float)) or not isinstance(prev, (int, float)):
        return False
    if metric == "cls":
        return curr > prev + 0.02
    return curr > prev * 1.10


def _fmt(val, metric: str) -> str:
    if not isinstance(val, (int, float)):
        return "N/A"
    if metric == "lcp":
        return f"{val}s"
    if metric == "inp":
        return f"{int(val)}ms"
    return str(val)


def send_report(label: str, results: list[dict]) -> None:
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK")
    if not webhook_url:
        print("GOOGLE_CHAT_WEBHOOK not set — skipping notification")
        return

    danger: list[str] = []
    regressing: list[str] = []

    for r in results:
        name = r["name"]
        for device, cwv in (("mWeb", r["mobile"]), ("dWeb", r["desktop"])):
            if cwv is None:
                continue
            for metric in ("lcp", "inp", "cls"):
                curr = cwv.get(metric)
                prev = cwv.get(f"prev_{metric}")
                tag = f"[{device}] {name} — {metric.upper()} {_fmt(curr, metric)}"
                if _is_poor(curr, metric):
                    danger.append(f"{tag}  (limit: {_fmt(_POOR[metric], metric)})")
                elif _is_regressing(curr, prev, metric):
                    if metric == "cls":
                        delta = f"+{round(curr - prev, 2)}"
                    else:
                        delta = f"+{round((curr / prev - 1) * 100)}%"
                    regressing.append(f"{tag}  (was {_fmt(prev, metric)}, {delta})")

    lines = [f"*CWV Report — {label}*", ""]

    if danger:
        lines.append("DANGER (poor — act now):")
        lines += [f"  • {d}" for d in danger]
    else:
        lines.append("No poor scores this week.")

    lines.append("")

    if regressing:
        lines.append("REGRESSING vs last week:")
        lines += [f"  • {r}" for r in regressing]
    else:
        lines.append("No regressions vs last week.")

    resp = requests.post(webhook_url, json={"text": "\n".join(lines)}, timeout=10)
    resp.raise_for_status()
    print("Google Chat notification sent.")
