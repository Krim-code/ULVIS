# pages/bitrix.py
import logging, requests
from django.conf import settings

log = logging.getLogger(__name__)

def normalize_phone_ru(phone: str) -> str:
    import re
    d = re.sub(r"\D+", "", phone or "")
    if d.startswith("8"): d = "7" + d[1:]
    if not d.startswith("7"): d = "7" + d
    return f"+{d}" if d else ""

def send_lead_to_bitrix(*, name: str, phone: str, message: str = "",
                        utm: dict | None = None, source: str = "", referer: str = "") -> tuple[bool, str]:
    """
    Шлёт crm.lead.add через вебхук. Возвращает (ok, err_msg)
    """
    base = settings.BITRIX_WEBHOOK_URL
    if not base:
        return False, "BITRIX_WEBHOOK_URL is empty"
    url = f"{base}/crm.lead.add.json"
    payload = {
        "fields": {
            "TITLE": f"ULVIS заявка: {name or phone}",
            "NAME": name or "Без имени",
            "PHONE": [{"VALUE": normalize_phone_ru(phone), "VALUE_TYPE": "WORK"}],
            "COMMENTS": (message or "")[:4000],
            "SOURCE_ID": settings.BITRIX_DEFAULT_SOURCE_ID or "WEB",
            "SOURCE_DESCRIPTION": source or "site",
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }

    # кастомные поля, utm, назначение
    if settings.BITRIX_ASSIGNED_BY_ID:
        payload["fields"]["ASSIGNED_BY_ID"] = settings.BITRIX_ASSIGNED_BY_ID
    if settings.BITRIX_PIPELINE_ID:
        payload["fields"]["CATEGORY_ID"] = settings.BITRIX_PIPELINE_ID

    utm = utm or {}
    for k in ("utm_source","utm_medium","utm_campaign","utm_content","utm_term"):
        if utm.get(k):
            payload["fields"][k.upper()] = utm[k]

    try:
        r = requests.post(url, json=payload, timeout=4.0)
        data = r.json()
        if r.ok and data.get("result"):
            return True, ""
        err = (data.get("error_description")
               or data.get("error")
               or f"HTTP {r.status_code}")
        log.warning("Bitrix lead failed: %s", err)
        return False, str(err)
    except Exception as e:
        log.exception("Bitrix lead exception")
        return False, str(e)
