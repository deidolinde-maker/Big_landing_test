from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from config.loader import available_providers, load_site_configs
from config.schema import derive_site_id

URL_FILE_BY_BRAND: dict[str, str] = {
    "mts": "mts.txt",
    "beeline": "beeline.txt",
    "megafon": "megafon.txt",
    "t2": "t2.txt",
    "rostelecom": "rostelecom.txt",
    "domru": "domru.txt",
    "ttk": "ttk.txt",
}


def available_url_brands() -> list[str]:
    return sorted(URL_FILE_BY_BRAND.keys())


def _resolve_urls_dir(urls_dir: str | Path | None = None) -> Path:
    if urls_dir is not None:
        return Path(urls_dir).resolve()
    return (Path(__file__).resolve().parent.parent / "urls").resolve()


def _normalize_url(raw: str) -> str | None:
    line = (raw or "").strip()
    if not line or line.startswith("#"):
        return None

    parsed = urlsplit(line)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Некорректный URL в файле: {line!r}")
    return line


def load_urls_for_brand(brand: str, *, urls_dir: str | Path | None = None) -> list[str]:
    brand_key = (brand or "").strip().lower()
    if brand_key not in URL_FILE_BY_BRAND:
        raise ValueError(
            f"Неизвестный бренд {brand!r}. Доступно: {', '.join(available_url_brands())}"
        )

    root = _resolve_urls_dir(urls_dir)
    file_name = URL_FILE_BY_BRAND[brand_key]
    file_path = root / file_name
    if not file_path.exists():
        raise ValueError(f"Файл URL не найден: {file_path}")

    urls: list[str] = []
    seen: set[str] = set()
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        normalized = _normalize_url(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)

    if not urls:
        raise ValueError(f"Файл URL пустой после фильтрации комментариев: {file_path}")

    return urls


def build_site_configs_from_urls(
    *,
    brand: str,
    urls_dir: str | Path | None = None,
) -> dict[str, dict]:
    """
    Строит runtime-конфиг для прямого обхода URL.

    Источник полей поведения формы (has_checkaddress/has_business/...) берётся
    из provider-конфига по домену, а base_url заменяется на конкретный URL
    страницы из urls/<brand>.txt.
    """
    brand_key = (brand or "").strip().lower()
    if brand_key not in available_providers():
        raise ValueError(
            f"Бренд {brand!r} отсутствует в provider-конфигах. "
            f"Доступно: {', '.join(available_providers())}"
        )

    source_urls = load_urls_for_brand(brand_key, urls_dir=urls_dir)
    provider_sites = load_site_configs(provider=brand_key)

    by_host: dict[str, dict] = {}
    for _, cfg in provider_sites.items():
        host_id = derive_site_id(cfg["base_url"])
        by_host[host_id] = cfg

    built: dict[str, dict] = {}
    for page_url in source_urls:
        host_id = derive_site_id(page_url)
        source_cfg = by_host.get(host_id)
        if source_cfg is None:
            raise ValueError(
                f"Для URL {page_url!r} не найден провайдерный базовый конфиг по домену {host_id!r}."
            )

        cfg_copy = dict(source_cfg)
        cfg_copy["base_url"] = page_url
        cfg_copy["_provider"] = brand_key
        cfg_copy["_site_id"] = host_id
        cfg_copy["_source_mode"] = "url_file"

        built[page_url] = cfg_copy

    return built

