"""
╔══════════════════════════════════════════════════════════════╗
║        ROBÔ DE TRIAGEM DE CURRÍCULOS — BotCity + pypdf       ║
║  Lê PDFs → Filtra por palavras-chave → Classifica candidatos ║
║  Envia e-mail automático para candidatos aprovados           ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import csv
import re
import smtplib
import unicodedata
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pdfplumber                      # extracao de texto dos PDFs
from botcity.core import DesktopBot    # orquestracao / automacao desktop

from dotenv import load_dotenv
import os

load_dotenv()

# ══════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURAÇÕES — EDITE AQUI
# ══════════════════════════════════════════════════════════════

# Pasta onde estão os currículos em PDF
PASTA_CURRICULOS = Path("curriculos")

# Pasta de saída dos relatórios
PASTA_SAIDA = Path("triagem_saida")

# ── Configurações de E-mail ────────────────────────────────────
# Defina as variáveis de ambiente para não expor credenciais:
#   Windows : set EMAIL_REMETENTE=recrutamento@suaempresa.com
#             set EMAIL_SENHA=sua_senha_de_app
#   Linux   : export EMAIL_REMETENTE=recrutamento@suaempresa.com
#             export EMAIL_SENHA=sua_senha_de_app
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA     = os.getenv("EMAIL_SENHA")        # senha de app (Gmail) ou SMTP
SMTP_HOST       = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))

# Dados exibidos no corpo do e-mail
NOME_EMPRESA = "Sua Empresa"
NOME_VAGA    = "Desenvolvedor(a) Python"

# Se True, apenas simula o envio sem conectar ao SMTP (util para testes)
MODO_SIMULACAO = False

# ── Palavras-chave por categoria ───────────────────────────────
KEYWORDS = {
    "hard_skills": [
        "python", "java", "javascript", "sql", "machine learning",
        "power bi", "excel avancado", "aws", "docker", "react",
        "django", "fastapi", "git", "api rest",
    ],
    "soft_skills": [
        "lideranca", "comunicacao", "proatividade", "trabalho em equipe",
        "gestao de projetos", "resolucao de problemas", "adaptabilidade",
    ],
    "formacao": [
        "ciencia da computacao", "sistemas de informacao", "engenharia",
        "analise de sistemas", "tecnologia da informacao", "ti",
        "bacharel", "licenciatura", "mba", "pos-graduacao",
    ],
    "experiencia": [
        "anos de experiencia", "senior", "pleno", "junior",
        "estagio", "trainee", "coordenador", "gerente", "analista",
    ],
    "idiomas": [
        "ingles", "espanhol", "ingles avancado", "ingles fluente",
        "bilingue", "frances",
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


def extrair_nome_candidato(texto: str) -> str:
    """Tenta capturar o nome do candidato na primeira linha do PDF."""
    primeira_linha = texto.strip().splitlines()[0] if texto.strip() else ""
    # Heurística: primeira linha costuma ser o nome (sem @ e sem CEP)
    if primeira_linha and "@" not in primeira_linha and not re.search(r"\d{5}", primeira_linha):
        return primeira_linha.strip()
    return "Candidato(a)"


def extrair_email(texto: str) -> str:
    """Tenta capturar o e-mail do candidato no texto."""
    match = re.search(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}", texto)
    return match.group(0) if match else "nao encontrado"


def extrair_telefone(texto: str) -> str:
    """Tenta capturar um número de telefone no texto."""
    match = re.search(r"(\(?\d{2}\)?\s?\d{4,5}[-.\s]?\d{4})", texto)
    return match.group(0).strip() if match else "nao encontrado"


def calcular_pontuacao(texto: str) -> tuple[float, dict]:
    """
    Verifica quais palavras-chave aparecem no texto e calcula
    uma pontuação ponderada de 0 a 100.
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
        return "APROVADO - Alta Aderencia"
    elif pontuacao >= PONTUACAO_MINIMA:
        return "APROVADO - Aderencia Media"
    else:
        return "REPROVADO - Baixa Aderencia"


def salvar_csv(resultados: list[dict], caminho: Path):
    """Salva todos os resultados num arquivo CSV."""
    if not resultados:
        return
    campos = list(resultados[0].keys())
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)
    print(f"\n📄 Relatorio CSV salvo em: {caminho}")


