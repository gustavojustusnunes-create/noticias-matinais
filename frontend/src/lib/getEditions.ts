import fs from "fs";
import path from "path";
import { Edition } from "../types";

export function getAllEditions(): Edition[] {
  try {
    const edicoesDir = path.resolve(process.cwd(), "..", "edicoes");
    if (!fs.existsSync(edicoesDir)) {
      return [getFallbackEdition()];
    }

    const files = fs
      .readdirSync(edicoesDir)
      .filter((file) => file.endsWith(".json") && /^\d{4}-\d{2}-\d{2}\.json$/.test(file))
      .sort()
      .reverse();

    if (files.length === 0) {
      return [getFallbackEdition()];
    }

    const editions: Edition[] = [];
    for (const file of files) {
      try {
        const fullPath = path.join(edicoesDir, file);
        const content = fs.readFileSync(fullPath, "utf-8");
        const parsed = JSON.parse(content);
        if (parsed.data && parsed.cadernos) {
          editions.push(parsed);
        }
      } catch (e) {
        console.error(`Error reading ${file}:`, e);
      }
    }

    return editions.length > 0 ? editions : [getFallbackEdition()];
  } catch (err) {
    console.error("Error loading editions from filesystem:", err);
    return [getFallbackEdition()];
  }
}

export function getLatestEdition(): Edition {
  const editions = getAllEditions();
  return editions[0] || getFallbackEdition();
}

export function getFallbackEdition(): Edition {
  return {
    data: "2026-09-14",
    data_extenso: "Segunda-feira, 14 de Setembro de 2026",
    editorial: "As principais notícias do Brasil e do mundo curadas e sintetizadas por inteligência artificial.",
    manchete: "EUA dizem ter colocado arma espacial em órbita, diz jornal",
    cadernos: {
      Mundo: [
        {
          titulo: "EUA dizem ter colocado arma espacial em órbita, diz jornal",
          link: "https://g1.globo.com/mundo/noticia/2026/09/14/eua-anunciam-primeira-arma-espacial-em-orbita.ghtml",
          imagem: "https://s2-g1.glbimg.com/tNdGKCwqr0uZtsdE7poS7hE0Pgw=/4896x0/filters:format(jpeg)/https://i.s3.glbimg.com/v1/AUTH_59edd422c0c84a879bd37670ae4f538a/internal_photos/bs/2019/t/8/pR7d27Rba1wlnHCUlLsg/ap19345820043222.jpg",
          resumo: "O Pentágono é o centro de inteligência do governo dos EUA. O secretário da Força Aérea dos Estados Unidos afirmou nesta segunda-feira que o país já posicionou armas espaciais em órbita capazes de defender as forças conjuntas contra adversários hostis."
        },
        {
          titulo: "Trump compara preocupações sobre IA com mudanças climáticas e chama ambas de 'farsa'",
          link: "https://g1.globo.com/mundo/noticia/2026/09/14/trump-compara-preocupacoes-sobre-ia-com-mudancas-climaticas-e-chama-ambas-de-farsa.ghtml",
          imagem: "https://s2-g1.glbimg.com/7RqEwxXoes5EKi8o0WyRPB_DMdQ=/6000x0/filters:format(jpeg)/https://i.s3.glbimg.com/v1/AUTH_59edd422c0c84a879bd37670ae4f538a/internal_photos/bs/2026/z/W/lOmudLTuSlT7i3jE6Ayg/2026-09-09t183748z-793362701-rc2ufnabbbjk-rtrmadp-3-usa-trump.jpg",
          resumo: "Trump afirmou que estão armando conspiração contra a IA e comparou alertas de risco de modelos de IA às discussões climáticas."
        }
      ],
      Economia: [
        {
          titulo: "Brasil e Estados Unidos marcam reunião presencial para negociar tarifaço",
          link: "https://g1.globo.com/economia/noticia/2026/09/14/brasil-e-estados-unidos-marcam-reuniao-presencial-para-negociar-tarifaco.ghtml",
          imagem: "https://s2-g1.glbimg.com/g82CHxGM0obaBWP_HbmsOKxL_hY=/3744x0/filters:format(jpeg)/https://i.s3.glbimg.com/v1/AUTH_59edd422c0c84a879bd37670ae4f538a/internal_photos/bs/2026/f/k/AXxvTPSRy3iBf4jayOcw/55227748493-7951e3623d-o.jpg",
          resumo: "O ministro do MDIC e o representante comercial dos EUA se reunirão entre 30 de setembro e 1° de outubro para discutir tarifas comerciais."
        }
      ],
      IA: [
        {
          titulo: "IA pode aumentar risco de corrida por armas biológicas, dizem especialistas",
          link: "https://olhardigital.com.br/2026/09/14/inteligencia-artificial/ia-pode-aumentar-risco-de-corrida-por-armas-biologicas-dizem-especialistas/",
          imagem: "https://olhardigital.com.br/wp-content/uploads/2026/09/risco-biologico.jpg",
          resumo: "Especialistas em biossegurança alertam sobre o potencial de modelos de inteligência artificial aplicados à biologia sintética."
        }
      ]
    }
  };
}
