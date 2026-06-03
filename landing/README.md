# Landing — `allnewsjournal.uk` (redirect para Streamlit)

Pasta deployada no **Cloudflare Pages** como `https://allnewsjournal.uk`.
Faz redirect 302 de todas as requisições para o app Streamlit hospedado em
`https://all-news-journal-ikgdbajp9nobmquagzvx3v.streamlit.app/`.

## Por que redirect (e não iframe)

A primeira versão usava iframe pra esconder a badge "Made with Streamlit"
do canto inferior direito. O Streamlit Cloud (free tier) detecta iframes
e força o navegador a sair, então a abordagem não funcionou. Solução
provisória: redirect simples — perdemos o esconde-badge mas mantemos
a URL bonita `allnewsjournal.uk` pra compartilhar.

Solução definitiva no futuro: migrar de hosting (Render, Railway, Fly).

## Como funciona

Dois mecanismos em paralelo (belt-and-suspenders):

1. **`_redirects`**: regra processada pelo Cloudflare Pages no nível CDN
   antes mesmo de servir qualquer HTML. Redirect instantâneo, sem JS.
2. **`index.html`**: HTML mínimo com `<meta http-equiv="refresh">` +
   `window.location.replace()`. Fallback caso o `_redirects` não pegue
   por algum motivo. Também é a página que renderiza a meta tag Open
   Graph (preview rico no WhatsApp/Slack/etc.).

Query string é sempre preservada (`?acao=cancelar` do email continua
funcionando).

## Setup do Cloudflare Pages

| Campo | Valor |
|---|---|
| Production branch | `main` |
| Build command | _(vazio)_ |
| Build output directory | `landing` |

Custom domain: `allnewsjournal.uk`.

## Para mudar o destino do redirect

Trocar a URL do Streamlit em DOIS lugares:

- `_redirects`: linha `/* ... 302`
- `index.html`: variável `TARGET` no `<script>` + atributo `content` da
  meta refresh + atributo `href` do link `noscript` e `manual-link`
