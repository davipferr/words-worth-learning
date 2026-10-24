---
title: Conceitos lado a lado
toc: false
---

# Conceitos lado a lado

O mesmo conceito em oito línguas, na ordem de frequência do inglês. A cor diz quanto cada palavra se parece com a portuguesa.

```js
import {parquet} from "../components/parquet.js";
import {num, resultados, rows} from "../components/format.js";
import {palette} from "../components/palette.js";
import {ALVOS, CLASSES, corClasse, NOMES} from "../components/poliglota.js";
import {baixar, tsvPoliglota} from "../components/exportar.js";

const conceitos = rows(await parquet(FileAttachment("../data/poliglota/conceitos.parquet")));
const baralho = FileAttachment("../data/poliglota/poliglota.apkg");
const pal = palette(dark);
const cor = corClasse(pal);
```

```js
html`<div class="legend-row">${CLASSES.map((c) => html`<span><i style=${{background: cor[c]}}></i>${c === "diferente" ? "diferente do português" : c}</span>`)}</div>`
```

```js
const filtros = view(
  Inputs.form(
    {
      completos: Inputs.toggle({label: "Só com palavra em todas as línguas", value: true}),
      lingua: Inputs.select(new Map([["qualquer língua", null], ...ALVOS.filter((c) => c !== "en").map((c) => [NOMES[c], c])]), {label: "Igual ou parecida em"}),
      classes: Inputs.select(new Map([["Todas", null], ["Substantivos", "noun"], ["Verbos", "verb"], ["Adjetivos", "adj"], ["Advérbios", "adv"]]), {label: "Classe"})
    },
    {template: (inputs) => html`<div class="filtros">${Object.values(inputs)}</div>`}
  )
);
```

```js
const filtrados = conceitos.filter(
  (d) =>
    (!filtros.completos || (d.palavra_pt && d.n_linguas === ALVOS.length - 1)) &&
    (!filtros.classes || d.classe === filtros.classes) &&
    (!filtros.lingua || ["igual", "parecida"].includes(d[`vs_pt_${filtros.lingua}`]))
);
const busca = view(Inputs.search(filtrados, {placeholder: "Buscar em qualquer língua…", columns: ["conceito", "palavra_pt", "palavra_es", "palavra_fr", "palavra_it", "palavra_de", "palavra_ja", "palavra_zh"], format: resultados, width: 320}));
```

```js
// A word coloured by its class against Portuguese.
function celula(code) {
  return (palavra, i, data) => {
    const span = document.createElement("span");
    span.textContent = palavra ?? "—";
    const c = data[i]?.[`vs_pt_${code}`];
    if (palavra && c) {
      span.style.color = c === "diferente" ? "inherit" : cor[c];
      if (c !== "diferente") span.style.fontWeight = 600;
      span.title = c;
    }
    return span;
  };
}
```

```js
Inputs.table(busca, {
  columns: ["rank_en", "palavra_pt", "palavra_en", "palavra_es", "palavra_fr", "palavra_it", "palavra_de", "palavra_ja", "palavra_zh", "classe_pt"],
  header: {rank_en: "Nº", palavra_pt: "Português", palavra_en: "Inglês", palavra_es: "Espanhol", palavra_fr: "Francês", palavra_it: "Italiano", palavra_de: "Alemão", palavra_ja: "Japonês", palavra_zh: "Chinês", classe_pt: "Classe"},
  format: {rank_en: num, palavra_en: celula("en"), palavra_es: celula("es"), palavra_fr: celula("fr"), palavra_it: celula("it"), palavra_de: celula("de"), palavra_ja: celula("ja"), palavra_zh: celula("zh")},
  width: {rank_en: 56},
  sort: "rank_en",
  rows: 20,
  select: false,
  locale: "pt-BR"
})
```

<p class="muted small">Nº: posição da palavra inglesa em frequência, que dá a ordem dos conceitos. Uma palavra entre as 10.000 mais comuns da sua língua só entra se a tabela de tradução do Wiktionary a lista e, de preferência, se a sua própria definição confirma o sentido; quando não há uma assim, a célula fica vazia.</p>

## Baralho para o Anki

Um cartão por conceito: na frente, a palavra em português; no verso, as sete línguas, cada uma com a pronúncia e a marca de semelhança com o português, e lidas em voz alta pelo Anki. Os cartões novos seguem a ordem de frequência e têm identificadores fixos, como os baralhos da seção [Vocabulário](../vocabulario/anki).

```js
html`<p><a class="botao" href=${baralho.href} download="poliglota.apkg">Baixar o baralho Poliglota (${num(conceitos.filter((d) => d.palavra_pt).length)} conceitos)</a></p>`
```

```js
const exportar = view(Inputs.button(`Baixar os ${num(busca.length)} conceitos filtrados (.txt para o Anki)`, {value: null, reduce: () => baixar("poliglota.txt", tsvPoliglota(busca))}));
```

<p class="muted small">O verso lê as sete palavras em sequência; para ouvir uma de cada vez, desligue a reprodução automática nas opções do baralho e clique no ícone de som de cada língua.</p>

<style>
.filtros { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
.filtros form { margin: 0; }
.botao { display: inline-block; padding: 0.45rem 0.9rem; border: 1px solid var(--theme-foreground-focus); border-radius: 6px; text-decoration: none; }
.legend-row i { border-radius: 50%; }
</style>
