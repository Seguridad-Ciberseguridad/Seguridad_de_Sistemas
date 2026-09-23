import pdfplumber
import os

PDF_PATH = os.path.join(os.path.dirname(__file__), "norma-iso-27002-2022-es.pdf")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "norma-iso-27002-2022-es.txt")


def extraer_contenido(pdf_path: str, output_path: str) -> None:
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Total de páginas: {total}")

        with open(output_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(pdf.pages, start=1):
                texto = page.extract_text()
                if texto:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"PÁGINA {i}/{total}\n")
                    f.write(f"{'='*60}\n")
                    f.write(texto)
                print(f"Procesando página {i}/{total}...", end="\r")

    print(f"\nContenido extraído en: {output_path}")


if __name__ == "__main__":
    extraer_contenido(PDF_PATH, OUTPUT_PATH)
