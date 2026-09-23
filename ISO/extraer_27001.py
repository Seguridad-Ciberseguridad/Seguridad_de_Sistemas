import pdfplumber
import os

PDF_PATH = os.path.join(os.path.dirname(__file__), "norma-iso-27001-2022-es.pdf")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "norma-iso-27001-2022-es.txt")


def extraer_contenido(pdf_path, output_path):
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Total de paginas: {total}")
        with open(output_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(pdf.pages, start=1):
                texto = page.extract_text()
                if texto:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"PAGINA {i}/{total}\n")
                    f.write(f"{'='*60}\n")
                    f.write(texto)
                print(f"Procesando pagina {i}/{total}...", end="\r")
    print(f"\nListo: {output_path}")


if __name__ == "__main__":
    extraer_contenido(PDF_PATH, OUTPUT_PATH)
