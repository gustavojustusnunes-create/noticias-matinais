# All News Journal — v15.0

Jornal digital automatizado que coleta notícias via RSS, reescreve resumos com IA (Claude/Anthropic) e envia por e-mail diariamente às 6h BRT.

## Estrutura do Projeto

```
all-news-journal/
├── config.py                # Configuração central compartilhada (RSS, ícones, cores, filtros, instruções)
├── main.py                  # Pipeline principal (coleta → IA → e-mail)
├── app.py                   # Portal web Streamlit
├── instagram_poster.py      # Geração de imagens e posts automáticos no Instagram
├── requirements.txt         # Dependências do Streamlit Cloud e pipeline principal
├── requirements-instagram.txt  # Dependências exclusivas do Instagram (NÃO misturar!)
├── .env                     # Variáveis de ambiente (NÃO commitar)
├── .env.example             # Exemplo de configuração
├── subscribers.json         # Lista de assinantes
├── preview.html             # Último jornal gerado (HTML)
├── session.json             # Sessão Instagram (gerado automaticamente)
├── filters/
│   └── global.txt           # Palavras-chave globais de filtro
├── templates/               # Templates HTML do e-mail
│   ├── email.html
│   ├── section.html
│   └── article.html
├── logs/                    # Logs diários
└── .github/workflows/
    ├── publish.yml          # Envio diário às 6h BRT (cron: 0 9 * * *)
    └── instagram.yml        # Posts Instagram às 6h15 BRT (cron: 15 9 * * *)
```

## Os 8 Cadernos

| # | Caderno  | Ícone | Foco editorial |
|---|----------|-------|----------------|
| 1 | Mundo    | 🌎 | Geopolítica, relações internacionais, conflitos, eventos globais |
| 2 | Economia | 📈 | Mercados, ações, empresas, macro, política monetária |
| 3 | Politica | 🏛️ | Política institucional brasileira simplificada e neutra |
| 4 | IA       | 🤖 | OpenAI, Anthropic, Google AI, modelos, papers, regulação de IA |
| 5 | Wellness | 🏃 | Endurance, corrida, ciclismo, musculação, nutrição, mindset, sono |
| 6 | Ciencia  | 🔬 | Pesquisa, descobertas, saúde científica, espaço |
| 7 | Cinema   | 🎬 | Filmes, séries, streaming, festivais, crítica |
| 8 | Fofoca   | ⭐ | Cultura pop INTERNACIONAL: Hollywood, K-pop, realeza, viral global |

> **Removidos na v15.0:** Tech (genérico), Esportes, Motos

## Comandos

```bash
# Instalar dependências principais
pip install -r requirements.txt

# Rodar em modo teste (não envia e-mail)
python main.py --dry-run

# Rodar em produção (envia e-mail)
python main.py

# Portal web
streamlit run app.py

# Instagram (instalar requirements separado primeiro)
pip install -r requirements-instagram.txt
python instagram_poster.py
```

## Configuração de Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição |
|----------|-----------|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória) |
| `SMTP_HOST` | Servidor SMTP (padrão: smtp.gmail.com) |
| `SMTP_PORT` | Porta SMTP (padrão: 587) |
| `SMTP_USER` | E-mail Gmail |
| `SMTP_PASS` | Senha de App do Gmail (não a senha normal) |
| `FROM_EMAIL` | E-mail remetente |
| `FROM_NAME` | Nome do remetente |
| `INSTAGRAM_USER` | Usuário do Instagram (@allnews_journal) |
| `INSTAGRAM_PASS` | Senha do Instagram |
| `INSTAGRAM_ENABLED` | `true` para postar, `false` para só salvar imagens localmente |

## GitHub Actions Secrets

Configure em: `Settings → Secrets and variables → Actions`

```
ANTHROPIC_API_KEY
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
FROM_EMAIL
FROM_NAME
INSTAGRAM_USER
INSTAGRAM_PASS
INSTAGRAM_ENABLED
```

## Pipeline (main.py)

1. Carrega filtros globais de `filters/global.txt`
2. Para cada caderno (na ordem editorial de `ORDEM_CADERNOS`):
   - Coleta artigos via RSS dos feeds definidos em `config.py`
   - Aplica filtros globais + filtros específicos do caderno (`FILTROS_TEMA`)
   - Remove duplicatas por título similar
   - Reescreve resumos com Claude usando instrução editorial específica (`INSTRUCAO_TEMA`)
3. Monta HTML usando templates de `templates/`
4. Salva preview em `preview.html`
5. Envia para assinantes de `subscribers.json`

### Fallback de 3 camadas para IA

1. Se tem resumo RSS → reescreve com Claude (instrução por caderno)
2. Se não tem resumo → gera a partir do título com Claude
3. Se a API falhar → usa texto original do RSS

## Instagram Poster (instagram_poster.py)

- Coleta a notícia mais recente e relevante de cada caderno
- Gera imagem 1080x1080 px com Pillow (gradiente por tema + manchete)
- Gera legenda de 85-105 palavras com Claude
- Posta via instagrapi com reutilização de sessão (`session.json`)
- Se `INSTAGRAM_ENABLED=false`, salva imagens em `/tmp/instagram_posts/` sem postar

## config.py — Referência

- `ORDEM_CADERNOS` — ordem editorial dos cadernos no e-mail
- `RSS_FEEDS` — dict com listas de URLs por caderno
- `ICONES_TEMA` — emoji de cada caderno
- `CORES_TEMA` — cor hex (sem `#`) de cada caderno
- `FILTROS_TEMA` — palavras de exclusão por caderno
- `INSTRUCAO_TEMA` — instrução editorial para a IA por caderno
- `FALLBACK_IMAGES` — imagem Unsplash de fallback por caderno
- `HASHTAGS` — hashtags do Instagram por caderno

## Convenções

- Python 3.11+
- Encoding UTF-8 em todos os arquivos
- Logs em `logs/` com nome `journal_YYYYMMDD.log`
- Fuso horário: BRT (UTC-3)
- Máximo 5 artigos por caderno no e-mail
- Artigos com mais de 48h são ignorados
- `requirements-instagram.txt` é SEPARADO — nunca misturar com `requirements.txt`
