# All News Journal — Guia para o Claude Code

> Este arquivo existe para que futuras sessões do Claude Code entendam o projeto instantaneamente.

---

## O que é este projeto

O **All News Journal** (`noticias-matinais`) é um jornal digital premium 100% automatizado. Ele:
1. Busca notícias via feeds RSS de 10 categorias temáticas
2. Gera resumos jornalísticos em português brasileiro usando a API do Claude
3. Envia uma edição diária por email a cada assinante (às 6h, horário de Brasília)
4. Tem um portal Streamlit que exibe as últimas notícias + formulário de inscrição na sidebar
5. É automatizado via GitHub Actions (cron `0 9 * * *` = 09:00 UTC = 06:00 BRT)

---

## Estrutura de arquivos

```
noticias-matinais/
├── main.py               ← Motor principal (RSS → Claude → Email)
├── app.py                ← Portal Streamlit (preview de notícias + inscrição/cancelamento)
├── requirements.txt      ← Dependências Python
├── CLAUDE.md             ← Este arquivo
├── .env.example          ← Template de variáveis de ambiente
├── .gitignore
└── .github/
    └── workflows/
        └── daily_edition.yml   ← GitHub Actions (6h BRT, timeout 30min)
```

---

## Variáveis de ambiente

| Variável | Onde é usada | Descrição |
|---|---|---|
| `CLAUDE_KEY` | main.py | Chave da API Anthropic |
| `GCP_JSON` | main.py + app.py | JSON da Service Account Google (para Sheets) |
| `EMAIL_USER` | main.py | Email remetente (Gmail) |
| `EMAIL_PASSWORD` | main.py | App Password do Gmail |
| `EMAIL_FROM` | main.py | Nome de exibição do remetente (opcional) |
| `SMTP_HOST` | main.py | Servidor SMTP (padrão: smtp.gmail.com) |
| `SMTP_PORT` | main.py | Porta SMTP (padrão: 587) |
| `URL_CANCELAMENTO` | main.py | URL do Streamlit para cancelamento |

**No Streamlit Cloud**, as variáveis são configuradas em `st.secrets` com os mesmos nomes.

---

## Google Sheets — Estrutura da planilha

- Nome da planilha: **`noticias_db`**
- Aba principal (sheet1): lista de assinantes

| Nome | Email | Mundo | Mercado | Politica | Tech | Esportes | Cinema | Fitness | Ciencia | Motos | Fofoca |
|---|---|---|---|---|---|---|---|---|---|---|---|
| João Silva | joao@email.com | 1 | 2 | Não | 3 | 4 | Não | 5 | Não | 6 | Não |

- Colunas de tema: número (posição no email) ou `"Não"` (não receber)
- Aba `historico`: hash + título + data das notícias já enviadas (anti-duplicata)
- Aba `logs`: registro de envios por assinante

---

## Cadernos e feeds RSS

### Mercado (📈)
InfoMoney, UOL Economia, Valor Econômico, Bloomberg Línea BR, Exame Invest  
**Filtros:** bloqueia toda política, eleições, partidos, governo, STF, TSE, impeachment, reforma, CPI, orçamento federal

### Tech (💻)
TechCrunch, The Verge, Olhar Digital, Tecnoblog, Canaltech, TecMundo

### Esportes (🏎️)
Motorsport F1, The Playoffs, ESPN BR, SporTV, UOL Esporte, GE, Lance!  
**Filtros:** bloqueia apostas, bet, odds, palpites, casas de apostas, futebol em geral  
**Prioridade:** F1, NBA, MMA, Tênis (não futebol)

### Fitness (🏃)
EU Atleta (GE), Runner's World BR, Men's Health, Women's Health, Boa Forma, Viva Bem, Bicycling  
**IMPORTANTE:** artigos em inglês → resumo OBRIGATORIAMENTE em português brasileiro

### Fofoca (⭐)
Hugo Gloss, Revista Quem  
**Filtros:** ex-BBB, sertanejo, funkeiro, política brasileira  
**Foco:** celebridades internacionais/Hollywood (via instrução IA com SKIP)

### Motos (🏍️)
Motociclismo Online, Motoo (UOL), Motoblog, Motonline, Duas Rodas, Motor1 Motos, iCarros Motos, Autoesporte

### Cinema (🎬)
Omelete, CinePop, Papo de Cinema, AdoroCinema

### Ciência (🔬)
G1 Ciência e Saúde, Gizmodo, Inovação Tecnológica, TecMundo Ciência

### Mundo (🌎)
G1 Mundo

### Política (🏛️)
G1 Política *(sem filtros — tudo é relevante neste caderno)*

---

## Fluxo do main.py

```
validar_ambiente() + conectar_banco()    ← Google Sheets
    ↓
carregar_historico()                     ← Anti-duplicata (30 dias)
    ↓
Para cada tema demandado pelos assinantes:
    coletar RSS → aplicar_filtros()      ← Filtra título + link + corpo
    titulos_similares()                  ← Deduplicação
    extrair_contexto_base()              ← Fallback: content > summary > description (800 chars)
    chamar_claude_api()                  ← Prompt por caderno + retry backoff
        SKIP → descarta notícia
        Fallback 1: reescreve contexto base
        Fallback 2: gera só pelo título
        Fallback 3: usa contexto limpo
        ↓
    extrair_imagem_rss()                 ← og:image > media > enclosure > fallback Unsplash
    ↓
obter_indicadores()                      ← yfinance (USD/BRL, IBOV, BTC)
    ↓
Para cada assinante:
    gerar_html_final()                   ← Template inline com CORES_TEMA por caderno
    enviar_email()                       ← SMTP configurável
    registrar_log()                      ← Aba "logs" no Sheets
```

---

## Modelo Claude utilizado

- **claude-sonnet-4-6** (tentativa 1, timeout 90s)
- **claude-haiku-4-5-20251001** (fallback, timeout 60s)
- Chamadas via HTTP direto (`requests.post`) para a API Anthropic
- Retry automático em rate-limit com backoff: 20s × tentativa

---

## Como rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/gustavojustusnunes-create/noticias-matinais.git
cd noticias-matinais

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais reais

# 5. Rode o motor principal (envia emails)
python main.py

# 6. Rode o portal Streamlit
streamlit run app.py
```

---

## Secrets do GitHub Actions

Configure em: `Settings → Secrets and variables → Actions`

```
CLAUDE_KEY
GCP_JSON
EMAIL_USER
EMAIL_PASSWORD
EMAIL_FROM
SMTP_HOST
SMTP_PORT
URL_CANCELAMENTO
```

---

## Padrões de código

- Comentários em português brasileiro
- Logging com `print()` e emojis (estilo do projeto original)
- Try/except em toda chamada externa
- Máximo ~4 artigos por caderno no email (evita emails gigantes)
- Filtragem em 3 níveis: título + link + corpo do artigo
- SKIP retornado pela IA descarta a notícia silenciosamente
