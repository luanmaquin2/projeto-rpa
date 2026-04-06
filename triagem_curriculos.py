"""
╔══════════════════════════════════════════════════════════════╗
║        ROBÔ DE TRIAGEM DE CURRÍCULOS — BotCity + pypdf       ║
║  Lê PDFs → Filtra por palavras-chave → Classifica candidatos ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pdfplumber                      # extração de texto dos PDFs
from botcity.core import DesktopBot    # orquestração / automação desktop


# ══════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURAÇÕES — EDITE AQUI
# ══════════════════════════════════════════════════════════════

# Pasta onde estão os currículos em PDF
PASTA_CURRICULOS = Path("curriculos")

# Pasta de saída dos relatórios
PASTA_SAIDA = Path("triagem_saida")

# ── Palavras-chave por categoria (ajuste à vaga que você precisa) ──
KEYWORDS = {
    "hard_skills": [
        "python", "java", "javascript", "sql", "machine learning",
        "power bi", "excel avançado", "aws", "docker", "react",
        "django", "fastapi", "git", "api rest",
    ],
    "soft_skills": [
        "liderança", "comunicação", "proatividade", "trabalho em equipe",
        "gestão de projetos", "resolução de problemas", "adaptabilidade",
    ],
    "formacao": [
        "ciência da computação", "sistemas de informação", "engenharia",
        "análise de sistemas", "tecnologia da informação", "ti",
        "bacharel", "licenciatura", "mba", "pós-graduação",
    ],
    "experiencia": [
        "anos de experiência", "sênior", "pleno", "júnior",
        "estágio", "trainee", "coordenador", "gerente", "analista",
    ],
    "idiomas": [
        "inglês", "espanhol", "inglês avançado", "inglês fluente",
        "bilíngue", "francês",
    ],
}

# Pontuação mínima para aprovação (0 a 100)
PONTUACAO_MINIMA = 40

# Pesos por categoria (devem somar 100)
PESOS = {
    "hard_skills":  40,
    "soft_skills":  20,
    "formacao":     20,
    "experiencia":  10,
    "idiomas":      10,
}


# ══════════════════════════════════════════════════════════════
#  🔧  FUNÇÕES AUXILIARES
# ══════════════════════════════════════════════════════════════

def normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para comparação robusta."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


def extrair_texto_pdf(caminho_pdf: Path) -> str:
    """Extrai todo o texto de um PDF usando pdfplumber."""
    texto_total = []
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto_total.append(t)
    except Exception as e:
        print(f"    [AVISO] Erro ao ler {caminho_pdf.name}: {e}")
    return "\n".join(texto_total)


def extrair_email(texto: str) -> str:
    """Tenta capturar o e-mail do candidato no texto."""
    match = re.search(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}", texto)
    return match.group(0) if match else "não encontrado"


def extrair_telefone(texto: str) -> str:
    """Tenta capturar um número de telefone no texto."""
    match = re.search(r"(\(?\d{2}\)?\s?\d{4,5}[-.\s]?\d{4})", texto)
    return match.group(0).strip() if match else "não encontrado"


def calcular_pontuacao(texto: str) -> tuple[float, dict]:
    """
    Verifica quais palavras-chave aparecem no texto e calcula
    uma pontuação ponderada de 0 a 100.

    Retorna: (pontuacao_final, detalhes_por_categoria)
    """
    texto_norm = normalizar(texto)
    detalhes = {}
    pontuacao_final = 0.0

    for categoria, keywords in KEYWORDS.items():
        encontradas = [kw for kw in keywords if normalizar(kw) in texto_norm]
        total = len(keywords)
        acertos = len(encontradas)
        pct = acertos / total if total > 0 else 0
        peso = PESOS.get(categoria, 0)
        contribuicao = pct * peso

        detalhes[categoria] = {
            "encontradas": encontradas,
            "acertos": acertos,
            "total": total,
            "contribuicao": round(contribuicao, 2),
        }
        pontuacao_final += contribuicao

    return round(pontuacao_final, 2), detalhes


def classificar(pontuacao: float) -> str:
    """Retorna o status de aprovação com base na pontuação."""
    if pontuacao >= 70:
        return "✅ APROVADO — Alta Aderência"
    elif pontuacao >= PONTUACAO_MINIMA:
        return "🟡 APROVADO — Aderência Média"
    else:
        return "❌ REPROVADO — Baixa Aderência"


def salvar_csv(resultados: list[dict], caminho: Path):
    """Salva todos os resultados num arquivo CSV."""
    if not resultados:
        return
    campos = list(resultados[0].keys())
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)
    print(f"\n📄 Relatório CSV salvo em: {caminho}")


def salvar_relatorio_txt(resultados: list[dict], caminho: Path):
    """Gera um relatório detalhado em texto."""
    aprovados   = [r for r in resultados if "APROVADO" in r["status"]]
    reprovados  = [r for r in resultados if "REPROVADO" in r["status"]]

    linhas = [
        "=" * 60,
        "   RELATÓRIO DE TRIAGEM DE CURRÍCULOS",
        f"   Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "=" * 60,
        f"\nTotal analisados : {len(resultados)}",
        f"Aprovados        : {len(aprovados)}",
        f"Reprovados       : {len(reprovados)}",
        f"Pontuação mínima : {PONTUACAO_MINIMA}",
        "\n" + "─" * 60,
        "RANKING DOS APROVADOS",
        "─" * 60,
    ]

    for i, r in enumerate(sorted(aprovados, key=lambda x: x["pontuacao"], reverse=True), 1):
        linhas.append(
            f"{i:>2}. {r['arquivo']:<35} "
            f"Pontuação: {r['pontuacao']:>5.1f}  |  {r['status']}"
        )

    linhas += ["\n" + "─" * 60, "REPROVADOS", "─" * 60]
    for r in sorted(reprovados, key=lambda x: x["pontuacao"], reverse=True):
        linhas.append(
            f"   {r['arquivo']:<35} "
            f"Pontuação: {r['pontuacao']:>5.1f}  |  {r['status']}"
        )

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"📋 Relatório TXT salvo em: {caminho}")


# ══════════════════════════════════════════════════════════════
#  🤖  ROBÔ PRINCIPAL (BotCity)
# ══════════════════════════════════════════════════════════════

def main():
    bot = DesktopBot()
    resultados: list[dict] = []

    # ── Cria estrutura de pastas ───────────────────────────────
    PASTA_CURRICULOS.mkdir(exist_ok=True)
    PASTA_SAIDA.mkdir(exist_ok=True)

    # ── Localiza todos os PDFs ─────────────────────────────────
    pdfs = sorted(PASTA_CURRICULOS.glob("*.pdf"))

    if not pdfs:
        print(f"[AVISO] Nenhum PDF encontrado em '{PASTA_CURRICULOS}/'.")
        print("        Coloque os currículos em PDF nessa pasta e execute novamente.")
        return

    print(f"\n🔍 {len(pdfs)} currículo(s) encontrado(s). Iniciando triagem...\n")
    print(f"{'ARQUIVO':<40} {'PONTUAÇÃO':>10}  STATUS")
    print("─" * 75)

    for pdf in pdfs:
        # 1. Extrai texto
        texto = extrair_texto_pdf(pdf)

        if not texto.strip():
            print(f"  {pdf.name:<38} [SEM TEXTO — PDF ESCANEADO]")
            continue

        # 2. Calcula pontuação
        pontuacao, detalhes = calcular_pontuacao(texto)

        # 3. Classifica
        status = classificar(pontuacao)

        # 4. Extrai informações de contato
        email    = extrair_email(texto)
        telefone = extrair_telefone(texto)

        # 5. Monta registro
        registro = {
            "arquivo":    pdf.name,
            "pontuacao":  pontuacao,
            "status":     status,
            "email":      email,
            "telefone":   telefone,
            # keywords encontradas por categoria
            **{
                f"kw_{cat}": ", ".join(d["encontradas"]) or "—"
                for cat, d in detalhes.items()
            },
            **{
                f"score_{cat}": d["contribuicao"]
                for cat, d in detalhes.items()
            },
        }
        resultados.append(registro)

        print(f"  {pdf.name:<38} {pontuacao:>8.1f}/100  {status}")

    if not resultados:
        print("\n[INFO] Nenhum resultado gerado.")
        return

    # ── Salva relatórios ───────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    salvar_csv(resultados, PASTA_SAIDA / f"triagem_{ts}.csv")
    salvar_relatorio_txt(resultados, PASTA_SAIDA / f"relatorio_{ts}.txt")

    # ── Resumo final ───────────────────────────────────────────
    aprovados = [r for r in resultados if "APROVADO" in r["status"]]
    print(f"\n{'═'*50}")
    print(f"  ✅  Aprovados : {len(aprovados)}/{len(resultados)}")
    print(f"  📁  Saída     : {PASTA_SAIDA.resolve()}")
    print(f"{'═'*50}\n")


# ══════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
