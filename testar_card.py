import os
from pathlib import Path
from datetime import datetime

# Define diretório local de preview
OUTPUT_DIR = Path("preview_insta")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
os.environ["INSTAGRAM_OUTPUT_DIR"] = str(OUTPUT_DIR)

from instagram_poster import (
    gerar_slide,
    obter_foto_garantida,
    extrair_keywords,
    segmentar_corpo_leitura,
    gerar_legenda
)

URL = "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=1080&h=1350&fit=crop"

testes = [
    (
        "Mundo",
        "Conselho de Seguranca da ONU aprova tregua historica apos semanas de impasse",
        "O Conselho de Seguranca das Nacoes Unidas aprovou uma resolucao conjunta estabelecendo uma trégua imediata nas zonas de maior tensao no Oriente Medio. Diplomatas destacam que o acordo destrava canais de ajuda humanitaria e abre espaco para negociacoes multilaterais em Genebra nos proximos dias. O documento foi referendado por unanimidade entre os membros permanentes.",
        URL
    ),
    (
        "IA",
        "Nova geracao de chips de inteligencia artificial reduz custo de treinamento em 40%",
        "A nova arquitetura de aceleradores neurais apresentada nesta semana estabelece novos marcos de eficiencia computacional e rendimento termico em data centers de larga escala. As empresas que utilizam a nova tecnologia relataram uma reducao media de 40% no custo total de treinamento e inferencia para modelos generativos com mais de 70 bilhoes de parametros.",
        None
    ),
]

for idx, (tema, titulo, resumo, url) in enumerate(testes, 1):
    print(f"\n--- Gerando teste para [{tema}] ---")
    foto = obter_foto_garantida(url, tema)
    keywords = extrair_keywords(titulo, resumo, tema)
    blocos = segmentar_corpo_leitura(resumo, tema)
    data_str = datetime.now().strftime("%d.%m.%Y")
    
    total_slides = 3
    # Slide 1: Capa Clássica
    s1 = gerar_slide(
        slide_idx=1,
        total_slides=total_slides,
        tema=tema,
        titulo=titulo,
        corpo="",
        kw=keywords[0],
        foto=foto,
        data_str=data_str
    )
    p1 = OUTPUT_DIR / f"teste_{idx}_slide1_capa.jpg"
    s1.save(str(p1), quality=95)
    print(f"Salvo: {p1}")

    # Slide 2: Conteúdo Brutalista Knockout
    s2 = gerar_slide(
        slide_idx=2,
        total_slides=total_slides,
        tema=tema,
        titulo=titulo,
        corpo=blocos[0],
        kw=keywords[0],
        foto=foto,
        data_str=data_str
    )
    p2 = OUTPUT_DIR / f"teste_{idx}_slide2_conteudo.jpg"
    s2.save(str(p2), quality=95)
    print(f"Salvo: {p2}")

    # Slide 3: Fechamento / CTA
    s3 = gerar_slide(
        slide_idx=3,
        total_slides=total_slides,
        tema=tema,
        titulo="INFORMAÇÃO DIRETO AO PONTO",
        corpo="Notícias completas e aprofundadas, entregues diariamente às 6h no seu e-mail. Cadastre-se gratuitamente pelo link na nossa bio.",
        kw="ALL NEWS",
        foto=foto,
        data_str=data_str
    )
    p3 = OUTPUT_DIR / f"teste_{idx}_slide3_cta.jpg"
    s3.save(str(p3), quality=95)
    print(f"Salvo: {p3}")

print("\nTodos os testes foram gerados em preview_insta/")

