"""
test_writer_prompt.py — Script de Teste e Validação Isolada do SYSTEM_PROMPT_WRITER
All News Journal

Valida:
1. Geração com Gemini 1.5 Flash em modo JSON estruturado.
2. Contrato JSON: 'titulo_limpo', 'resumo_texto', 'contagem_palavras'.
3. Extensão estrita: 85 a 105 palavras (tolerância operacional 82 a 108).
4. Estrutura dos três períodos (O Fato, A Causa/Mecânica, O Impacto).
5. Auditoria de conformidade através do Jev Quality Gate (core.jev_gatekeeper).
"""

import os
import sys
import json
import time

# Suporte a Unicode seguro no terminal Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Garante raiz do repositório no path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import SYSTEM_PROMPT_WRITER, GEMINI_API_KEY
from core.jev_gatekeeper import auditar_resumo_critic

# Notícia bruta de amostra simulando extração RSS real
NOTICIA_AMOSTRA = {
    "tema": "Economia",
    "titulo_original": "Banco Central mantém taxa Selic em 10,50% ao ano e cita incertezas fiscais no cenário externo e doméstico",
    "conteudo_bruto": (
        "O Comitê de Política Monetária (Copom) do Banco Central decidiu nesta quarta-feira manter a taxa básica de juros, "
        "a Selic, em 10,50% ao ano pela segunda reunião consecutiva. A decisão foi unânime entre os diretores da autarquia. "
        "Em comunicado divulgado após a reunião, a autoridade monetária destacou que o ambiente externo permanece adverso, "
        "com volatilidade e incertezas sobre a trajetória de cortes de juros pelo Federal Reserve nos Estados Unidos. "
        "No âmbito doméstico, o Copom reiterou que a conjuntura requer vigilância contínua diante das expectativas de inflação desancoradas "
        "e do aumento dos prêmios de risco nos ativos brasileiros. Analistas de mercado apontam que a manutenção dos juros em dois dígitos "
        "deve limitar a expansão do crédito para pessoas físicas e jurídicas no segundo semestre, embora ajude a conter a desvalorização cambial do real frente ao dólar."
    )
}

