import json
import os
import sqlite3
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from MyQtApp.config import DB_PATH, IMAGES_DIR, IMAGES_WEBP_DIR, normalize_lang_code
from MyQtApp.app.getImgs import _clean_card_filename, download_card_webp


def _scan_local_images(images_dir: str, images_webp_dir: str) -> tuple[dict[str, set[str]], set[str]]:
    """
    Escanea assets/images y assets/images_webp retornando:
    - files_by_lang: {lang_code -> set(filenames_lower)}
    - root_files: set(filenames_lower) en raíz sin subcarpeta de idioma
    """
    files_by_lang = defaultdict(set)
    root_files = set()
    valid_exts = (".webp", ".png", ".jpg", ".jpeg")

    for base_dir in (images_dir, images_webp_dir):
        if not base_dir or not os.path.exists(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            rel_dir = os.path.relpath(root, base_dir).replace("\\", "/").lower()
            is_root = rel_dir in (".", "")
            lang_folder = rel_dir.split("/")[0] if not is_root else None
            for fname in files:
                fl = fname.lower()
                if not fl.endswith(valid_exts):
                    continue
                if is_root:
                    root_files.add(fl)
                else:
                    files_by_lang[lang_folder].add(fl)

    return files_by_lang, root_files


def analyze_missing_images(
    db_path: str = DB_PATH,
    images_dir: str = IMAGES_DIR,
    images_webp_dir: str = IMAGES_WEBP_DIR,
    top_n: int = 15,
) -> dict:
    """
    Algoritmo de análisis que cruza la tabla Cartas (95k+ registros) contra
    las imágenes locales (.webp/.png) para detectar exactamente qué Pokémon,
    sets e idiomas carecen de imagen para mostrarse en PokeBinder.
    """
    files_by_lang, root_files = _scan_local_images(images_dir, images_webp_dir)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id_api, idioma, nombre, set_id, number FROM Cartas")
    rows = cur.fetchall()
    conn.close()

    by_language = {}
    missing_records = defaultdict(list)  # lang -> list of dicts
    missing_pokemon_by_lang = defaultdict(Counter)
    missing_sets_by_lang = defaultdict(Counter)
    total_per_lang = Counter()
    present_per_lang = Counter()

    exts = (".webp", ".png", ".jpg")

    for id_api, idioma, nombre, set_id, number in rows:
        lang = normalize_lang_code(idioma or "en")
        total_per_lang[lang] += 1

        clean_id = str(id_api or "").lower()
        clean_name = _clean_card_filename(nombre or "")
        raw_name = str(nombre or "").lower().replace(" ", "_")

        lang_set = files_by_lang.get(lang, set())
        found = False
        for name_cand in (clean_name, raw_name):
            for ext in exts:
                fname = f"{name_cand}_{clean_id}{ext}"
                if fname in lang_set or (lang == "en" and fname in root_files):
                    found = True
                    break
            if found:
                break

        if found:
            present_per_lang[lang] += 1
        else:
            missing_pokemon_by_lang[lang][nombre or "Desconocido"] += 1
            missing_sets_by_lang[lang][set_id or "N/A"] += 1
            missing_records[lang].append({
                "id_api": id_api,
                "idioma": lang,
                "nombre": nombre,
                "set_id": set_id,
                "number": number,
            })

    total_db = sum(total_per_lang.values())
    total_present = sum(present_per_lang.values())
    total_missing = total_db - total_present

    for lang in sorted(total_per_lang.keys()):
        tot = total_per_lang[lang]
        pres = present_per_lang[lang]
        miss = tot - pres
        pct = round((pres / tot) * 100.0, 2) if tot else 0.0
        by_language[lang] = {
            "total": tot,
            "present": pres,
            "missing": miss,
            "coverage_pct": pct,
            "top_missing_pokemon": [
                {"nombre": k, "faltantes": v}
                for k, v in missing_pokemon_by_lang[lang].most_common(top_n)
            ],
            "top_missing_sets": [
                {"set_id": k, "faltantes": v}
                for k, v in missing_sets_by_lang[lang].most_common(top_n)
            ],
        }

    return {
        "summary": {
            "total_cards": total_db,
            "total_present": total_present,
            "total_missing": total_missing,
            "coverage_pct": round((total_present / total_db) * 100.0, 2) if total_db else 0.0,
        },
        "by_language": by_language,
        "missing_records": dict(missing_records),
    }


def sync_missing_webp_images(
    languages: list[str] = None,
    limit_per_lang: int = None,
    max_workers: int = 10,
    progress_callback=None,
) -> dict:
    """
    Descarga en paralelo las imágenes .webp faltantes detectadas por el algoritmo
    de análisis usando la cascada multi-API (TCGdex nativo -> TCGdex EN -> pokemontcg.io).
    """
    report = analyze_missing_images()
    missing_map = report["missing_records"]
    target_langs = languages or sorted(missing_map.keys())

    stats = {}
    for lang in target_langs:
        lang_code = normalize_lang_code(lang)
        items = missing_map.get(lang_code, [])
        if limit_per_lang:
            items = items[:limit_per_lang]

        downloaded = 0
        failed = 0
        total = len(items)

        if total == 0:
            stats[lang_code] = {"requested": 0, "downloaded": 0, "failed": 0}
            continue

        def _task(rec):
            return download_card_webp(
                rec["id_api"],
                nombre_archivo=rec["nombre"],
                idioma=lang_code,
                set_id=rec.get("set_id"),
                number=rec.get("number"),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_task, rec) for rec in items]
            for idx, fut in enumerate(as_completed(futures), start=1):
                try:
                    res = fut.result()
                    if res:
                        downloaded += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
                if progress_callback:
                    progress_callback(lang_code, idx, total, downloaded)

        stats[lang_code] = {
            "requested": total,
            "downloaded": downloaded,
            "failed": failed,
        }

    return stats


def export_analysis_report(output_json_path: str) -> dict:
    """Ejecuta el análisis completo y guarda un resumen JSON (sin volcar los 75k registros crudos)."""
    report = analyze_missing_images()
    clean_report = {
        "summary": report["summary"],
        "by_language": report["by_language"],
    }
    os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(clean_report, f, indent=2, ensure_ascii=False)
    return clean_report
