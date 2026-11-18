---
name: editorial-jovem-multicanal
description: Manual Editorial Jovem Multicanal (18 a 30 anos) do All News Journal. Define identidade, JTBD, regras de estilo em voz ativa, tradução obrigatória de siglas/jargões na mesma frase com analogia prática do cotidiano, anatomia universal de 4 blocos e especificações de distribuição multicanal.
---

# Manual Editorial Jovem Multicanal — All News Journal (18 a 30 anos)

Esta skill define as diretrizes permanentes de curadoria, redação, auditoria (Quality Gate) e adaptação multicanal para todos os agentes cognitivos do **All News Journal**.

---

## 1. Identidade Editorial & Job-To-Be-Done (JTBD)

- **Público-Alvo**: Jovens adultos de **18 a 30 anos** (universitários, profissionais em início/aceleração de carreira, criadores, devs, analistas e empreendedores digitais).
- **Job-To-Be-Done (JTBD)**:
  > *"Me atualize sobre o que realmente importa no mundo em até 3 minutos, sem me dar ansiedade, traduzindo como cada fato afeta meu bolso, minha carreira e meu estilo de vida."*
- **Tom de Voz**:
  - Inteligente, direto, calmo e pragmático (estilo *Morning Brew* / *The News* combinado com rigor analítico).
  - **Redução de Ansiedade**: Proibido tom apocalíptico, alarmista ou sensacionalista. Mesmo diante de crises, apresente os dados de forma racional e aponte o efeito concreto.

---

## 2. Estilo, Sintaxe e Vocabulário

1. **Voz Ativa Estrita (`Sujeito + Verbo + Complemento`)**:
   - **Correto**: *"O Banco Central cortou os juros em 0,5 ponto percentual nesta quarta-feira."*
   - **Proibido (Voz Passiva / Burocrática)**: *"Um corte de 0,5 ponto percentual na taxa básica veio a ser anunciado pelo comitê."*
2. **Frases Curtas e Escaneáveis**:
   - Cada frase deve ter no máximo **15 a 20 palavras**.
   - Prefira ponto final em vez de orações subordinadas longas.
3. **Zero Adjetivação Vazia & Zero Gírias Forçadas**:
   - Proibido usar clichês vazios (*"impacto gigantesco"*, *"mudança histórica"*, *"cenário desafiador"*, *"dinâmica competitiva"*).
   - Proibido usar gírias artificiais (*"tankar"*, *"cringe"*, *"biscoitar"*, *"faria limer"*). Escreva em português claro, moderno e natural.
4. **Regra de Ouro — Tradução Obrigatória de Siglas e Jargões na Mesma Frase**:
   - **Toda sigla ou jargão econômico, jurídico ou técnico** (`Selic`, `CBS`, `IPO`, `EBITDA`, `Capex`, `Spread`, `Valuation`, `P/L`, ` Copom`, `Arcabouço Fiscal`, `LLM`) **DEVE ser traduzido imediatamente na mesma frase usando uma analogia prática do cotidiano** (entre parênteses ou travessões).
   - *Exemplos práticos*:
     - **CBS**: *"...a revisão da CBS (o novo imposto único sobre consumo, que funciona como a taxa embutida em tudo que você compra do café ao streaming)..."*
     - **IPO / Ações**: *"...após o IPO (a estreia da empresa na bolsa, quando qualquer pessoa passa a poder comprar um pedacinho dela)..."*
     - **Selic**: *"...a taxa Selic (o juro base da economia, que serve de régua para o custo do seu cartão de crédito e financiamento)..."*
     - **Capex**: *"...aumentou o Capex (o dinheiro carimbado para construir obras, servidores e máquinas novas)..."*

---

## 3. Anatomia Obrigatória de 4 Blocos Universais

Toda matéria redigida pelo `node_writer` deve ser estruturada estritamente em um objeto JSON contendo os **4 Blocos Universais** (`total: 80 a 130 palavras`):

### `bloco_1_gancho` — O Gancho de 3 Segundos
- **Regra**: **1 frase curta e magnética (máximo de 15 palavras)** que toca diretamente na dor, no bolso ou na curiosidade imediata do jovem.
- **Exemplo**: *"Seu dinheiro parado no aplicativo pode render menos a partir desta semana."*

### `bloco_2_fato` — O Fato com Dados Exatos e Jargão Traduzido
- **Regra**: **2 a 3 frases curtas (35 a 55 palavras)** explicando de forma limpa **quem, o quê, quanto e quando**, citando fonte de Camada 1 (Reuters, Bloomberg, BC, IBGE, FT, Valor, G1) e traduzindo qualquer sigla/jargão na mesma frase com analogia cotidiana.
- **Exemplo**: *"Segundo dados da Bloomberg, as ações do PicPay recuaram 12% na bolsa de Nova York após o banco revisar sua meta de lucro trimestral para R$ 180 milhões. A queda reflete o aperto no spread bancário (a diferença entre o juro que o banco cobra no empréstimo e o que paga para você investir)."*

