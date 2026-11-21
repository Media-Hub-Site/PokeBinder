"""
Algoritmo de análisis y sincronización de imágenes faltantes (.webp) para PokeBinder.

Uso:
  python scripts/analyze_missing_images.py
  python scripts/analyze_missing_images.py --export scripts/missing_images_report.json
  python scripts/analyze_missing_images.py --download --lang es --limit 200
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from MyQtApp.app.image_analyzer import (
    analyze_missing_images,
    export_analysis_report,
    sync_missing_webp_images,
)


def main():
    parser = argparse.ArgumentParser(description="Analiza y descarga imágenes .webp faltantes de PokeBinder.")
    parser.add_argument("--export", type=str, default=None, help="Ruta JSON para exportar el reporte de análisis.")
    parser.add_argument("--download", action="store_true", help="Descargar imágenes .webp faltantes vía multi-API.")
    parser.add_argument("--lang", nargs="+", default=None, help="Idiomas a procesar (ej: es en fr pt ja zh).")
    parser.add_argument("--limit", type=int, default=100, help="Límite máximo de descargas por idioma.")
    parser.add_argument("--workers", type=int, default=10, help="Hilos paralelos de descarga.")
    args = parser.parse_args()

    print("Ejecutando análisis de cobertura de imágenes en PokeDatabase.db...")
    report = analyze_missing_images()
    summary = report["summary"]

    print(
        f"\nResumen Global: {summary['total_present']:,} / {summary['total_cards']:,} "
        f"cartas con imagen local ({summary['coverage_pct']}% cobertura, {summary['total_missing']:,} faltantes)\n"
    )
    print(f"{'Idioma':<8} | {'Total BD':>9} | {'Locales':>9} | {'Faltantes':>9} | {'Cobertura':>9}")
    print("-" * 58)
    for lang, info in report["by_language"].items():
        print(
            f"{lang:<8} | {info['total']:>9,} | {info['present']:>9,} | "
            f"{info['missing']:>9,} | {info['coverage_pct']:>8.2f}%"
        )
        top_pokes = ", ".join(f"{p['nombre']} ({p['faltantes']})" for p in info["top_missing_pokemon"][:5])
        top_sets = ", ".join(f"{s['set_id']} ({s['faltantes']})" for s in info["top_missing_sets"][:5])
        print(f"   Top Pokémon sin imagen: {top_pokes}")
        print(f"   Top Sets sin imagen:    {top_sets}")

    if args.export:
        export_analysis_report(args.export)
        print(f"\nReporte exportado en: {args.export}")

    if args.download:
        print(f"\nIniciando descarga .webp multi-API (límite {args.limit}/idioma, {args.workers} hilos)...")

        def on_prog(lang_code, idx, total, downloaded):
            if idx % 20 == 0 or idx == total:
                print(f"  [{lang_code}] {idx}/{total} procesadas ({downloaded} descargadas)")

        stats = sync_missing_webp_images(
            languages=args.lang,
            limit_per_lang=args.limit,
            max_workers=args.workers,
            progress_callback=on_prog,
        )
        print("\nResultado de sincronización:")
        for lang_code, st in stats.items():
            print(f"  {lang_code}: {st['downloaded']}/{st['requested']} descargadas ({st['failed']} sin escaneo disponible)")


if __name__ == "__main__":
    main()
