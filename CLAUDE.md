# All News Journal — Guia para o Claude Code (v15.0)

> Este arquivo existe para que futuras sessões do Claude Code entendam o projeto instantaneamente.

---

## O que é este projeto

O **All News Journal** (`noticias-matinais`) é um jornal digital premium 100% automatizado. Ele:
1. Busca notícias via feeds RSS de 10 categorias temáticas
2. Gera resumos jornalísticos em português brasileiro usando a API do Claude
3. Envia uma edição diária por email a cada assinante (às 6h, horário de Brasília)
4. Tem um portal Streamlit que exibe as últimas notícias + formulário de inscrição na sidebar
5. É automatizado via GitHub Actions (cron `0 9 * * *` = 09:00 UTC = 06:00 BRT)
6. Posta automaticamente no Instagram 15 minutos após o email (via `instagram.yml`)

---

## Estrutura de arquivos (v15.0)

```
noticias-matinais/
├── main.py               <- Motor principal (orquestra os módulos)
├── config.py             <- Todas as constantes: RSS_FEEDS, FILTROS_TEMA, INSTRUCAO_TEMA,
│                            CORES_TEMA, ICONES_TEMA, HASHTAGS_TEMA, FEEDS_INGLES, etc.
├── feeds.py              <- Coleta RSS, filtros, deduplicacao, traducao, pipeline por tema
├── claude_api.py         <- Chamadas a API Anthropic: chamar_claude_api, chamar_claude_haiku,
│                            limpar_texto_rss, extrair_contexto_base, limpar_resumo
├── email_builder.py      <- Geracao HTML do email, painel financeiro, envio com retry
├── sheets_db.py          <- Google Sheets: conectar, historico, logs
├── instagram_poster.py   <- Geracao de imagens Pillow + postagem via instagrapi
├── app.py                <- Portal Streamlit (importa de config.py)
├── requirements.txt      <- Dependencias Python
├── CLAUDE.md             <- Este arquivo
├── .env.example          <- Template de variaveis de ambiente
├── .gitignore
└── .github/
    └── workflows/
        ├── daily.yml           <- GitHub Actions (6h BRT, timeout 30min)
        ├── keep_alive.yml      <- Ping leve no Streamlit a cada 25 min (curl)
        └── instagram.yml       <- Posts Instagram (09:15 UTC = 06:15 BRT)
```

---

## Variaveis de ambiente

| Variavel | Onde e usada | Descricao |
|---|---|---|
| `CLAUDE_KEY` / `ANTHROPIC_API_KEY` | config.py | Chave da API Anthropic |
| `GCP_JSON` | sheets_db.py + app.py | JSON da Service Account Google (para Sheets) |
| `EMAIL_USER` | email_builder.py | Email remetente (Gmail) |
| `EMAIL_PASS` / `EMAIL_PASSWORD` | email_builder.py | App Password do Gmail |
| `EMAIL_FROM` | email_builder.py | Nome de exibicao do remetente (opcional) |
| `SMTP_HOST` | config.py | Servidor SMTP (padrao: smtp.gmail.com) |
| `SMTP_PORT` | config.py | Porta SMTP (padrao: 587) |
| `URL_CANCELAMENTO` | config.py | URL do Streamlit para cancelamento |
| `GOOGLE_SHEETS_ID` | config.py | ID da planilha (alternativa ao nome) |
| `INSTAGRAM_USER` | instagram_poster.py | Usuario do Instagram |
| `INSTAGRAM_PASS` | instagram_poster.py | Senha do Instagram |
| `INSTAGRAM_ENABLED` | instagram_poster.py | "true" para ativar posts (padrao: "false") |

**No Streamlit Cloud**, as variaveis sao configuradas em `st.secrets` com os mesmos nomes.

---

## Google Sheets — Estrutura da planilha

- Nome da planilha: **`noticias_db`**
- Aba principal (sheet1): lista de assinantes

| Nome | Email | Mundo | Mercado | Politica | Tech | Esportes | Cinema | Fitness | Ciencia | Motos | Fofoca |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Joao Silva | joao@email.com | 1 | 2 | Nao | 3 | 4 | Nao | 5 | Nao | 6 | Nao |

- Colunas de tema: numero (posicao no email) ou `"Nao"` (nao receber)
- Aba `historico`: hash + titulo + data das noticias ja enviadas (anti-duplicata)
- Aba `logs`: registro de envios por assinante

---

## Fluxo do main.py