def salvar_relatorio_txt(resultados: list[dict], caminho: Path):
    """Gera um relatório detalhado em texto."""
    aprovados  = [r for r in resultados if "APROVADO" in r["status"]]
    reprovados = [r for r in resultados if "REPROVADO" in r["status"]]

    linhas = [
        "=" * 60,
        "   RELATORIO DE TRIAGEM DE CURRICULOS",
        f"   Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "=" * 60,
        f"\nTotal analisados : {len(resultados)}",
        f"Aprovados        : {len(aprovados)}",
        f"Reprovados       : {len(reprovados)}",
        f"Pontuacao minima : {PONTUACAO_MINIMA}",
        "\n" + "-" * 60,
        "RANKING DOS APROVADOS",
        "-" * 60,
    ]

    for i, r in enumerate(sorted(aprovados, key=lambda x: x["pontuacao"], reverse=True), 1):
        email_status = "e-mail enviado" if r.get("email_enviado") == "sim" else "sem e-mail"
        linhas.append(
            f"{i:>2}. {r['arquivo']:<30} "
            f"Pontuacao: {r['pontuacao']:>5.1f}  |  {email_status}"
        )

    linhas += ["\n" + "-" * 60, "REPROVADOS", "-" * 60]
    for r in sorted(reprovados, key=lambda x: x["pontuacao"], reverse=True):
        linhas.append(
            f"   {r['arquivo']:<30} Pontuacao: {r['pontuacao']:>5.1f}"
        )

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"📋 Relatorio TXT salvo em: {caminho}")


# ══════════════════════════════════════════════════════════════
#  📧  MÓDULO DE E-MAIL
# ══════════════════════════════════════════════════════════════

