---
title: Sobre os dados
---

# Sobre os dados

```js
import {LINGUAS, num, pct, pctd} from "./components/format.js";
const r = await FileAttachment("data/resumo.json").json();
const manifesto = await FileAttachment("data/manifest.json").json();
const linguas = LINGUAS.filter((l) => r.linguas.some((d) => d.codigo === l.codigo));
const por = Object.fromEntries(r.linguas.map((d) => [d.codigo, d]));
```

Este é um site estático. Os dados são baixados e processados **em tempo de build** por _data loaders_ em Python (Polars) do Observable Framework; o navegador recebe apenas arquivos Parquet/JSON prontos, e os baralhos do Anki são gerados no mesmo build. Última geração: **${new Date(r.gerado_em).toLocaleString("pt-BR")}**.

## Fontes

Nenhuma fonte exige chave ou cadastro.

| Fonte | O que usamos | Licença |
| --- | --- | --- |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018) | Quantas vezes cada forma de palavra aparece nas legendas de filmes e séries de cada língua | CC BY-SA 4.0 |
| [Wiktionary](https://en.wiktionary.org) em inglês, extraído pelo [kaikki.org](https://kaikki.org) | Qual palavra de dicionário cada forma representa, classe, gênero, pronúncia (IPA), definições, etimologia; na seção Poliglota, as tabelas de tradução e os ancestrais de cada palavra (também para o português) | CC BY-SA 4.0 |
| [Universal Dependencies](https://universaldependencies.org) (EWT, AnCora, GSD, ISDT) | Textos anotados à mão, usados para decidir formas ambíguas | CC BY-SA / CC BY / CC BY-NC-SA |
| [Tatoeba](https://tatoeba.org) | Frases de exemplo e suas traduções | CC BY 2.0 FR |

```js
Inputs.table(
  linguas.map((l) => ({lingua: l.nome, tokens: por[l.codigo].tokens, formas: por[l.codigo].formas, palavras: por[l.codigo].palavras_dicionario})),
  {header: {lingua: "Língua", tokens: "Palavras nas legendas", formas: "Formas distintas", palavras: "Palavras de dicionário encontradas"}, format: {tokens: num, formas: num, palavras: num}, sort: null, select: false, layout: "auto"}
)
```

## De formas a palavras

As listas de frequência contam formas: "estoy", "estaba" e "estuvo" aparecem separadas, e quem estuda aprende "estar". O pipeline soma as formas de cada palavra de dicionário (o *lema*), nesta ordem de decisão:

1. **Contrações partidas.** As listas separam "don't" em "don" e "'t", e "c'est" em "c'" e "est". Uma tabela fixa leva cada pedaço à palavra certa ("don" → *do*, "c'" → *ce*); sem isso, "don" contaria como o verbo inglês "vestir".
2. **Textos anotados.** Se a forma aparece pelo menos 3 vezes no corpus Universal Dependencies da língua, a contagem é dividida como os anotadores a classificaram lá: "anda" é quase sempre *andar*; "como" é na maior parte a conjunção, e um pouco *comer*.
3. **Wiktionary.** Senão, uma forma com definições próprias conta para si mesma, a não ser que seja também flexão de outra palavra e tenha um único sentido ("flores" vai para *flor*, não para o sentido raro "menstruação"). Uma forma que é só flexão divide a contagem igualmente entre as palavras de que deriva ("fue" → metade *ser*, metade *ir*).
4. **Nomes próprios e palavras desconhecidas** continuam no total de palavras (são parte do que se ouve), mas nunca entram na lista para estudar nem contam como "reconhecidos".

As 50 mil formas mais frequentes de cada língua passam por essas regras; as demais, raras, contam cada uma como palavra própria.

```js
Inputs.table(
  // Languages without contraction rules have no "contração" key: show 0 %.
  linguas.map((l) => ({lingua: l.nome, "contração": 0, ...por[l.codigo].status_formas})),
  {
    header: {lingua: "Língua", lema: "Já é a palavra", "flexão": "Flexão", "contração": "Contração", "nome próprio": "Nome próprio", "fora do dicionário": "Fora do dicionário"},
    format: {lema: pctd, "flexão": pctd, "contração": pctd, "nome próprio": pctd, "fora do dicionário": pctd},
    columns: ["lingua", "lema", "flexão", "contração", "nome próprio", "fora do dicionário"],
    sort: null,
    select: false,
    layout: "auto"
  }
)
```

<p class="muted small">Parcela de todas as palavras das legendas, por como cada forma foi resolvida (só as 50 mil formas mais frequentes).</p>

## Definições e pronúncia

As definições são as do Wiktionary em inglês, como estão escritas lá, sem tradução. Quando uma palavra tem várias entradas (Wiktionary separa "de" preposição de "de", nome da letra D), a ordem segue a classe que a palavra tem com mais frequência nos textos anotados, e entradas de letras, notas musicais e afixos vão para o fim. A pronúncia é a primeira transcrição fonêmica do Wiktionary; no inglês, a americana quando marcada.

## Frases de exemplo

Para cada palavra, entre as frases do Tatoeba que contêm uma das suas formas (de 3 a 14 palavras), a escolhida é a que mais se aproxima do princípio "*i*+1": todas as outras palavras da frase devem ser mais frequentes que a palavra estudada, então quem estuda na ordem de frequência já conhece o resto. A preferência é, em ordem: tradução para o português; dificuldade ao alcance (a palavra mais rara da frase não passa da posição da própria palavra, ou das 300 primeiras); tamanho perto de oito palavras. Sem tradução para o português, vale a tradução para o inglês. Nomes próprios, como o onipresente "Tom" do Tatoeba, contam como conhecidos.

```js
Inputs.table(
  linguas.map((l) => ({lingua: l.nome, com_frase: por[l.codigo].com_frase / r.palavras_por_lingua, pt: por[l.codigo].frase_traduzida_pt / por[l.codigo].com_frase, alcance: por[l.codigo].frase_ao_alcance / por[l.codigo].com_frase, ipa: por[l.codigo].com_ipa / r.palavras_por_lingua})),
  {header: {lingua: "Língua", com_frase: "Palavras com frase", pt: "Frase traduzida para o português", alcance: "Frase ao alcance", ipa: "Palavras com IPA"}, format: {com_frase: pct, pt: pct, alcance: pct, ipa: pct}, sort: null, select: false, layout: "auto"}
)
```

## Poliglota

**Conceitos.** Cada uma das 5.000 palavras mais frequentes do inglês (com a sua classe principal) é um conceito. As palavras equivalentes em português, espanhol, francês, italiano e alemão vêm da tabela de tradução dessa entrada do Wiktionary, só da mesma classe. As tabelas têm sentidos raros misturados ("dog" lista *vaca*, uma gíria), então uma palavra só é aceita se estiver entre as 10.000 mais frequentes da sua língua (no português, entre as 30.000 formas mais frequentes das legendas). Entre as candidatas, vence a que tem o conceito na primeira definição ("aller": "to go"), depois a que o tem em qualquer definição, a mais frequente primeiro. Uma candidata cuja definição não confirma o sentido só entra se for uma das duas primeiras da tabela. Sem candidata, vale a palavra mais frequente da língua cuja primeira definição é o conceito.

**Semelhança.** Os acentos são ignorados. *Igual*: mesma grafia. *Parecida*: uma letra de diferença (palavras com pelo menos 2 letras), ou, com 4 letras ou mais, distância de edição de no máximo metade do comprimento da palavra mais longa. *Mesma origem*: um ancestral em comum na etimologia do Wiktionary (latim, protogermânico…, mas não o proto-indo-europeu, que aproximaria quase tudo), ou uma palavra citada como ancestral ou cognata da outra.

**Vantagem.** Para a língua B e a língua de partida A: soma das ocorrências nas legendas de B das palavras de B (entre as 5.000 mais frequentes) cuja equivalente em A é igual ou parecida, dividida pelo total de palavras ditas em B. Se uma palavra de B aparece em vários conceitos, vale a melhor semelhança.

**Falsos amigos.** Duas palavras entre as 5.000 mais frequentes das suas línguas, com a mesma grafia sem acentos (pelo menos 3 letras), que não estão ligadas por nenhum conceito e cujas definições não têm nenhum sentido em comum (comparando os pedaços curtos das definições em inglês, inclusive por prefixo: "photo" e "photograph"). Ficam de fora os pares em que uma das definições é a própria palavra (empréstimos como o italiano *okay*) e os pares de flexões de verbos parecidos (*visto* em espanhol e em italiano).

## Limitações

- Legendas são fala roteirizada, com mais diálogo, palavrões e "hey" que a conversa real; também incluem trechos em outras línguas e erros de reconhecimento de texto.
- O pipeline não separa sentidos: "banco" de sentar e "banco" de dinheiro contam juntos.
- Algumas regras de decisão erram em casos raros (por exemplo, formas pouco frequentes nos textos anotados que são ao mesmo tempo palavra e flexão).
- O tratamento de maiúsculas é simples: as listas vêm em minúsculas, então "Essen" (comida) e "essen" (comer) do alemão se juntam.
- A licença do corpus italiano (ISDT) é não comercial; este site não tem fins comerciais.
- Na seção Poliglota, as palavras gramaticais (pronomes, artigos, verbos auxiliares) se alinham mal: "you" não tem um equivalente único em espanhol, e o "will" do futuro inglês não existe como palavra nas outras línguas. Os conceitos começam a ficar confiáveis a partir dos substantivos, verbos e adjetivos comuns.
- A vantagem mede reconhecimento na escrita. Pronúncia, gênero e falsos amigos parciais (a mesma palavra com um sentido em comum e outro diferente) ficam de fora.

## Versão dos dados

Cada build publica um manifesto com a versão do código, a data de download de cada fonte e contagens por língua, também em `/manifest.json`, num endereço fixo, para comparar cada atualização com a anterior (${html`<a href=${FileAttachment("data/manifest.json").href}>ver o arquivo</a>`}).

<p class="muted">Código do pipeline: <code>${manifesto.codigo_pipeline}</code>${manifesto.commit ? html` · commit <a href=${`https://github.com/davipferr/words-worth-learning/commit/${manifesto.commit}`}><code>${manifesto.commit.slice(0, 7)}</code></a>` : ""}</p>
