import os

# Definido ANTES do import porque OUTPUT_DIR é lido no carregamento do módulo.
os.environ["INSTAGRAM_OUTPUT_DIR"] = "preview_insta"  # salva localmente

from instagram_poster import gerar_imagem_post, gerar_legenda

# Use uma URL real de og:image de qualquer portal para ver a foto ao fundo.
# (Troque pela URL que quiser testar.)
URL = "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=1080&h=1350&fit=crop"

testes = [
    ("Mundo",    "Conselho de Seguranca aprova tregua historica apos semanas", URL),
    ("Economia", "Dolar recua para R$ 4,98 e Ibovespa renova maxima do ano", None),
    ("IA",       "Nova geracao de modelos reduz custo de inferencia em 40%", None),
]
for tema, titulo, url in testes:
    p = gerar_imagem_post(tema, titulo, "03 JUN 2026", imagem_url=url)
    print("Gerado:", p)

print("\nLegenda exemplo:\n")
print(gerar_legenda("Economia",
      "Dolar recua para R$ 4,98 e Ibovespa renova maxima do ano",
      "O dolar fechou em queda de 1,2%, cotado a R$ 4,98. O Ibovespa avancou "
      "0,9% e atingiu 134.200 pontos, recorde do ano. Para o investidor, o real "
      "mais forte tende a aliviar a inflacao de importados nos proximos meses."))