def montar_email_html(nome_candidato: str, pontuacao: float, status: str) -> str:
    """Gera o corpo do e-mail em HTML com visual profissional."""
    nivel    = "Alta Aderencia" if pontuacao >= 70 else "Aderencia Media"
    cor      = "#2E6DA4" if pontuacao >= 70 else "#F59E0B"
    barra    = min(int(pontuacao), 100)

    return f"""
    <html>
    <body style="margin:0;padding:0;background:#F4F6F8;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:32px 16px;">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:8px;
                          box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;">

              <!-- Cabecalho -->
              <tr>
                <td style="background:#1A3A5C;padding:32px 40px;">
                  <h1 style="margin:0;color:#ffffff;font-size:22px;">{NOME_EMPRESA}</h1>
                  <p style="margin:6px 0 0;color:#B8D4F0;font-size:14px;">
                    Processo Seletivo &mdash; {NOME_VAGA}
                  </p>
                </td>
              </tr>

              <!-- Corpo -->
              <tr>
                <td style="padding:36px 40px;">
                  <p style="color:#333;font-size:16px;margin:0 0 16px;">
                    Ola, <strong>{nome_candidato}</strong>!
                  </p>
                  <p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 24px;">
                    Temos uma otima noticia: apos a analise do seu curriculo para a vaga de
                    <strong>{NOME_VAGA}</strong>, voce foi <strong>aprovado(a)</strong>
                    na nossa triagem inicial e avancou para a proxima etapa do processo seletivo!
                  </p>

                  <!-- Card de pontuacao -->
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="background:#F4F6F8;border-radius:6px;margin-bottom:24px;">
                    <tr>
                      <td style="padding:20px 24px;">
                        <p style="margin:0 0 8px;color:#1A3A5C;font-size:13px;
                                  font-weight:bold;text-transform:uppercase;
                                  letter-spacing:.5px;">
                          Resultado da Triagem
                        </p>
                        <p style="margin:0 0 12px;color:#333;font-size:22px;font-weight:bold;">
                          {pontuacao:.1f}
                          <span style="font-size:14px;color:#888;">/ 100</span>
                          &nbsp;
                          <span style="font-size:13px;color:{cor};font-weight:normal;">
                            {nivel}
                          </span>
                        </p>
                        <!-- Barra de progresso -->
                        <div style="background:#DDE3EB;border-radius:4px;height:8px;">
                          <div style="background:{cor};width:{barra}%;
                                      height:8px;border-radius:4px;"></div>
                        </div>
                      </td>
                    </tr>
                  </table>

                  <p style="color:#555;font-size:14px;line-height:1.7;margin:0 0 24px;">
                    Nossa equipe de RH entrara em contato em breve com as instrucoes
                    para as proximas etapas. Fique atento ao seu e-mail e telefone.
                  </p>

                  <p style="color:#555;font-size:14px;line-height:1.7;margin:0;">
                    Atenciosamente,<br>
                    <strong>Equipe de Recrutamento</strong><br>
                    {NOME_EMPRESA}
                  </p>
                </td>
              </tr>

              <!-- Rodape -->
              <tr>
                <td style="background:#F4F6F8;padding:16px 40px;
                            border-top:1px solid #E2E8F0;">
                  <p style="margin:0;color:#999;font-size:11px;text-align:center;">
                    Este e um e-mail automatico enviado pelo sistema de triagem de curriculos.
                    Por favor, nao responda diretamente a esta mensagem.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


def enviar_email(destinatario: str, nome_candidato: str,
                 pontuacao: float, status: str) -> bool:
    """
    Envia e-mail de aprovacao para o candidato.
    Retorna True se enviado com sucesso, False caso contrario.
    """
    if destinatario == "nao encontrado":
        print(f"      ⚠️  E-mail nao encontrado no curriculo — pulando envio.")
        return False

    assunto = f"Parabens! Voce avancou no processo seletivo — {NOME_VAGA}"

    # ── Modo simulacao: apenas loga, nao envia ───────────────────
    if MODO_SIMULACAO:
        print(f"      [SIMULACAO] E-mail para: {destinatario} ({nome_candidato}, {pontuacao:.1f} pts)")
        return True

    # ── Envio real via SMTP ──────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{NOME_EMPRESA} Recrutamento <{EMAIL_REMETENTE}>"
        msg["To"]      = destinatario
        msg["Subject"] = assunto

        html = montar_email_html(nome_candidato, pontuacao, status)
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
            servidor.sendmail(EMAIL_REMETENTE, destinatario, msg.as_string())

        print(f"      📧 E-mail enviado para: {destinatario}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("      ❌ Falha de autenticacao SMTP. Verifique EMAIL_REMETENTE e EMAIL_SENHA.")
        return False
    except smtplib.SMTPException as e:
        print(f"      ❌ Erro SMTP ao enviar para {destinatario}: {e}")
        return False
    except Exception as e:
        print(f"      ❌ Erro inesperado: {e}")
        return False


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
        print("        Coloque os curriculos em PDF nessa pasta e execute novamente.")
        return

    modo = "SIMULACAO" if MODO_SIMULACAO else "ENVIO REAL"
    print(f"\n🔍 {len(pdfs)} curriculo(s) encontrado(s). Modo de e-mail: {modo}\n")
    print(f"{'ARQUIVO':<40} {'PONTUACAO':>10}  STATUS")
    print("-" * 75)

    for pdf in pdfs:
        # 1. Extrai texto
        texto = extrair_texto_pdf(pdf)

        if not texto.strip():
            print(f"  {pdf.name:<38} [SEM TEXTO — PDF ESCANEADO]")
            continue

        # 2. Calcula pontuacao
        pontuacao, detalhes = calcular_pontuacao(texto)

        # 3. Classifica
        status = classificar(pontuacao)

        # 4. Extrai contato
        email          = extrair_email(texto)
        telefone       = extrair_telefone(texto)
        nome_candidato = extrair_nome_candidato(texto)

        print(f"  {pdf.name:<38} {pontuacao:>8.1f}/100  {status}")

        # 5. Envia e-mail apenas para aprovados
        email_enviado = False
        if "APROVADO" in status:
            email_enviado = enviar_email(email, nome_candidato, pontuacao, status)

        # 6. Monta registro
        registro = {
            "arquivo":       pdf.name,
            "nome":          nome_candidato,
            "pontuacao":     pontuacao,
            "status":        status,
            "email":         email,
            "telefone":      telefone,
            "email_enviado": "sim" if email_enviado else "nao",
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

    if not resultados:
        print("\n[INFO] Nenhum resultado gerado.")
        return

    # ── Salva relatorios ───────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    salvar_csv(resultados, PASTA_SAIDA / f"triagem_{ts}.csv")
    salvar_relatorio_txt(resultados, PASTA_SAIDA / f"relatorio_{ts}.txt")

    # ── Resumo final ───────────────────────────────────────────
    aprovados     = [r for r in resultados if "APROVADO" in r["status"]]
    emails_ok     = [r for r in aprovados if r["email_enviado"] == "sim"]
    emails_falhou = [r for r in aprovados if r["email_enviado"] == "nao"]

    print(f"\n{'='*50}")
    print(f"  Aprovados       : {len(aprovados)}/{len(resultados)}")
    print(f"  E-mails enviados: {len(emails_ok)}/{len(aprovados)}")
    if emails_falhou:
        print(f"  Sem e-mail      : {len(emails_falhou)} candidato(s)")
        for r in emails_falhou:
            print(f"    -> {r['arquivo']}  ({r['email']})")
    print(f"  Saida           : {PASTA_SAIDA.resolve()}")
    print(f"{'='*50}\n")


# ══════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()