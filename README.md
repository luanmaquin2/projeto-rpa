# 🤖 Robô de Triagem de Currículos — BotCity + Python

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![BotCity](https://img.shields.io/badge/BotCity-Framework-00C896?style=for-the-badge)
![pdfplumber](https://img.shields.io/badge/pdfplumber-PDF%20Parser-E34F26?style=for-the-badge)
![License](https://img.shields.io/badge/Licença-MIT-yellow?style=for-the-badge)

**Automatize a triagem inicial de candidatos com Python, BotCity e visão computacional.**  
Lê PDFs de currículos → Filtra por palavras-chave → Classifica candidatos → Gera relatório.

</div>

---

## 📋 Sumário

- [Sobre o projeto](#-sobre-o-projeto)
- [Como funciona](#-como-funciona)
- [Resultados gerados](#-resultados-gerados)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação e uso](#-instalação-e-uso)
- [Configuração](#-configuração)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Currículos de teste](#-currículos-de-teste)
- [Tecnologias](#-tecnologias)
- [Licença](#-licença)

---

## 💡 Sobre o projeto

Triagem manual de currículos é um processo lento e suscetível a vieses. Este robô automatiza a **seleção inicial de candidatos** em 3 etapas:

1. **Lê** todos os PDFs de uma pasta automaticamente
2. **Filtra** o conteúdo por palavras-chave configuráveis por categoria
3. **Classifica** e pontua cada candidato de 0 a 100

O robô é construído com o framework **BotCity** e a biblioteca **pdfplumber**, gerando ao final um relatório CSV e um resumo em texto com o ranking dos aprovados.

---

## ⚙️ Como funciona

```
curriculos/
  ├── candidato1.pdf
  ├── candidato2.pdf
  └── ...
        │
        ▼
┌─────────────────────┐
│  Extração de texto  │  ← pdfplumber lê cada PDF
└────────┬────────────┘
         │
┌────────▼────────────┐
│  Análise de keywords│  ← verifica hard skills, soft skills,
│  por categoria      │     formação, experiência e idiomas
└────────┬────────────┘
         │
┌────────▼────────────┐
│  Pontuação ponderada│  ← cada categoria tem um peso (0–100)
└────────┬────────────┘
         │
┌────────▼────────────┐
│  Classificação      │  ✅ Alta Aderência (≥ 70)
│                     │  🟡 Aderência Média (40–69)
│                     │  ❌ Reprovado (< 40)
└────────┬────────────┘
         │
┌────────▼────────────┐
│  Relatório CSV + TXT│  ← salvo em triagem_saida/
└─────────────────────┘
```

---

## 📊 Resultados gerados

Após a execução, a pasta `triagem_saida/` conterá:

**`triagem_YYYYMMDD_HHMMSS.csv`** — planilha com todos os candidatos e detalhes:

| arquivo | pontuacao | status | email | kw_hard_skills | kw_idiomas | … |
|---------|-----------|--------|-------|----------------|------------|---|
| ana_souza.pdf | 85.0 | ✅ APROVADO — Alta Aderência | ana@email.com | python, aws, docker | inglês fluente | … |

**`relatorio_YYYYMMDD_HHMMSS.txt`** — resumo com ranking dos aprovados e lista de reprovados.

---

## 🔧 Pré-requisitos

- Python **3.10** ou superior
- pip atualizado

```bash
python --version   # deve ser 3.10+
pip install --upgrade pip
```

---

## 🚀 Instalação e uso

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/triagem-curriculos-botcity.git
cd triagem-curriculos-botcity
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Adicione os currículos

Coloque os arquivos `.pdf` dos candidatos na pasta `curriculos/`:

```bash
mkdir curriculos
cp /caminho/para/curriculos/*.pdf curriculos/
```

> 💡 **Não tem PDFs para testar?** Veja a seção [Currículos de teste](#-currículos-de-teste).

### 4. Execute o robô

```bash
python triagem_curriculos.py
```

**Saída esperada no terminal:**

```
🔍 5 currículo(s) encontrado(s). Iniciando triagem...

  ARQUIVO                                  PONTUAÇÃO  STATUS
  ─────────────────────────────────────────────────────────────────────────────
  01_ana_souza_senior.pdf                      85.0/100  ✅ APROVADO — Alta Aderência
  02_marcos_lima_pleno.pdf                     65.0/100  🟡 APROVADO — Aderência Média
  03_juliana_ferreira_junior.pdf               45.0/100  🟡 APROVADO — Aderência Média
  04_roberto_alves_trainee.pdf                 42.0/100  🟡 APROVADO — Aderência Média
  05_fernanda_campos_design.pdf                20.0/100  ❌ REPROVADO — Baixa Aderência

══════════════════════════════════════════════════
  ✅  Aprovados : 4/5
  📁  Saída     : /seu/projeto/triagem_saida
══════════════════════════════════════════════════
```

---

## ⚙️ Configuração

Todas as configurações ficam no topo do arquivo `triagem_curriculos.py`:

### Palavras-chave por categoria

```python
KEYWORDS = {
    "hard_skills": [
        "python", "java", "sql", "machine learning", "docker", "aws", ...
    ],
    "soft_skills": [
        "liderança", "comunicação", "trabalho em equipe", ...
    ],
    "formacao": [
        "ciência da computação", "engenharia", "mba", ...
    ],
    "experiencia": [
        "sênior", "pleno", "analista", "coordenador", ...
    ],
    "idiomas": [
        "inglês fluente", "inglês avançado", "bilíngue", ...
    ],
}
```

### Pesos por categoria

```python
PESOS = {
    "hard_skills":  40,   # peso maior = mais importante na nota
    "soft_skills":  20,
    "formacao":     20,
    "experiencia":  10,
    "idiomas":      10,
}
# Os pesos devem somar 100
```

### Pontuação mínima para aprovação

```python
PONTUACAO_MINIMA = 40   # candidatos abaixo disso são reprovados
```

---

## 📁 Estrutura do projeto

```
triagem-curriculos-botcity/
│
├── triagem_curriculos.py    # robô principal
├── requirements.txt         # dependências Python
├── README.md                # este arquivo
│
├── curriculos/              # coloque os PDFs aqui (não versionado)
│   └── .gitkeep
│
├── triagem_saida/           # relatórios gerados (não versionado)
│   └── .gitkeep
│
└── curriculos_teste/        # currículos fictícios para teste
    ├── 01_ana_souza_senior.pdf
    ├── 02_marcos_lima_pleno.pdf
    ├── 03_juliana_ferreira_junior.pdf
    ├── 04_roberto_alves_trainee.pdf
    └── 05_fernanda_campos_design.pdf
```

---

## 🧪 Currículos de teste

O projeto inclui **5 currículos fictícios** prontos para testar, com perfis que cobrem todas as classificações:

| # | Candidato | Perfil | Nota Esperada |
|---|-----------|--------|:-------------:|
| 1 | **Ana Souza** — Eng. Sênior | Python, AWS, ML, Docker, liderança | ~85 ✅ |
| 2 | **Marcos Lima** — Analista Pleno | SQL, Power BI, Python, inglês avançado | ~65 🟡 |
| 3 | **Juliana Ferreira** — Dev Júnior | React, JavaScript, Git, SQL básico | ~45 🟡 |
| 4 | **Roberto Alves** — Trainee TI | Excel avançado, gestão de projetos | ~42 🟡 |
| 5 | **Fernanda Campos** — Designer | Photoshop, Figma (sem TI) | ~20 ❌ |

Para gerá-los automaticamente:

```bash
python gerar_curriculos_teste.py
```

---

## 🛠️ Tecnologias

| Biblioteca | Uso |
|-----------|-----|
| [BotCity Framework Core](https://github.com/botcity-dev/botcity-framework-core-python) | Orquestração do robô desktop |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Extração de texto dos PDFs |
| [pypdf](https://github.com/py-pdf/pypdf) | Leitura e metadados de PDF |
| [reportlab](https://www.reportlab.com/) | Geração dos PDFs de teste |

---

## 📄 Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE) para mais informações.

---

<div align="center">
  Feito com 🐍 Python e <a href="https://botcity.dev">BotCity</a>
</div>