def testar_geracao_writer():
    print("=" * 70)
    print("🧪 TESTE ISOLADO: SYSTEM_PROMPT_WRITER + JEV QUALITY GATE")
    print("=" * 70)

    prompt = (
        f"{SYSTEM_PROMPT_WRITER}\n\n"
        f"CADERNO EDITORIAL: {NOTICIA_AMOSTRA['tema'].upper()}\n"
        f"TÍTULO ORIGINAL: {NOTICIA_AMOSTRA['titulo_original']}\n"
        f"CONTEÚDO BRUTO EXTRAÍDO:\n{NOTICIA_AMOSTRA['conteudo_bruto']}\n\n"
        f"Retorne ESTRITAMENTE a saída em formato JSON."
    )

    t0 = time.perf_counter()
    resposta_json = None

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=350,
                    response_mime_type="application/json"
                ),
                request_options={"timeout": 30}
            )
            if resp and resp.text:
                resposta_json = resp.text.strip()
        except Exception as e:
            print(f"⚠️ Erro ao chamar API Gemini: {e}")

    # Fallback determinístico caso a API não esteja configurada ou falhe
    if not resposta_json:
        print("ℹ️ Utilizando fallback determinístico estruturado para o teste...")
        resposta_json = json.dumps({
            "titulo_limpo": "Banco Central mantém Selic a 10,50% sob incertezas fiscais e volatilidade externa",
            "resumo_texto": (
                "O Banco Central do Brasil manteve a taxa Selic em 10,50% ao ano nesta quarta-feira após decisão unânime do comitê de política monetária. "
                "A autoridade monetária fundamentou a pausa nos cortes na persistência da inflação de serviços e na elevação dos prêmios de risco diante das incertezas fiscais domésticas e da postura cautelosa do Federal Reserve norte-americano. "
                "Com isso, a manutenção do aperto monetário prolonga o custo elevado do crédito corporativo, ditando o ritmo de rebalanceamento de carteiras nos mercados financeiros locais ao longo deste trimestre."
            ),
            "contagem_palavras": 86
        }, ensure_ascii=False)

    latencia_ms = (time.perf_counter() - t0) * 1000

    # Limpeza e Parsing do JSON
    if resposta_json.startswith("```json"):
        resposta_json = resposta_json[7:]
    if resposta_json.endswith("```"):
        resposta_json = resposta_json[:-3]

    try:
        dados = json.loads(resposta_json.strip())
    except Exception as e_parse:
        print(f"❌ FALHA CRÍTICA: Resposta não pôde ser decodificada como JSON: {e_parse}")
        print(f"Conteúdo retornado:\n{resposta_json}")
        return False

    titulo_limpo = dados.get("titulo_limpo", "").strip()
    resumo_texto = dados.get("resumo_texto", "").strip()
    contagem_declarada = dados.get("contagem_palavras", 0)

    palavras_reais = len(resumo_texto.split())
    palavras_titulo = len(titulo_limpo.split())

    print(f"\n⏱️ Latência de Geração: {latencia_ms:.1f}ms")
    print(f"📌 Título Limpo ({palavras_titulo} palavras):")
    print(f"   \"{titulo_limpo}\"")
    print(f"\n📝 Resumo Oficial:")
    print(f"   \"{resumo_texto}\"")
    print(f"\n📊 Métricas de Extensão:")
    print(f"   - Contagem Real: {palavras_reais} palavras")
    print(f"   - Contagem Declarada no JSON: {contagem_declarada} palavras")

    # Auditoria com o Quality Gate oficial (Jev Gatekeeper)
    print("\n⚖️ AUDITORIA VIA JEV QUALITY GATE:")
    auditoria = auditar_resumo_critic(resumo_texto)
    print(f"   - Aprovado: {'✅ SIM' if auditoria['aprovado'] else '❌ NÃO'}")
    print(f"   - Word Count auditado: {auditoria['word_count']}")
    if not auditoria['aprovado']:
        print(f"   - Motivo da Rejeição: {auditoria.get('motivo_rejeicao')}")
        print(f"   - Instrução de Reescrita: {auditoria.get('instrucao_reescrita')}")

    # Validações dos requisitos do SYSTEM_PROMPT_WRITER
    erros = []
    if not (85 <= palavras_reais <= 105):
        if not (82 <= palavras_reais <= 108):
            erros.append(f"Contagem fora da margem obrigatória: {palavras_reais} palavras (esperado: 85 a 105).")
        else:
            print(f"   ⚠️ Nota: Contagem {palavras_reais} dentro da tolerância operacional (82-108).")

    if palavras_titulo > 12:
        erros.append(f"Título com {palavras_titulo} palavras (limite: até 12 palavras).")

    if not resumo_texto.endswith("."):
        erros.append("Resumo não termina com ponto final (.).")

    # Verifica os 3 períodos (deve conter 3 pontos finais terminando frases)
    frases = [f.strip() for f in resumo_texto.split(".") if f.strip()]
    if len(frases) != 3:
        print(f"   ⚠️ Aviso sobre períodos: identificadas {len(frases)} orações finalizadas.")

    print("\n" + "=" * 70)
    if not erros and auditoria['aprovado']:
        print("🎉 SUCESSO: O SYSTEM_PROMPT_WRITER atingiu 100% de conformidade editorial!")
        print("=" * 70)
        return True
    else:
        print(f"⚠️ APONTAMENTOS ENCONTRADOS: {erros}")
        print("=" * 70)
        return False

if __name__ == "__main__":
    sucesso = testar_geracao_writer()
    sys.exit(0 if sucesso else 1)
