# Landing page — `allnewsjournal.uk`

Pasta deployada no **Cloudflare Pages** como o site público em
[`https://allnewsjournal.uk`](https://allnewsjournal.uk).

Contém uma **única página** (`index.html`) que embute o app Streamlit
([`https://allnewsjournal.streamlit.app`](https://allnewsjournal.streamlit.app))
num iframe em modo `embed=true`. Resultado:

- Visitantes acessam o domínio próprio (não o subdomínio `streamlit.app`)
- A badge "Made with Streamlit" some (escondida pelo embed mode dentro do iframe)
- O HTML wrapper tem meta tags próprias (Open Graph, Twitter Card, favicon)
- Tela de loading com a logo ANJ enquanto o Streamlit carrega
- Query params (`?acao=cancelar`, etc.) são repassados para o iframe

## Setup do Cloudflare Pages

| Campo | Valor |
|---|---|
| Production branch | `main` |
| Build command | _(vazio)_ |
| Build output directory | `landing` |
| Root directory | _(vazio)_ |

Custom domain configurado: `allnewsjournal.uk` (apex).

## Manutenção

- Para mudar o app embutido: edite a constante `BASE_URL` no `<script>`.
- Para atualizar meta tags / SEO: edite o `<head>` do `index.html`.
- Para mudar a logo da tela de loading: substitua `assets/anj-logo.png`
  no root do repo — a URL no HTML aponta para o GitHub raw e pega
  a nova imagem automaticamente.
