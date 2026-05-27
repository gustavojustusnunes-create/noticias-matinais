# UptimeRobot — Monitor de redundância para o portal Streamlit

> Este monitor é uma **segunda camada de keep-alive** em cima do
> workflow `.github/workflows/keep_alive.yml`. O workflow do GitHub
> roda a cada 10 minutos; o UptimeRobot vai bater a cada 5 minutos,
> reduzindo a chance de o app hibernar entre execuções.

---

## Por que ter os dois

| Camada | Frequência | Pontos fortes | Pontos fracos |
|---|---|---|---|
| GitHub Actions (`keep_alive.yml`) | 10 min | Detecta hibernação e dispara wake-up via POST | Cron do GH pode atrasar em horários de pico |
| **UptimeRobot** | **5 min** | Independente do GitHub, dashboard com histórico, alerta por email | Free tier não dispara POST de wake-up — apenas GET |

Combinando os dois: o UptimeRobot impede a hibernação acontecer (mantém
"morno" com GET de 5 em 5 min); o GitHub Actions trata o caso em que
ela aconteceu mesmo assim.

---

## Passo a passo

### 1. Criar conta

1. Acesse <https://uptimerobot.com/>
2. Clique em **Sign Up Free** (não precisa cartão).
3. Confirme o email.

O plano gratuito permite até 50 monitores com intervalo mínimo de 5 minutos.

### 2. Adicionar o monitor do Streamlit

1. No dashboard, clique em **+ New monitor**.
2. Preencha:

   | Campo | Valor |
   |---|---|
   | **Monitor Type** | `HTTP(s)` |
   | **Friendly Name** | `All News Journal — Streamlit` |
   | **URL (or IP)** | `https://allnewsjournal.streamlit.app/` (ou a URL do seu app) |
   | **Monitoring Interval** | `Every 5 minutes` |
   | **Monitor Timeout** | `30 seconds` |

3. Em **Advanced Settings**:
   - **HTTP Method**: `GET`
   - **Keyword Monitoring** (opcional, recomendado):
     - Marque a opção **Alert when keyword exists**
     - **Keyword Value**: `Yes, get this app back up`
     - Isso faz o UptimeRobot disparar alerta quando o app **estiver
       hibernando** (a string aparece na página de hibernação do
       Streamlit Cloud). Útil mesmo com o keep_alive ativo, porque
       avisa quando o wake-up automático falhou.

4. Em **Select alert contacts to notify**, marque seu email
   (`gustavojustusnunes@gmail.com`). Se quiser, crie também um contato
   de Telegram/Slack.

5. Clique em **Create Monitor**.

### 3. Confirmar que está funcionando

- Em até 5 minutos, o monitor deve aparecer como **Up** (verde) no
  dashboard.
- Clique no monitor para ver o histórico de response time e
  disponibilidade.

### 4. (Opcional) Status page pública

Para mostrar a saúde do serviço de forma pública:

1. **My Settings → Status Pages → + Add Status Page**
2. Selecione o monitor recém-criado.
3. Customize a URL pública (ex: `status.allnewsjournal.com`) ou use a
   URL gerada pelo UptimeRobot.

---

## Comportamento esperado

- **App acordado**: GET retorna 200 sem o keyword → monitor **Up**, sem alerta.
- **App hibernando**: GET retorna 200 **com** keyword "Yes, get this app back up" →
  monitor **Down** (por keyword), envia email. Enquanto isso, o
  `keep_alive.yml` na próxima execução (≤10 min) dispara o POST e acorda.
- **App fora do ar**: GET retorna 5xx/timeout → monitor **Down**, envia email.

---

## Quando reavaliar

- Se o Streamlit Cloud mudar a string da página de hibernação, atualizar
  o **Keyword Value** aqui e o `HIBERNATE_MARK` em `keep_alive.yml`.
- Se migrarmos para um plano pago do Streamlit (sem hibernação) ou para
  outra hospedagem (Fly.io, Railway), todo este monitor pode ir embora.
