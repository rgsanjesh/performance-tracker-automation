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
        url  = r["url"]
        link = f'<a href="{url}">{name}</a>'

        for device, cwv in (("mWeb", r["mobile"]), ("dWeb", r["desktop"])):
            if cwv is None:
                continue
            for metric in ("lcp", "inp", "cls"):
                curr = cwv.get(metric)
                prev = cwv.get(f"prev_{metric}")
                tag  = f"🔴 <b>[{device}]</b> {link} — {metric.upper()} <b>{_fmt(curr, metric)}</b>"

                if _is_poor(curr, metric):
                    danger.append(f"{tag}  <i>(limit: {_fmt(_POOR[metric], metric)})</i>")
                elif _is_regressing(curr, prev, metric):
                    delta = (
                        f"+{round(curr - prev, 2)}"
                        if metric == "cls"
                        else f"+{round((curr / prev - 1) * 100)}%"
                    )
                    regressing.append(
                        f"⚠️ <b>[{device}]</b> {link} — {metric.upper()} <b>{_fmt(curr, metric)}</b>"
                        f"  <i>(was {_fmt(prev, metric)}, {delta})</i>"
                    )

    sections: list[dict] = []

    if danger:
        sections.append({
            "header": "🚨  DANGER — Poor Scores (Act Now)",
            "widgets": [{"textParagraph": {"text": "<br>".join(danger)}}],
        })

    if regressing:
        sections.append({
            "header": "📉  Regressing vs Last Week",
            "widgets": [{"textParagraph": {"text": "<br>".join(regressing)}}],
        })

    if not danger and not regressing:
        sections.append({
            "widgets": [{"textParagraph": {
                "text": "✅  <b>All pages are within good thresholds. No regressions vs last week.</b>"
            }}],
        })

    payload = {
        "cards": [{
            "header": {
                "title":    f"📊  CWV Report — {label}",
                "subtitle": "Core Web Vitals · pharmeasy.in",
            },
            "sections": sections,
        }]
    }

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print("Google Chat notification sent.")