```
validar_ambiente()
    v
sheets_db.conectar_banco()         <- Google Sheets
    v
sheets_db.carregar_historico()     <- Anti-duplicata (30 dias)
    v
email_builder.obter_indicadores()  <- yfinance (USD/BRL, IBOV, BTC)
    v
Para cada tema demandado pelos assinantes:
    feeds.processar_tema()
        coletar_entries -> aplicar_filtros -> rankear_por_relevancia
        -> titulos_similares (dedup) -> traduzir titulo se ingles
        -> chamar_claude_api (prompt por caderno)
            SKIP -> descarta noticia
            Fallback 1: reescreve contexto base
            Fallback 2: gera so pelo titulo
            Fallback 3: usa contexto limpo
        -> extrair_imagem_rss (og:image > media > enclosure > fallback Unsplash)
    v
main.gerar_editorial()             <- Frase de abertura via Claude Haiku
    v
Para cada assinante:
    email_builder.montar_subject()     <- Subject dinamico com titulos reais
    email_builder.gerar_html_final()   <- Template com preheader, sumario, tempo de leitura
    email_builder.enviar_email()       <- SMTP com retry (3x, backoff 15s)
    sheets_db.registrar_log()          <- Aba "logs" no Sheets
    v
Resumo de status dos feeds (FEEDS_STATUS)
```

---

## Modelo Claude utilizado

- **claude-sonnet-4-6** (tentativa 1, timeout 90s)
- **claude-haiku-4-5-20251001** (fallback + tarefas leves: traducao, ranking, editorial)
- Chamadas via `claude_api.py` (HTTP direto para `api.anthropic.com/v1/messages`)
- Retry automatico em rate-limit com backoff: 20s x tentativa

---

## Melhorias implementadas na v15.0

### BLOCO 1 — Refatoracao em modulos
- `config.py`, `feeds.py`, `claude_api.py`, `email_builder.py`, `sheets_db.py`
- `main.py` agora tem ~100 linhas (era 1350+)
- `app.py` importa constantes de `config.py` (sem duplicacao)

### BLOCO 2 — Fix Fitness em ingles
- `FEEDS_INGLES` em `config.py` lista os feeds americanos
- `feeds._e_feed_ingles()` detecta entries de feeds ingleses por URL de origem
- Titulo traduzido automaticamente via `chamar_claude_haiku` antes de gerar o resumo
- Prompt injeta "ATENCAO: texto em ingles" com titulo original

### BLOCO 3 — Melhorias no email
- **Preheader**: texto invisivel para preview no Gmail
- **Subject dinamico**: titulos reais das noticias
- **Sumario/indice**: links clicaveis para cada caderno dentro do email
- **Tempo de leitura**: estimado por contagem de palavras dos resumos
- **Fallback de imagem**: gradiente colorido do caderno

### BLOCO 4 — Portal Streamlit
- **Contador de assinantes**: exibido abaixo da data com cache 10 min
- **Secao "Sobre"**: expander com missao, frequencia e tabela de cadernos
- **Meta tags SEO**: og:title, og:description, meta description

### BLOCO 5 — Confiabilidade
- **Retry no envio de email**: 3 tentativas com backoff de 15s
- **Log de feeds quebrados**: `FEEDS_STATUS` dict; resumo no final do main()
- **keep_alive.yml**: substituido por curl leve (era Playwright pesado), intervalo 25 min

### BLOCO 6 — Instagram
- `instagram_poster.py`: gera imagens 1080x1080 com Pillow + posta via instagrapi
- `.github/workflows/instagram.yml`: roda 15 min apos o daily
- Variaveis: `INSTAGRAM_USER`, `INSTAGRAM_PASS`, `INSTAGRAM_ENABLED`

### BLOCO 7 — Melhorias finais
- **Ranking de relevancia**: Claude Haiku ordena candidatas antes de gerar resumos
- **Editorial do dia**: frase de abertura conectando destaques (compartilhada com todos)
- **Feeds Fofoca**: People, Variety, Entertainment Weekly adicionados

---

## Como rodar localmente

```bash
# 1. Clone o repositorio
git clone https://github.com/gustavojustusnunes-create/noticias-matinais.git
cd noticias-matinais

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows

# 3. Instale as dependencias
pip install -r requirements.txt

# 4. Configure as variaveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais reais

# 5. Rode o motor principal (envia emails)
python main.py

# 6. Rode o portal Streamlit
streamlit run app.py

# 7. Rode o poster do Instagram (opcional)
INSTAGRAM_ENABLED=true python instagram_poster.py
```

---

## Secrets do GitHub Actions

Configure em: `Settings -> Secrets and variables -> Actions`

```
CLAUDE_KEY
GCP_JSON
EMAIL_USER
EMAIL_PASSWORD
EMAIL_FROM
SMTP_HOST
SMTP_PORT
URL_CANCELAMENTO
INSTAGRAM_USER
INSTAGRAM_PASS
INSTAGRAM_ENABLED
```

---

## Padroes de codigo

- Comentarios em portugues brasileiro
- Logging com `print()` e emojis (estilo do projeto original)
- Try/except em toda chamada externa
- Maximo ~4 artigos por caderno no email (evita emails gigantes)
- Filtragem em 3 niveis: titulo + link + corpo do artigo
- SKIP retornado pela IA descarta a noticia silenciosamente
