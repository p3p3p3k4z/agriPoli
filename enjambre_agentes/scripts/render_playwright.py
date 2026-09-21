import os
import json
from playwright.sync_api import sync_playwright

def render_mermaid_with_playwright(mermaid_code: str, output_png_path: str):
    """Renderiza codigo Mermaid a PNG de alta resolucion usando Playwright Chromium."""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      background-color: #ffffff;
      margin: 0;
      padding: 30px;
      display: flex;
      justify-content: center;
      align-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .mermaid {{
      width: 100%;
    }}
  </style>
</head>
<body>
  <div class="mermaid">
{mermaid_code}
  </div>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'default',
      flowchart: {{
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'basis'
      }}
    }});
  </script>
</body>
</html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 2400, "height": 3200, "device_scale_factor": 2})
        page.set_content(html_content)
        # Esperar a que el SVG de mermaid se dibuje
        page.wait_for_selector(".mermaid svg", timeout=20000)
        svg_element = page.locator(".mermaid svg")
        png_bytes = svg_element.screenshot(type="png")
        os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)
        with open(output_png_path, "wb") as f:
            f.write(png_bytes)
        browser.close()
        print(f"[OK] Renderizado exitoso con Playwright: {output_png_path} ({len(png_bytes):,} bytes)")
        return output_png_path


def render_multiple_mermaids_with_playwright(items: list[tuple[str, str, str]]) -> list[str]:
    """Renderiza multiples diagramas Mermaid a PNG en una sola sesion de Chromium.

    Args:
        items: Lista de tuplas (codigo_mermaid, ruta_png_salida, etiqueta)

    Returns:
        Lista de rutas de archivos PNG generados con exito.
    """
    generados = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for mermaid_code, output_png_path, etiqueta in items:
            try:
                page = browser.new_page(viewport={"width": 2400, "height": 3200, "device_scale_factor": 2})
                html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      background-color: #ffffff;
      margin: 0;
      padding: 30px;
      display: flex;
      justify-content: center;
      align-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .mermaid {{
      width: 100%;
    }}
  </style>
</head>
<body>
  <div class="mermaid">
{mermaid_code}
  </div>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'default',
      flowchart: {{
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'basis'
      }}
    }});
  </script>
</body>
</html>"""
                page.set_content(html_content)
                page.wait_for_selector(".mermaid svg", timeout=20000)
                svg_element = page.locator(".mermaid svg")
                png_bytes = svg_element.screenshot(type="png")
                os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)
                with open(output_png_path, "wb") as f:
                    f.write(png_bytes)
                page.close()
                generados.append(output_png_path)
                print(f"[OK] Renderizado exitoso ({etiqueta}): {output_png_path} ({len(png_bytes):,} bytes)")
            except Exception as e:
                print(f"[ERROR] Error al renderizar {etiqueta}: {e}")
        browser.close()
    return generados


if __name__ == "__main__":
    from test_render import DIAGRAMA_MERMAID
    render_mermaid_with_playwright(DIAGRAMA_MERMAID, "docs/arquitectura_v3.png")
