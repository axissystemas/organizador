import os
import sys
import shutil
import argparse
from pathlib import Path

# Configurar stdout para aceitar caracteres UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Mapeamento de categorias e suas respectivas extensões
CATEGORIAS = {
    "Documentos": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".epub"],
    "Planilhas_e_Dados": [".xls", ".xlsx", ".csv", ".ods", ".json", ".xml", ".sql", ".parquet"],
    "Apresentacoes": [".ppt", ".pptx", ".odp"],
    "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".psd", ".ai"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
    "Compactados": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Executaveis_e_Instaladores": [".exe", ".msi", ".bat", ".cmd", ".sh", ".ps1"]
}

# Extensões temporárias que devem ser ignoradas (downloads em andamento)
EXTENSOES_IGNORADAS = {".crdownload", ".part", ".tmp", ".download"}

# Arquivos de sistema ou ocultos a ignorar
ARQUIVOS_IGNORADOS = {"desktop.ini", "thumbs.db", ".ds_store"}


def obter_categoria(extensao: str) -> str:
    """Retorna o nome da categoria com base na extensão do arquivo."""
    ext = extensao.lower()
    for categoria, extensoes in CATEGORIAS.items():
        if ext in extensoes:
            return categoria
    return "Outros"


def gerar_nome_unico(destino_pasta: Path, nome_arquivo: str) -> Path:
    """
    Se o arquivo já existir na pasta destino, gera um nome único adicionando um contador.
    Exemplo: relatorio.pdf -> relatorio (1).pdf
    """
    caminho_final = destino_pasta / nome_arquivo
    if not caminho_final.exists():
        return caminho_final

    stem = caminho_final.stem
    suffix = caminho_final.suffix
    contador = 1

    while caminho_final.exists():
        caminho_final = destino_pasta / f"{stem} ({contador}){suffix}"
        contador += 1

    return caminho_final


def organizar_downloads(caminho_downloads: Path, dry_run: bool = False, log_callback=None):
    """
    Percorre a pasta Downloads e organiza os arquivos em subpastas por categoria.
    Dentro da pasta Documentos, divide em subpastas por extensão (PDF, DOCX, TXT, etc.).
    Suporta callback opcional para envio de logs (útil para interfaces gráficas).
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    if not caminho_downloads.exists():
        log(f"[ERRO] A pasta especificada não existe: {caminho_downloads}")
        return {"status": "erro", "mensagem": "Pasta não encontrada", "total_movidos": 0, "ignorados": 0}

    log("=" * 60)
    log(" Organização de Downloads")
    log(f" Pasta Alvo: {caminho_downloads}")
    log(f" Modo Simulação (Dry Run): {'ATIVADO' if dry_run else 'DESATIVADO'}")
    log("=" * 60)

    nomes_categorias = set(CATEGORIAS.keys()) | {"Outros"}
    estatisticas = {cat: 0 for cat in nomes_categorias}
    ignorados = 0

    def processar_item(item: Path, pasta_base: Path):
        nonlocal ignorados

        if item.is_dir():
            return

        if (
            item.name.lower() in ARQUIVOS_IGNORADOS
            or item.name.startswith(".")
            or item.name.startswith("~$")
        ):
            ignorados += 1
            return

        if item.suffix.lower() in EXTENSOES_IGNORADAS:
            log(f"[IGNORADO - EM DOWNLOAD] {item.name}")
            ignorados += 1
            return

        categoria = obter_categoria(item.suffix)

        if categoria == "Documentos":
            ext_subpasta = item.suffix.upper().lstrip(".") or "OUTROS"
            pasta_destino = pasta_base / "Documentos" / ext_subpasta
            rel_path = f"Documentos/{ext_subpasta}"
        else:
            pasta_destino = pasta_base / categoria
            rel_path = categoria

        caminho_destino_final = gerar_nome_unico(pasta_destino, item.name)

        if dry_run:
            log(f"[SIMULACAO] Mover '{item.name}' -> '{rel_path}/{caminho_destino_final.name}'")
        else:
            pasta_destino.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(caminho_destino_final))
            log(f"[MOVIDO] '{item.name}' -> '{rel_path}/{caminho_destino_final.name}'")

        estatisticas[categoria] += 1

    # 1. Processar arquivos na raiz de Downloads
    for item in caminho_downloads.iterdir():
        processar_item(item, caminho_downloads)

    # 2. Processar arquivos soltos já existentes dentro de Downloads/Documentos
    pasta_documentos = caminho_downloads / "Documentos"
    if pasta_documentos.exists() and pasta_documentos.is_dir():
        for item in pasta_documentos.iterdir():
            # Apenas arquivos soltos diretamente na pasta Documentos (não subpastas como PDF, DOCX...)
            if not item.is_dir():
                processar_item(item, caminho_downloads)

    log("\n" + "=" * 60)
    log(" Resumo da Operação:")
    total_movidos = sum(estatisticas.values())
    for cat, qtd in estatisticas.items():
        if qtd > 0:
            log(f"  - {cat}: {qtd} arquivo(s)")
    log(f"\n Total de arquivos {'planejados para mover' if dry_run else 'movidos'}: {total_movidos}")
    log(f" Total de arquivos ignorados: {ignorados}")
    log("=" * 60)

    return {
        "status": "sucesso",
        "dry_run": dry_run,
        "estatisticas": estatisticas,
        "total_movidos": total_movidos,
        "ignorados": ignorados
    }


def main():
    # Detecta automaticamente a pasta Downloads do usuário logado no sistema
    pasta_padrao = Path.home() / "Downloads"

    parser = argparse.ArgumentParser(description="Organiza a pasta Downloads por tipo de arquivo.")
    parser.add_argument(
        "--path",
        type=str,
        default=str(pasta_padrao),
        help=f"Caminho para a pasta a ser organizada (padrão: {pasta_padrao})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa uma simulação sem mover nenhum arquivo de fato"
    )

    args = parser.parse_args()
    pasta_alvo = Path(args.path)

    organizar_downloads(pasta_alvo, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