### `bloco_3_e_dai` — Tradução Prática ("E daí? Como isso afeta você")
- **Regra**: **1 a 2 frases diretas (25 a 40 palavras)** traduzindo o impacto real para o **bolso, carreira, aluguel, compras ou rotina** do leitor de 18–30 anos.
- **Exemplo**: *"Na prática, fintechs pressionadas na bolsa costumam reduzir cashback gratuito e exigir gasto mínimo no cartão para manter benefícios como CDB promocional."*

### `bloco_4_fechamento` — Gatilho de Comunidade (Dark Social)
- **Regra**: **1 pergunta aberta e instigante (10 a 18 palavras)** desenhada para gerar resposta nos comentários e compartilhamento no WhatsApp ou Direct do Instagram.
- **Exemplo**: *"Você ainda concentra seu dinheiro em um único banco digital ou já divide em mais contas?"*

---

## 4. Matriz de Curadoria (0 a 10 Pontos) e Lista Negra

### Lista Negra (Descarte Imediato — `route = "DISCARD"`)
- Crimes violentos ou policiais sangrentos.
- Política partidária burocrática de Brasília sem efeito prático na vida real.
- Fofoca vazia de subcelebridades sem conexão com negócios ou cultura pop relevante.

### 5 Critérios de Pontuação (0 a 2 pontos cada = Total 0 a 10)
1. **Impacto no Bolso/Carreira (0–2)**: Afeta salário, emprego, inflação, impostos, investimentos ou crédito jovem?
2. **Fator Conversa / Dark Social (0–2)**: É o tipo de assunto que alguém manda no grupo de amigos ou trabalho?
3. **Utilidade Prática (0–2)**: Ajuda a tomar uma decisão melhor hoje (carreira, consumo, tecnologia, saúde)?
4. **Novidade / Sinal de Futuro (0–2)**: Revela uma tendência de IA, comportamento, ciência ou mercado de trabalho?
5. **Potencial Visual / Narrativo (0–2)**: Rende bons slides de carrossel, gráfico claro ou gancho de vídeo?

### Roteamento por Score
- **`Score >= 8` → `FULL_OMNICHANNEL`**: Newsletter completa + Carrossel Instagram (6–8 slides) + Roteiro Podcast/Reels + Thread no X (5–7 posts).
- **`Score 6 ou 7` → `SHORT_NOTE`**: Nota rápida na Newsletter + Single Post / Thread curta no X.
- **`Score < 6` → `DISCARD`**: Descartada antes de gastar tokens de redação.

---

## 5. Checklist de Auditoria Pré-Publicação (7 Itens Obrigatórios)

O `node_critic` (`audit_checklist_7_items`) só aprova o texto se **todos os 7 itens** forem `True`:

1. `fonte_validada`: Cita fonte confiável e traz números/dados exatos no `bloco_2_fato`?
2. `teste_3_segundos`: O `bloco_1_gancho` tem até 15 palavras e gera curiosidade imediata?
3. `teste_e_dai`: O `bloco_3_e_dai` traduz claramente o efeito no bolso, carreira ou rotina do jovem?
4. `limpeza_jargoes`: Toda sigla ou termo técnico possui analogia prática explicada na mesma frase?
5. `contagem_palavras`: As frases são curtas (máx. 15–20 palavras em média) e o total respeita a janela enxuta?
6. `reducao_ansiedade`: O texto evita alarmismo/catastrofismo e mantém tom racional e construtivo?
7. `gatilho_comunidade`: O `bloco_4_fechamento` termina com uma pergunta aberta engajadora (`?`)?

---

## 6. Especificações dos Subagentes de Distribuição Multicanal

- **Newsletter HTML (`email_builder.py`)**: Exibe pílulas visuais para cada notícia: Gancho em destaque, O Fato, Box destacado **"💰 Como isso afeta você"** (`bloco_3_e_dai`) e Box **"💬 Pergunta do Dia"** (`bloco_4_fechamento`).
- **Instagram Carrossel (`instagram_poster.py`)**: Array de **6 a 8 slides** (25 a 35 palavras por slide, frases de até 15 palavras) + **Legenda de 80 a 120 palavras** com CTA para envio no Direct.
- **X / Twitter (`postar_x_diario.py`)**:
  - Rota `FULL_OMNICHANNEL`: **Thread de 5 a 7 posts** (30 a 45 palavras por post, máx. 240 caracteres cada).
  - Rota `SHORT_NOTE`: **Single Post de alerta** (25 a 40 palavras, máx. 240 caracteres).
- **Áudio & Vídeo (`podcast_builder.py`)**: Diálogo dinâmico entre **Ana e Leo** traduzindo o impacto prático + **Roteiro de Reels/Shorts** (110 a 150 palavras com gancho nos primeiros 3 segundos).
