# Instagram — Deixar o post diário 100% automático

O `instagram.yml` roda todo dia às **06:15 BRT** e posta 1 card por caderno
(até 8). Para funcionar de forma estável, siga os 4 blocos abaixo **uma vez**.

O ponto crítico é o **login**: a partir do IP do GitHub Actions (datacenter,
fora do Brasil), o Instagram quase sempre pede verificação (challenge) e
bloqueia. A solução é gerar a sessão **no seu computador** e guardá-la como
secret. Aí o Actions só reaproveita a sessão, sem logar do zero.

---

## Bloco 1 — Secrets e Variable no GitHub

Em **Settings → Secrets and variables → Actions**:

### Secrets (aba "Secrets")
| Nome | Valor |
|---|---|
| `INSTAGRAM_USER` | usuário do Instagram (sem @) |
| `INSTAGRAM_PASS` | senha do Instagram |
| `INSTAGRAM_SESSION` | (preenchido no Bloco 3) |
| `CLAUDE_KEY` | chave Anthropic (já deve existir) |
| `GCP_JSON` | service account Google (já deve existir) |
| `GOOGLE_SHEETS_ID` | ID da planilha (já deve existir) |

### Variable (aba "Variables")
| Nome | Valor |
|---|---|
| `INSTAGRAM_ENABLED` | `true` para ligar os posts / `false` para pausar |

> Enquanto `INSTAGRAM_ENABLED` for `false`, o workflow roda mas **não posta**.

---

## Bloco 2 — Recomendações de conta (reduz bloqueio)

- Use uma conta **dedicada** ao jornal (não a sua pessoal).
- Deixe a conta **logada no celular** normalmente por alguns dias antes.
- De preferência **desative o 2FA** ou esteja pronto para digitar o código
  quando rodar o gerador (Bloco 3). Com 2FA por app autenticador, tenha o
  código em mãos.

---

## Bloco 3 — Gerar a sessão (no SEU computador, uma vez)

Na raiz do projeto, no PowerShell:

```powershell
pip install -r requirements-instagram.txt
$env:INSTAGRAM_USER = "seu_usuario"
$env:INSTAGRAM_PASS = "sua_senha"
py gerar_sessao_instagram.py
```

- Se o Instagram pedir um **código** (e-mail/SMS), o script pergunta no
  terminal — digite e continue.
- No fim, ele imprime um **texto longo em base64**. Copie **tudo**.

Depois, no GitHub: **Settings → Secrets and variables → Actions → New
repository secret**:
- **Name**: `INSTAGRAM_SESSION`
- **Secret**: cole o base64 copiado.

> O arquivo `session.json` criado localmente é sensível e já está no
> `.gitignore` — **não comite**.

---

## Bloco 4 — Ativar e testar

1. Confirme que a Variable `INSTAGRAM_ENABLED` está como `true`.
2. Vá em **Actions → "Instagram Daily Posts" → Run workflow** (botão manual)
   para testar agora, sem esperar as 06:15.
3. Acompanhe o log. Procure por:
   - `🔑 Sessão restaurada a partir do secret INSTAGRAM_SESSION.`
   - `✅ Sessão Instagram válida (reaproveitada).`
   - `✅ Post publicado!`
4. Confira o perfil no Instagram.

Se aparecer `❌ Instagram pediu verificação (challenge)`, a sessão do secret
expirou ou ficou inválida — basta **repetir o Bloco 3** (rodar o gerador de
novo e atualizar o secret `INSTAGRAM_SESSION`).

---

## Manutenção

- A sessão dura bastante (meses) enquanto o device for o mesmo. Se um dia os
  posts pararem com erro de login, refaça o **Bloco 3**.
- Para **pausar** os posts sem mexer em código: Variable
  `INSTAGRAM_ENABLED = false`.
- As imagens de cada execução ficam disponíveis como **artefato** do run
  (aba Actions → run → Artifacts), retidas por 7 dias.
