# Idiomas do jogo (i18n)

O jogo continua **escrito em português**. Os outros idiomas (en, es, fr, de) traduzem o texto na saída:

- `translator.ts`: procura cada texto no catálogo nesta ordem:
  1. texto exato;
  2. padrão com `{0}`, `{1}`… no lugar dos números e nomes (ex.: `"Pedido de {0} {1} confirmado!"`);
  3. o texto quebrado em frases ou separadores (`·`, `:`, quebra de linha, listas "a, b e c"), com cada pedaço procurado sozinho.

  O que não estiver no catálogo fica em português (nada quebra).
- `index.ts`: idioma atual, `t(texto)` e `localizeView` / `localizeSnapshot`.
  - O host do desktop (`desktop/host.ts`) traduz todas as páginas e snapshots antes de mandar ao Unity.
  - O host também manda o catálogo para o Unity (`kind: "i18n"`) ao conectar.
- `locales/<idioma>.ts`: catálogo `texto em português → tradução`. Um texto que fica igual no idioma pode não aparecer no arquivo.

No Unity:
- `CheckoutI18n.cs`: o mesmo tradutor em C#, mais os textos do menu inicial, que aparecem antes do host.
- `CheckoutI18nText.cs`: traduz os textos escritos no próprio C# (minigame do caixa, imprevistos, popups) antes de cada quadro.
- O idioma é escolhido no menu inicial (**Idioma**) e salvo em `PlayerPrefs` (`checkout.language`). Na primeira vez, o jogo segue o idioma do computador.
- O Unity passa o idioma ao host pela variável `CHECKOUT_LANG`.

## Textos novos

```
node scripts/i18n/missing.cjs
```

O script lista em `scripts/i18n/missing.json` os textos do código que ainda não estão em nenhum catálogo (ids e rotas também aparecem; é só ignorar). Traduza cada um e acrescente a mesma chave (o texto em português, com `{0}`…) nos quatro arquivos de `locales/`.

Dica para textos montados no código: prefira frases inteiras, por exemplo
`n === 1 ? \`${n} produto acabando\` : \`${n} produtos acabando\``,
em vez de colar pedaços de palavra (`produto${n === 1 ? "" : "s"}`), que não dão para traduzir.

## Conferir as telas montadas

```
node --import ./desktop/register.mjs scripts/i18n/scan-en.ts en
```

O `missing.cjs` só enxerga os textos escritos no código; o `scan-en.ts` confere o que o jogador vê de verdade. Ele abre o HUD e todas as páginas ligadas a ele (num jogo novo e em cada expansão, da banca ao supermercado), traduz cada página e snapshot no idioma pedido (padrão `en`) e lista em `scripts/i18n/scan-<idioma>.json` os textos que ainda saíram em português, com a página onde apareceram. Rotas (`~loja:…`, `!loja`) podem ser ignoradas. O ideal é terminar com zero; cada texto da lista pede uma entrada nova no catálogo (ou uma frase inteira no código, como na dica acima).
