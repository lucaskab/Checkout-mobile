# Evoluções dos móveis (tiers visuais)

Ideia da Mari (30/10): além das expansões do mercado, os **móveis de dentro** também evoluem visualmente (prateleiras, geladeiras, freezers, setores, caixa, caixa eletrônico...), para o jogador ter onde gastar e **ver** o mercado melhorando. E os móveis das lojas pequenas (Conveniência, Quitanda) começam **menores**, porque hoje já nascem do tamanho de supermercado e ficam apertados.

Status (30/10, rodada 3):

| Situação | Itens |
|---|---|
| ✅ **Aprovados e exportados para o Unity** | gôndola, caixa, geladeira de bebidas, laticínios (com o T4 novo), congelados, sorvetes, padaria, hortifrúti, câmara fria, cestinha / carrinho / carrinho grande, caixa eletrônico, máquina de chiclete, máquina de pelúcia |
| 🔁 **Refeitos nesta rodada** | os 7 setores especiais, com muito mais detalhe (produtos de verdade, textura pintada e objetos de cada setor) |
| 📍 **Câmara fria** | do lado de fora, colada no depósito / armazém central |

Os FBX dos aprovados estão em `ArtSource/fixture_tiers/export/`, com um README de pivô, pegada e materiais.

**Implementação:** está no branch `fixture-tiers-impl`. A seção 5 mostra o que entrou e o que mudou em relação à proposta.

---

## 1. O que outros jogos fazem (pesquisa)

| Jogo | Como o móvel/estação evolui | O que aprendemos |
|---|---|---|
| Idle Supermarket Tycoon (Codigames) | Cada departamento, caixa e estacionamento sobe de nível; "Epic upgrades" permanentes custam gemas ([Gamezebo](https://www.gamezebo.com/walkthroughs/idle-supermarket-tycoon-guide-tips-cheats-and-strategies/)) | Upgrade por estação + upgrade premium em diamante |
| Cooking Fever (Nordcurrent) | Cada aparelho tem poucos níveis (tempo menor); decoração dá clientes extras, paciência e gorjeta; seta vermelha piscando indica o upgrade recomendado ([TouchTapPlay](https://www.touchtapplay.com/cooking-fever-cheats-tips-tricks-strategy-guide/)) | Poucos níveis bem visíveis; o jogo **aponta** o próximo upgrade |
| Hay Day (Supercell) | Máquinas ganham vagas de produção com diamantes; a "maestria" (72 h / 288 h / 1.152 h de produção) dá +10% moedas, +5% XP e −15% tempo, e a máquina ganha estrelas ([Hay Day Wiki](https://hayday.fandom.com/wiki/File:Candy_Machine_Mastered.png)) | 3 marcos grandes, com recompensa e selo visual |
| My Perfect Hotel (SayGames) | Camas, TVs e banheiros dos quartos sobem de nível e o quarto rende mais por hóspede; "escolha entre vários designs de quarto" ([guia](https://www.whisperofthehouse.com/my-perfect-hotel), [App Store](https://apps.apple.com/app/id1635760774)) | O jogador **vê** o quarto mudar: é isso que dá vontade de gastar |
| Idle Bank / Idle Miner (Kolibri) | Cada estação sobe de nível no ponto que trava o fluxo, tudo visível numa tela só ([GameAnalytics](https://www.gameanalytics.com/blog/making-a-hit-idle-game-eight-lessons-from-kolibri-games), [PocketGamer.biz](https://www.pocketgamer.biz/game-analysis-deconstructing-idle-bank-tycoon-by-kolibri-games/)) | Muitos níveis pequenos de número; a cada marco, um salto visual |
| Supermarket / Hypermarket Simulator (PC) | Não evolui: compra-se outro móvel maior; capacidade depende do tipo ([guia Steam](https://steamcommunity.com/sharedfiles/filedetails/?id=3378008529)). Jogadores reclamam quando o móvel "grande" guarda pouco ([fórum Steam](https://steamcommunity.com/app/3614460/discussions/0/841754922594830571/)) | O **tamanho tem que combinar com a capacidade**; móvel maior precisa de espaço livre |

Padrões que vamos seguir:
1. **3 a 5 visuais por móvel.** O número muda a cada compra, mas o visual só muda nos marcos.
2. **Custo cresce uns ×3 a ×5 por tier**, e o último degrau também pode ser comprado com diamantes.
3. **Mostrar o próximo visual antes de pagar**, indicar o upgrade recomendado e comemorar a evolução.
4. **Tamanho = capacidade.** Um móvel maior pede espaço livre: mostrar o fantasma verde ou vermelho antes de pagar.

(Não deu para abrir as páginas da wiki de maestria do Hay Day, da wiki de móveis do Supermarket Simulator nem da appgamer sobre o My Perfect Hotel. A comparação com Idle Miner, Cooking Fever e o PC Simulator vem do que se sabe desses jogos.)

---

## 2. O que existe hoje no jogo (inventário)

**Uma correção:** o "Nível x/10 · Subir de nível (+10% de lucro)" é o **nível do produto** (`src/services/product-levels.ts`, `desktop/pages/shelves.ts:199`), e não do móvel. Ele continua como está. Por móvel já existem **duas** progressões, e elas são a base desta proposta:

- **Capacidade por produto** `shelfUpgradeLevels[shelfId]` (`src/data/shelf-capacity.ts`): 5 → 10 → 15 → 20 → 25 unidades. Custa 1.200 / 6.000 / 22.000 / 70.000 moedas, ou 6 / 14 / 28 / 48 💎, a partir dos níveis 4 / 8 / 14 / 22.
- **Lugares de produto** `shelfSlotCounts[shelfId]`: 4 → 5 → 6 → 7 produtos, por 600 / 2.500 / 9.000 moedas, a partir dos níveis 3 / 6 / 10.

Hoje nenhuma das duas muda o visual do móvel.

| Coisa | Onde está | Hoje | Modelo / pegada (Kit) |
|---|---|---|---|
| Hortifrúti `produce` | `src/data/shelf-types.ts` | Caixotes (mesinha) → Banca de hortifrúti (banca); grátis | `shelf-produce` 1,9 × 1,1 m |
| Bebidas `drinks` | idem | Isopor com gelo → Geladeira de bebidas (contêiner); grátis | `shelf-cooler` 1,9 × 0,84 m |
| Padaria `bakery` | idem | Cesto de pães (tenda) → Prateleira da padaria (Conveniência); 300 | `bread-basket` 1,0 × 0,72 m / `shelf-bakery` 1,9 × 0,85 m |
| Laticínios `dairy` | idem | Expositor refrigerado (banca) → Geladeira (Conveniência); 1.500 | `shelf-dairy` 1,9 × 0,92 m |
| Doces `snacks` | idem | Prateleira de doces (contêiner) → Gôndola (Conveniência); 3.000 | gôndola de corredor 2,84 × 0,96 m (o `rk_gondola`), reserva 1,9 × 0,66 |
| Mercearia `coffee` | idem | Gôndola de mercearia (Conveniência); 6.000 | idem |
| Congelados `pizza` | idem | Freezer de congelados (Quitanda); 12.000 | `shelf-freezer` 1,9 × 0,96 m |
| Casa e higiene `home` | idem | Gôndola (Minimercado); 20.000 | gôndola |
| Sorvetes `icecream` | idem | Freezer horizontal (Supermercado); 40.000 | `shelf-freezer` |
| 7 setores (padaria, queijaria, açougue, sucos, peixaria, sorvetes, adega) | `production-sectors.ts`, `sectorCounters` | Abrem do Mercadinho ao Hiper; 2–3 vagas de produção | balcões 3,96 × 3,36 m (os de atendente), 3,3 × 2,4 m nos outros |
| Caixa `checkout:main` / `checkout:extra` | `CheckoutInteriorKitBuilder.CheckoutCounter` | Upgrades separados na Loja: Caixa Extra 8k, Esteira 12k (×1,25), Leitor 30k (×1,25), Caixa Dourado 120 💎 (×1,5) | 2,5 × 1,7 m (com o lugar do operador); **o modelo tem a palavra "CAIXA" escrita** (`KLetters`) |
| Autoatendimento `kiosk:1/2` | Loja: 70k + 300k | 2 totens | 1,57 × 0,68 m |
| Caixa eletrônico `atm` | `interior-decor.ts` | 15k, clientes gastam +15% | 0,74 × 0,84 m |
| Máquinas de jogar (chiclete, bebidas, pelúcia, fotos, quiosque de café) | `interior-decor.ts` (`effect.play`) | moedas por jogada, até 2–3 de cada | 0,7–1,3 m |
| Carrinhos | Cestinhas 800 (Loja) → `cart-corral` 4k (mapa) → Carrinhos Grandes 22k (Loja) | três compras soltas | corral |
| Registradora das lojas pequenas | modelo da loja (`NEW_ERA4_Counter_Register`…) | fixa no balcão na Conveniência e na Quitanda (`CheckoutStall.PlacedCounter = false`) | – |

**Grade de construção:** as bordas encaixam em quadrados de 0,25 m (`CheckoutInterior.Square`). A pegada vem de `CheckoutInteriorPiece.min/max`, e `Fits()` / `Settle()` já testam e corrigem a colisão.

**Tamanho das lojas** (piso do modelo × 1,2 no jogo, `CheckoutStall` Plans):

| Loja | Piso no jogo | Área |
|---|---|---|
| Conveniência | 8,5 × 4,9 m (balcão fixo de 2,1 × 1,7 m) | ~42 m² |
| Quitanda | 9,8 × 7,8 m | ~77 m² |
| Minimercado | 14,2 × 8,8 m (o caixa já é móvel posto) | ~124 m² |

Na Conveniência entram 6 móveis de 1,9–2,84 m (~13 m² só de móveis). Por isso fica apertado: veja `conveniencia_fit_hoje.jpg`.

---

## 3. Proposta

### 3.1 Regra geral
- Cada móvel tem **4 visuais (T1–T4)** e mais um **acabamento premium ★** no fim. As bancas das primeiras expansões (mesinha → contêiner) continuam com os objetos do próprio modelo (caixote, isopor, cesto): é o **"T0"**, que não se põe nem se move.
- **Evoluir = o upgrade de capacidade que já existe**, com outro nome e visual novo. Os preços, os diamantes e os níveis de jogador ficam **iguais aos de hoje**, então o balanço não muda (o robô de economia nem simula capacidade):

| Tier | Unidades por produto | Preço | 💎 | Nível do jogador | Visual liberado a partir de |
|---|---|---|---|---|---|
| T1 | 5 | compra do móvel | – | – | Conveniência |
| T2 | 10 | 1.200 | 6 | 4 | Conveniência |
| T3 | 15 | 6.000 | 14 | 8 | **Minimercado** |
| T4 | 20 | 22.000 | 28 | 14 | **Mercadinho** |
| T4 ★ acabamento premium | 25 | 70.000 | 48 | 22 | **Supermercado** |

- **O tamanho acompanha a loja.** Conveniência e Quitanda mostram no máximo o T2 (são lojas pequenas), o Minimercado o T3, o Mercadinho o T4 e o Supermercado em diante o ★. Quem comprou capacidade antes **mantém os números**. O visual maior aparece sozinho quando a loja cresce ("Seus móveis evoluíram!"), se houver espaço.
- **Lugares de produto** (4 → 7) continuam num botão próprio ("Mais um produto"), mas com um limite pelo tamanho: T1 até 5, T2 até 6, T3/T4 até 7. Quem já tem mais fica com o que tem.
- O texto "Nível do produto x/10" continua igual: é outra coisa.

### 3.2 Itens e tiers (pegada em metros, grade de 0,25 m)

**Prateleiras / gôndolas** (mercearia, doces, casa e o "seco" da padaria). Já modeladas, ver os renders:

| Tier | Nome (pt-BR) | Pegada | Altura | Visual |
|---|---|---|---|---|
| T1 | Estante de madeira | 1,00 × 0,50 | 1,45 | laterais pintadas de navy, 3 tábuas de madeira, fundo de ripas, cestos de vime, plaquinha de giz em branco |
| T2 | Estante grande de madeira | 1,50 × 0,50 | 1,75 | colunas de madeira, painéis navy, fundo de tábuas, 4 níveis, coroa navy com filete dourado e placa creme (pictograma do jogo), caixotes |
| T3 | Gôndola de metal | 2,00 × 0,75 | 1,88 | estrutura navy, fundo perfurado, prateleiras de aço escovado, canaletas de preço, laterais arredondadas, testeira |
| T4 | Gôndola iluminada | 2,50 × 1,00 | 2,08 | ilha dupla (dois lados), espinha de inox, frente de vidro, LED quente em cada prateleira, etiquetas eletrônicas, pontas com promoção e bandeiras com disco iluminado |
| ★ | Gôndola iluminada premium | igual ao T4 | | filetes dourados, rodapé de LED e cor de destaque (pinta com "Cores do mercado") |

**Outros móveis de produto** (mesma tabela de preços; **lote A modelado em 30/10**, ver seção 4):

| Móvel | T0 (bancas) | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|
| Hortifrúti | caixotes | Banca de caixotes 1,0 × 0,75 (cavalete, 3 caixotes inclinados, cestos de batata e cebola, plaquinha de giz) | Banca inclinada de madeira 1,5 × 0,75 (6 caixotes em degraus, toldo navy recortado, filete dourado) | **Banca em degraus** 2,0 × 1,0 (rodada 2: 3 degraus de caixotes inclinados, tulhas de batata e cebola nas pontas, fundo de ripas de madeira com maços de ervas pendurados e cestos, coroa navy) | Ilha refrigerada com névoa 2,5 × 1,25 (rodada 2: montes mais fartos, caixotes de madeira + cubas de inox + cestos de vime, degrau central com melões e laranjas, cones de névoa visíveis, cobertura navy em arco com pendentes e filete dourado) |
| Bebidas | isopor com gelo | Geladeira de 1 porta 0,75 × 0,75 | Geladeira de 2 portas 1,25 × 0,75 (moldura creme) | Geladeira de 3 portas 2,0 × 0,75 (moldura inox, LED) | Parede de portas com LED 2,5 × 1,0 (4 portas, sanca navy iluminada, base inox) |
| Laticínios e frios | expositor da banca | Expositor refrigerado pequeno 1,0 × 0,75 (2 degraus, vidro) | Balcão refrigerado 1,5 × 0,75 (vidro curvo, frente de madeira, queijos, salames, presunto) | Expositor aberto (multideck) 2,0 × 1,0 (cortina de ar, persiana noturna) | **Ilha de laticínios e frios** 2,5 × 1,0 (rodada 2: ilha baixa e aberta dos dois lados, 3 degraus subindo para o centro com iogurtes, leites e queijos, tábua no topo com queijos e salames, ponta de frios com redoma de vidro, cobertura com LED; não se parece mais com a parede de geladeiras) |
| Padaria | cesto de pães | Estante de pães 1,0 × 0,5 (cestos de vime inclinados, baguetes) | Estante de cestos inclinados 1,5 × 0,5 (croissants, pães, filões, coroa navy) | Vitrine de acrílico 2,0 × 0,75 (parede de caixas de acrílico, bolos com redoma) | Vitrine aquecida iluminada 2,0 × 1,0 (3 bandejas com LED quente, ripado) |
| Congelados | – | Freezer horizontal pequeno 1,0 × 0,75 (tampas de vidro corrediças) | Freezer horizontal grande 1,5 × 0,75 | Freezer vertical de 2 portas 1,5 × 0,9 (vidro com borda de gelo) | Ilha de congelados 2,5 × 1,25 (ripado, cobertura com LED frio) |
| Sorvetes (chega no Supermercado) | – | Freezer de sorvetes 1,0 × 0,75 (cúpula de vidro, potes de todos os sabores, emblema de casquinha) | Freezer de sorvetes grande 1,5 × 0,75 | Ilha de sorvetes 2,0 × 1,0 | Vitrine de gelato 2,5 × 1,0 (vidro curvo, cubas de inox com sabores, casquinhas) |

Sorvetes ganharam um T1 pequeno, porque o tier vem da capacidade (nível 0 = T1) e assim a tabela fica igual para todos. O tamanho máximo na loja segue a mesma regra (Supermercado = até ★).

"Refrigeração Eficiente" e "Congelamento Rápido" (Loja) passam a aparecer em **todas** as geladeiras e freezers: borda de gelo e LED frio.

**Caixa** (já modelado):

| Tier | Nome | Pegada (balcão + operador) | Efeito | Preço | Onde |
|---|---|---|---|---|---|
| T1 | Caixinha no balcão | 1,25 × 1,25 | ×1 | inicial | Na Conveniência e na Quitanda é a **registradora em cima do balcão fixo** que evolui (T1 → T2) |
| T2 | Caixa registradora | 1,75 × 1,50 | atendimento ×1,1 | **3.000** (ou 10 💎), nível 8 | primeiro caixa posto no Minimercado |
| T3 | Caixa com esteira | 2,50 × 1,75 (o de hoje) | ×1,25 = a "Esteira no Caixa" de hoje (12.000, nível 13) | | |
| T3 + leitor | (scanner aparece) | igual | ×1,25 = o "Leitor de Código de Barras" de hoje (30.000, nível 21) | | |
| T4 | Caixa premium | 3,00 × 1,75 | ×1,2 e fila espera +15% | **90.000** (ou 90 💎), nível 30, Supermercado | |

- O tier vale para **todos os caixas** (o Caixa Extra nasce no mesmo tier). O "Caixa Dourado" (120 💎) continua como está e põe aro dourado no poste da fila e nos trilhos da esteira.
- **Dinheiro novo gasto:** só o T2 (3.000) e o T4 (90.000 ≈ 1,4 h de vendas no Supermercado, dentro da regra da Loja de "~2 h de vendas"). A esteira e o leitor deixam de ser itens soltos na Loja e viram degraus do caixa.

**Setores especiais (rodada 2, todos refeitos).** O Lucas achou que, no lote B, os sete "ficaram todos iguais, perderam a identidade". A base agora é a identidade que cada setor já tem no jogo (ver `Resources/CheckoutDesktop/Decor/sector-*.png`). Cada tier é o mesmo setor, maior e melhor:

| Tier | Pegada |
|---|---|
| T1 | 2,5 × 2,0 m |
| T2 | 3,25 × 2,5 m |
| T3 | 4,0 × 3,25 m (≈ o balcão de hoje, 3,96 × 3,36) |

| Setor | O que faz ser ele (silhueta e material) | T1 | T2 | T3 |
|---|---|---|---|---|
| Padaria | parede de tijolo, **forno a lenha de cúpula** com boca acesa, paneleiras de madeira, sacos de farinha | forno pequeno, paneleira, balcão de madeira com cestos | forno maior no centro, duas paneleiras, balcão + vitrine de bolos, pendentes | arco de tijolo, forno grande, duas estantes de assadeiras de inox, vitrine aquecida longa, pirâmide de sacos |
| Açougue | **azulejo branco**, trilho de inox com peças e linguiças penduradas, cepo de madeira, vitrine refrigerada de carnes | cepo, vitrine refrigerada, balança | dois cepos, moedor, barra de facas, vitrine longa | **câmara de maturação** (armário de vidro aceso com peças), arco navy, vitrine de 2,9 m |
| Queijaria | **cave**: reboco e madeira escura, **estantes de rodas de queijo**, provolones pendurados em viga | estante de rodas, balcão de madeira escura com queijos e redoma, viga com 4 provolones | arco de pedra, duas estantes altas, vitrine de vidro reto, viga com 7 provolones | arco de pedra, três estantes até o teto, balcão de degustação com tábuas, pirâmide de rodas |
| Peixaria | **azulejo azul e branco**, **cama de gelo inclinada** com peixes e limões, caixotes, balança pendurada, rede | bancada de gelo, caixotes, balança, rede | bancada longa com frente de mosaico, pia, rede de pesca | ilha de gelo em dois degraus, **aquário de lagostas**, rede, pendentes |
| Sorveteria | sorveteria clássica: **toldo listrado navy/creme**, vitrine curva de gelato com cubas, **porta-casquinhas** | vitrine curta, porta-casquinhas, potes de cobertura | vitrine longa, máquina de sorvete expresso, balcão de fundo com potes de cobertura | dois expressos, nichos acesos com taças, mesinha com duas cadeiras de arame |
| Adega | **parede de nichos de vinho** (madeira escura), **barris**, balcão de degustação | estante de nichos + barril-mesa com taças + caixote de garrafas | 3 vãos de nichos, balcão sobre dois barris, barris deitados no berço | **cave de tijolo** com nichos iluminados, pirâmide de barris, balcão ripado com tampo de mármore, bancos, porta-taças |
| Sucos | **frente de frutas** (caixotes inclinados cheios), dispensers de suco, liquidificadores | barraca de madeira com frutas na frente, 2 dispensers, liquidificador, cestos na parede | balcão navy com frutas na frente, 3 dispensers, 2 liquidificadores, prateleiras de caixotes, redes de laranja | **bar de sucos** com 4 bancos, 4 dispensers, cascata de frutas na parede, moldura com pendentes |

- **Cor:** a cor de cada setor vem só de material e produto (tijolo, azulejo, carne, peixe, frutas, vinho). A estrutura é navy, creme, dourado e madeira, sem "salada de cor".
- **Efeito e preço** continuam como na proposta: T2 dá **+1 vaga de produção**, T3 dá **−20% de tempo** e +10% no preço. Preços T2 / T3: 18k / 55k no Mercadinho, 30k / 90k no Supermercado, 70k / 200k no Hiper (ou 30 / 80 💎).
- **Saves:** setor já construído vira T1 (sem perder nada). Como o T1 é menor que o balcão de hoje, ele sempre cabe.

**Setores, rodada 3: mais detalhe.** O Lucas achou que os setores ainda estavam "muito básicos, muita forma geométrica, sem detalhe, sem textura". Mantive a mesma planta e os mesmos tamanhos da rodada 2 e troquei o que está dentro:
- **Produtos com forma de verdade e textura pintada.** Todos vêm de um atlas novo, `FT_Sector_albedo.png` (8 × 8 células, sem nenhuma letra).

  | Setor | Produtos |
  |---|---|
  | Padaria | pão com cortes e casca dourada, bola com cruz e farinha, baguete com cortes, croissant em camadas, pãozinho, bolos com cobertura escorrendo e confeitos, sacos de juta com estêncil |
  | Açougue | bife com marmoreio e capa de gordura, T-bone com o osso, costela com ossos aparentes, bisteca, linguiça em gomos, frango (cru na vitrine, assado no forno de frango do T3), carne moída, presunto curado na rede |
  | Queijaria | roda com casca (cera, natural, parmesão com pontinhos, brie) e fatia tirada mostrando a massa com olhos, queijo azul, cunhas, provolone com corda, uvas, mel |
  | Peixaria | peixe com nadadeiras, olho, escamas e degradê do dorso para a barriga, camarão, lagosta, mexilhões, posta de salmão, limão cortado, gelo moído texturizado |
  | Sorveteria | cubas com sorvete em redemoinho e cobertura (pistache, chocolate, morango, creme, menta, manga, frutas vermelhas), casquinha de waffle, bolas, taça, potes de confeito |
  | Adega | garrafas com cápsula e rótulo só com pictograma, taças com vinho, decanter, rolhas, caixotes de vinho, balde de gelo, parede de garrafas pintada |
  | Sucos | laranja com folha, maçã, limão, kiwi, morango, abacaxi com coroa, melancia inteira e em fatia, bananas, frutas cortadas, jarra com gelo e rodelas, copos com canudo |

- **Objetos de cada setor:**
  - quadro-negro com pictogramas (em pé ou na parede);
  - plaquinhas de preço em branco;
  - balança;
  - fatiador de frios;
  - rolo de papel;
  - barra imantada de facas e cutelo;
  - aventais no gancho;
  - prateleiras com potes, garrafas e latas;
  - plantas (ervas e oliveira em vaso de terracota);
  - lenha;
  - pás de forno;
  - porta de ferro do forno;
  - boias e corda;
  - rede;
  - aquário de lagostas;
  - toldo listrado com babado;
  - "neon" de casquinha;
  - mesinha de gelateria;
  - bancos;
  - parreira com uvas;
  - pendentes com lâmpada quente.
- **Superfícies com textura:** tijolo (agora em fiadas que seguem a cúpula do forno), azulejo com rejunte, mármore, inox escovado, madeira e juta.
- **Câmera do jogo:** cada setor tem uma foto de cima (`sector-<id>_T3_topdown.jpg`). Os pendentes foram para o fundo, para não cobrir os produtos.
- **Triângulos (T1 / T2 / T3):**

  | Setor | T1 | T2 | T3 |
  |---|---|---|---|
  | Padaria | 10,2k | 16,2k | 24,4k |
  | Açougue | 10,3k | 16,7k | 22,7k |
  | Queijaria | 8,3k | 19,0k | 25,1k |
  | Peixaria | 11,7k | 13,9k | 26,3k |
  | Sorveteria | 9,6k | 14,5k | 19,9k |
  | Adega | 8,4k | 15,3k | 20,3k |
  | Sucos | 13,9k | 21,2k | 24,8k |


**Caixa eletrônico (rodada 2, refeito para parecer caixa de banco de verdade).** Cada máquina tem:
- frente creme e corpo navy;
- **cobertura inclinada** sobre a tela acesa em branco;
- **cartão** com luz verde e **comprovante**;
- **teclado** com protetor;
- **saída de dinheiro** cromada;
- **asas laterais de privacidade**;
- caixa de luz no topo (em branco).

| Tier | Nome | Pegada | Efeito | Preço |
|---|---|---|---|---|
| T1 | Caixa eletrônico (de pé) | 0,75 × 0,85 | +15% | o de hoje, 15k |
| T2 | Dois caixas na parede | 1,5 × 0,85 | +20% | 45k |
| T3 | Sala de autoatendimento bancário | 2,25 × 1,5 | +25% | 120k |

T2 é um painel navy com testeira acesa e uma bancada. T3 tem 3 caixas numa parede creme, laterais de vidro e cobertura navy com LED. Mantive **3 tiers** porque cada um muda de forma e de lugar (de pé → na parede → sala). Não é só "mais máquinas", e o T3 vira um canto do mercado.

**Máquina de chiclete (rodada 2): só 2 tiers.** A torre saiu.

| Tier | Como é | Pegada | Efeito | Preço |
|---|---|---|---|---|
| T1 | pedestal de três pés estilo ferro fundido, corpo navy com faixas douradas, moedeiro com manivela, saída com tampinha, globo de vidro cheio | 0,5 × 0,5 | – | 2,2k (hoje) |
| T2 | coluna que abre em dois braços, com duas máquinas e uma plaquinha em branco | 1,0 × 0,5 | +50% moedas por jogada | 6,6k |

**Máquina de pelúcia:** sem mudança.

| Tier | Nome | Pegada | Efeito | Preço |
|---|---|---|---|---|
| T1 | Máquina de pelúcia | 0,75 × 0,75 | – | a de hoje |
| T2 | Máquina de pelúcia dupla | 1,5 × 0,85 | +50% | 30 💎 |
| T3 | Pelúcia gigante | 1,5 × 1,5 | +100% | 60 💎 |

**Cestinhas e carrinhos (rodada 2): três itens separados que convivem, não tiers.** É como num mercado de verdade: quem vai levar pouco pega cestinha, quem vai levar mais pega carrinho, e quem vai fazer a compra do mês pega o carrinho grande.

| Item | Estação (modelada) | Pegada | Abre | Preço | Leva até |
|---|---|---|---|---|---|
| Cestinha | suporte navy com duas pilhas de cestinhas (alças douradas, borda creme), poste com plaquinha em branco | 0,75 × 0,6 | nível 2 (já existe: "Cestinhas de Mão") | 800 | base +1 produto |
| Carrinho | baia de trilhos cromados com 5 carrinhos encaixados, poste navy | 1,75 × 0,75 | nível 7 (já existe: `cart-corral`), **só no prédio do mercado** (Mercadinho em diante) | 4.000 | base +2 |
| Carrinho grande | baia maior com 4 carrinhos grandes e 2 carrinhos infantis (frente de carrinho creme) | 2,25 × 1,0 | nível 17 (já existe: "Carrinhos Grandes"), Mercadinho em diante | 22.000 | base +4 |

- **Como funciona hoje (código):**
  - cada cliente compra `getMaxProducts(arquétipo)` (1–3, `customer-simulation.ts`) mais um bônus somado: Cestinhas +1, baia de carrinhos +1, Carrinhos Grandes +2, Carrinho Turbo +2, e o `basketBonus` da expansão;
  - no Unity, quem empurra carrinho é sorteado pelo nome do ator (`CheckoutShopperRig.WantsCart`), e nas lojas pequenas todo mundo leva cestinha.
- **Regra nova:**
  1. Cada cliente chega com um **plano** de compras: a base do arquétipo (1–3) + bônus da expansão e de eventos + um **extra de 0 a +4**, sorteado pelo arquétipo (família puxa para cima; econômico e impulsivo, para baixo; normal e premium, no meio).
  2. Ele pega o **menor** que dá conta do extra: 0 → mãos; +1 → cestinha; +2 → carrinho; +3 ou +4 → carrinho grande.
  3. Se o que ele precisa **não existe** no mercado, ele pega o maior que existe e compra só o que cabe. Sem nenhum: só o que cabe nas mãos (base). Aparece a dica "Clientes deixaram de levar produtos: falta carrinho".
  4. No Unity, o objeto que o cliente carrega (cestinha / carrinho / carrinho grande) passa a seguir esse plano, e não mais o nome do ator.
- **Balanço:** com os três itens, o máximo continua base +4. Hoje é +1 +1 +2 = +4, então o teto não muda. Muda que nem todo cliente usa o máximo: a cestinha não vira inútil quando chega o carrinho.
- **Saves:** quem já tem "Cestinhas de Mão" ou "Carrinhos Grandes" ganha a estação correspondente no inventário do modo construir ("Para colocar"). A baia de carrinhos já posta continua onde está. O "Carrinho Turbo" (💎) continua como bônus premium.

### 3.2b Câmara fria (novo, pedido do Lucas em 30/10)
"Geralmente os mercados têm que ter câmara fria, e obviamente a câmara fria também vai crescendo baseado nas evoluções."

**O que é no jogo.** O estoque de **produtos gelados** (laticínios, queijos, frios, carnes, peixes, congelados e sorvetes) fica na câmara fria. O depósito normal guarda o seco: mercearia, bebidas, hortifrúti e padaria. Bebidas continuam no depósito, porque só gelam na geladeira da loja.
- Hoje o depósito guarda um certo número de **caixas por produto**: 2 caixas, e mais +1 / +3 / +6 / +10 nos upgrades de 600 / 2.400 / 8.000 / 22.000 (`src/data/inventory-capacity.ts`).
- Com a câmara fria, o **tier dela é o teto** desse upgrade para os produtos gelados. O seco não muda nada.
- O mini-jogo de repor (`CheckoutStockroom.cs`) já tem a prateleira "refrigerados": ela vira a **porta da câmara fria** (arrastar a caixa gelada para a câmara).
- O item da Loja **"Câmara Fria"** (500.000, nível 51, +10% nos gelados) passa a ser o tier T4. Quem já tem esse item **ganha o T4 na hora**.

| Tier | Nome | Pegada | Onde fica | Caixas por produto gelado (teto) | Preço | Obra |
|---|---|---|---|---|---|---|
| T1 | Freezer de estoque | 1,25 × 0,75 | atrás do balcão / no depósito | até 3 (upgrade 1) | **grátis** (chega com o sistema, para todo save) | – |
| T2 | Mini câmara fria | 2,0 × 2,0 | no depósito | até 5 (upgrade 2) | 8.000 ou 20 💎, Minimercado | 30 min |
| T3 | Câmara fria | 3,0 × 2,5 | encostada no depósito, porta de correr | até 8 (upgrade 3) | 45.000 ou 60 💎, Supermercado | 2 h |
| T4 | Câmara frigorífica | 5,0 × 4,0 | no **Armazém central** (expansão "Armazém central"), com doca | até 12 (upgrade 4) + os +10% de hoje nos gelados | 300.000 ou 150 💎 (≈ 2 h de vendas no Hiper) | 6 h |

- **Onde fica (rodada 2: do lado de fora do mercado):**

  | Tier | Onde | Porta |
  |---|---|---|
  | T1 Freezer de estoque | **dentro**, onde o estoque está: atrás do balcão nas lojas pequenas (Conveniência, Quitanda, Minimercado, onde ainda não existe depósito), depois dentro do depósito | – |
  | T2 Mini câmara | **colada na parede lateral do depósito**, do lado oposto à marquise de carga | **por dentro do depósito** (de fora só aparecem os painéis e a condensadora) |
  | T3 Câmara fria | no mesmo lugar, maior | mesma porta, agora de correr, por dentro |
  | T4 Câmara frigorífica | **colada no armazém central**, ao lado da rampa da doca | doca virada para o mesmo pátio dos caminhões, para eles descarregarem direto nela |

  - As fotos de posição usam as malhas que vão no jogo, em "massinha": `Assets/Art/Storage/Meshes/Depot_74x71.asset` e `CentralWarehouse.asset`, convertidas para OBJ por `scripts/blender/unity_mesh_to_obj.py`.
  - **Falta conferir no Unity** (não consegui montar o lote inteiro, com rua e mercado, fora dele): que o lado escolhido do depósito não encosta no mercado nem na calçada. Isso vale nas fases 0–2, em que o depósito fica **ao lado** da loja (`CheckoutMarketLayout.PlaceDepot`, `StorageBeside`), e depois, quando ele vai para trás. Se encostar, a câmara vai para o fundo do depósito.
- **Preços:** seguem a regra da Loja ("~2 h de vendas no estágio em que abre"). As obras podem ser puladas com diamantes (`diamond-skip.ts`), como todas as esperas.
- **Saves antigos, nada se perde:**
  - (1) todo save recebe o **T1 de graça**;
  - (2) produto gelado que já tem upgrade de depósito **acima do teto** mantém o nível e o estoque (o teto só vale para compras novas);
  - (3) quem tem o item "Câmara Fria" vai direto para o **T4**;
  - (4) o estoque gelado que já está guardado nunca é descartado nem diminuído.
- **Visual (modelado, seção 4):**
  - painéis isolantes creme com emendas, rodapé e cantoneiras navy (pintam com "Cores do mercado"), filete dourado embaixo do teto;
  - porta isolante com visor redondo embaçado e alavanca cromada (T2), porta de correr no trilho com cortina de tiras de PVC (T3), porta seccional de doca com vedação preta (T4);
  - condensadoras navy no teto com grade de ventilador e canos de cobre (1 / 2 / 3 unidades);
  - visor de temperatura em branco, gelo nas borrachas, luz fria na porta, palete com caixas e paleteira (T4).
  - **Nenhuma palavra** nos modelos.

### 3.3 Saves antigos (nada pode ser perdido)
- **Prateleiras, geladeiras e freezers não ganham campo novo:** o tier é **calculado** de `shelfUpgradeLevels` (0 → T1, 1 → T2, 2 → T3, 3 → T4, 4 → ★), limitado pelo teto da expansão. O save não muda, então os testers continuam exatamente onde estavam.
- **Caixa:** um campo novo opcional `fixtureTiers.checkout`. Sem ele, o tier sai das compras de hoje: `auto-scanner` → T3 + leitor, `smart-conveyor` → T3, Minimercado ou maior sem esteira → **T2 de presente**, e nas lojas pequenas → T1. Setores, caixa eletrônico e máquinas: sem o campo, ficam em T1 (que é o de hoje).
- **Espaço no primeiro carregamento:** cada móvel fica **onde está**. Se o visual novo não cabe ali (`CheckoutInterior.Fits`), ele mostra o maior visual que cabe e ganha o selo "⤢ quer crescer". No modo construir, o jogador move e ele cresce. **Nunca** se move nada sozinho e **nunca** se reduz um número. Como a maioria dos T1/T2 é menor que os móveis de hoje (1,9–2,84 m), quase tudo fica com mais espaço.
- **Evoluir para um tier maior pede espaço livre:** antes de pagar aparece o fantasma (verde = cabe, vermelho = "Sem espaço: mova o móvel"), com o mesmo `Fits()` do modo construir. O botão só fica ativo se couber.
- A nuvem (Cloudflare) só recebe esse campo opcional a mais. O `normalize` do worker/app aceita o campo sem ele e não precisa de migração.

### 3.4 Celular (UX)
1. **Tocar no móvel** abre o painel de hoje (`shelf-view.ts`) com um cartão novo, **"Evoluir"**: à esquerda o visual atual, à direita o próximo (sprite 3D gerado pelo `build_ui_sprites.py`, nunca texto na imagem), e as melhoras em chips: "📦 5 → 10 por produto", "📏 1,0 → 1,5 m".
2. Botões **"Evoluir · 1.200"** e **"· 6 💎"**. Sem espaço, o botão vira **"Ver onde cabe"**, que abre o modo construir com o fantasma do tamanho novo.
3. **T3 e maiores têm obra curta** (T3 5 min, T4 30 min, ★ 1 h), com tapume e operários do sistema de obras. Dá para pular com diamantes pela tabela de `diamond-skip.ts` (1 h ≈ 10 💎). Os diamantes passam a ter mais usos, e isso combina com a regra "toda espera pode ser pulada".
4. **Comemoração** (`celebration.ts`): poeirinha, brilho, o móvel quica e um som. Toast: "Seu móvel evoluiu!".
5. **Seta "recomendado"** (como no Cooking Fever) no móvel com mais vendas perdidas por falta de estoque.
6. **Inventário do modo construir:** cada cartão mostra estrelas de tier (★★☆☆), só com pictograma.
7. Textos novos (pt-BR, vão para en/es/fr/de): "Evoluir", "Evoluir · {0}", "Próximo visual", "{0} → {1} por produto", "Sem espaço: mova o móvel", "Ver onde cabe", "Disponível na {0}", "Seu móvel evoluiu!", "Pronto para crescer", e os nomes dos tiers das tabelas.

### 3.5 "Cores do mercado" (pintura)
`CheckoutMarketPaint.Classify` só pinta materiais `Standard` com **cor chapada** navy/dourada, as texturas da lista `WholeNavy` / `WholeGold` / `Keyed` e os atlas das eras com máscara. Os modelos novos seguem isso:
- partes navy: `C_1D2B4F` / `C_2E4A7D` chapados ou a textura `IK_V2_PaintNavy` (já está em `WholeNavy`): **pintam**;
- filetes dourados: `C_D3A53D` chapado: **pintam** como cor de destaque;
- madeira, aço, vidro (`G_Glass`), LED (`E_…`, que vira "Glow") e produtos (`T_FT_Labels`, que contém "Labels"): **nunca** pintam;
- se mais tarde fizermos um atlas próprio para cada tier, ele entra em `Keyed` ou ganha máscara `_PaintMask`, como as eras.

### 3.6 Plano de arte
**Regras:** navy dominante, azul de apoio, creme, dourado só em filetes, madeira natural. Cor viva só nos produtos. Bordas arredondadas (bevel), silhueta de verdade, **nenhuma palavra** nos modelos (placas em branco para o jogo escrever). Os produtos usam o atlas novo **`FT_Labels_albedo.png`**, gêmeo do `IK_Labels` só com pictogramas. Ele também serve para trocar o `IK_Labels` atual, que tem palavras como "COLA" e "SUCO", e a palavra "CAIXA" do caixa de hoje.

**Orçamento iPhone (com o estoque):** T1 ≤ 8k tris, T2 ≤ 15k, T3 ≤ 20k, T4 ≤ 30k. Texturas: só os atlas `IK_*` que já existem (1024 no Android) mais o `FT_Labels` (1024).

Medido (30/10, depois de enxugar o estoque das prateleiras sem mudar o visual):

| Item | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| Prateleira / gôndola | 5,9k | 10,3k | 14,6k | 30,5k |
| Caixa | 4,7k | 6,9k | 4,0k | 6,8k |
| Bebidas | 7,5k | 13,8k | 23,2k | 29,7k |
| Laticínios e frios | 4,0k | 2,2k | 17,2k | 19,9k |
| Congelados | 2,9k | 3,3k | 5,2k | 8,3k |
| Sorvetes | 3,0k | 3,8k | 4,5k | 4,3k |
| Padaria | 3,1k | 7,3k | 8,5k | 7,8k |
| Hortifrúti | 5,1k | 6,2k | 7,2k | ~12k |
| Câmara fria | 1,0k | 5,1k | 6,6k | ~9k |
| Setores v2 (padaria, açougue, queijaria, peixaria, sorveteria) | 5,0–6,3k | 6,7–12,1k | 8,5–16,8k | – |
| Adega v2 / Sucos v2 | 10,6k / 9,9k | 19,9k / 17,4k | 22,7k / 19,9k | – |
| Caixa eletrônico v2 | 2,4k | 4,6k | 7,2k | – |
| Chiclete v2 / pelúcia | 2,3k / 4,0k | 5,2k / 8,2k | – / 7,0k | – |
| Cestinha / carrinho / carrinho grande (itens) | 4,5k | 4,9k | 6,7k | – |
| Hortifrúti T3 / T4 v2, laticínios T4 v2 | – | – | 11,5k | 15,8k / 16,8k |

O que foi cortado é **só o que a câmera do jogo não vê**:
- fileiras de trás nas prateleiras de baixo (fica a fileira da frente; a de cima tem duas);
- garrafas e latas com 8 lados e perfil mais simples;
- etiquetas e caixinhas sem chanfro invisível;
- 4 garrafas por nível nas pontas da T4.

A silhueta, os materiais e as cores não mudaram. As geladeiras T3 de bebidas (23k) ficam um pouco acima da meta de 20k, mas podem perder uma fileira se precisar.

**Lista de modelos (item × tier):**
- ✅ gôndola: 4
- ✅ caixa: 4
- ✅ hortifrúti: 4
- ✅ bebidas: 4
- ✅ laticínios e frios: 4
- ✅ padaria: 4
- ✅ congelados: 4
- ✅ sorvetes: 4
- ✅ câmara fria: 4
- ✅ lote B: pelúcia 3
- 🔁 rodada 2: setores 7 × 3 refeitos, caixa eletrônico 3, chiclete 2, cestinha / carrinho / carrinho grande (3 itens), hortifrúti T3/T4, laticínios T4, posição da câmara fria
- lote C: máquina de bebidas, cabine de fotos, quiosque de café (T2/T3)
- falta: registradora do balcão fixo, 2 (T1/T2 para a Conveniência e a Quitanda)

**Achado:** o modelo da Quitanda que vai no jogo (`Resources/CheckoutEras/Era5_Quitanda.fbx`) tem a palavra **"CHECKOUT" pintada no balcão**. É texto no asset, a trocar por pictograma (como o "CAIXA" do caixa de hoje).

**Ordem:**
1. Aprovar gôndola + caixa (esta fase).
2. Hortifrúti + bebidas: estão na Conveniência desde o começo.
3. Laticínios + padaria.
4. Congelados + sorvetes.
5. Código: tiers derivados, Evoluir, fantasma, celebração.
6. Setores.
7. Caixa eletrônico, máquinas e carrinhos.

Cada lote: render → aprovação → export pelo `rk_core.export` → `CheckoutInteriorKitBuilder` com templates `shelf-grocery@t2` etc.

**Código (fase 2):**
- `src/data/fixture-tiers.ts`: nomes, pegadas e teto por expansão.
- `getFixtureTier(state, id)`, derivado como em 3.3.
- Unity: `ShelfTemplate(shelf, tier)` com o sufixo `@tN`. `CheckoutInteriorPiece.min/max` de cada template dá a pegada.
- `Fits()` antes do Evoluir.
- O selo "quer crescer" no carregamento.

---

## 4. Arte conceito (fase 1)
Builder `scripts/blender/fixture_tiers.py` (usa `rk_core` / `rk_products`), atlas `scripts/blender/fixture_tiers_labels.py` → `ArtSource/fixture_tiers/textures/FT_Labels_albedo.png`, blend `unity/CheckoutSimulator/ArtSource/fixture_tiers/fixture_tiers.blend`.

Renders em `unity/CheckoutSimulator/Temp/qa/fixture_tiers/` (cópia no branch `fixture-tiers` em `ArtSource/fixture_tiers/previews/`):
- `shelf_lineup.jpg`, `checkout_lineup.jpg` + `*_T1..T4_closeup.jpg`
- lote A: `drinks_lineup.jpg`, `dairy_lineup.jpg`, `freezer_lineup.jpg`, `icecream_lineup.jpg`, `bakery_lineup.jpg`, `produce_lineup.jpg` + os close-ups de cada tier
- câmara fria: `coldroom_lineup.jpg` + `coldroom_T1..T4_closeup.jpg`
- rodada 2: `coldroom_place_T2.jpg`, `coldroom_place_T3.jpg`, `coldroom_place_T4.jpg` (posição fora do mercado)
- lote B / rodada 2: `sector-padaria_lineup.jpg`, `sector-acougue_…`, `sector-queijaria_…`, `sector-peixaria_…`, `sector-sorvetes_…`, `sector-adega_…`, `sector-sucos_…`, `atm_lineup.jpg`, `gumball_lineup.jpg` (T1, T2), `claw_lineup.jpg`, `carts_lineup.jpg` (os 3 itens lado a lado) + close-ups
- caber na loja:
  - `conveniencia_fit_hoje.jpg`: os 6 móveis no tamanho de hoje;
  - `conveniencia_fit_tiers.jpg`: T1/T2 da proposta;
  - `quitanda_fit_tiers.jpg`: os 7 móveis da Quitanda em T1/T2 de verdade (gôndolas, padaria, laticínios, congelados, bebidas, hortifrúti) dentro do modelo que vai no jogo, com a faixa da fila livre na parede leste.

Grade: linhas escuras a cada 1 m, claras a cada 0,25 m. O contorno verde é a pegada no modo construir. Boneco de 1,75 m para escala.

---

## 5. O que entrou no jogo (implementação, 30/10; no main desde 31/10, b0a4fce)

Aprovado pelo Lucas ("pode pôr no jogo já"). Fora desta entrega: o lote C. Os 7 setores especiais entraram depois (5.4.2).

### 5.1 Tiers sem campo novo no save
- **Save 47 → 48.** A migração não apaga nada. Ela só converte os carrinhos antigos (ver 5.6) e dá a registradora a quem já tinha direito (5.3).
- **Prateleiras, geladeiras, freezers e balcões:** tier = `shelfUpgradeLevels + 1`, limitado pelo teto da expansão:

  | Expansão | Teto |
  |---|---|
  | Conveniência / Quitanda | T2 |
  | Minimercado | T3 |
  | Mercadinho | T4 |
  | Supermercado ou maior | ★ (T4 com o acabamento premium) |

  O teto também bloqueia a **compra** do próximo passo de capacidade ("Disponível no {0}"). Quem já comprou acima do teto mantém o número; o visual espera a expansão.
- **Nas barracas** (antes da Conveniência) os números seguem até o T2 e o visual é o da barraca.
- **Limite de produtos por móvel:** 5 / 6 / 7 por tier.
- O tier de cada móvel vai no snapshot (`shelves[].tier / tierTemplate / premium`), e o Unity só desenha.

### 5.2 Regra de espaço (decidida)
- Cada móvel fica **onde está** e mostra o **maior tier que cabe ali**. Quando o tier pedido não cabe, ele fica com o selo "pronto para crescer".
- Ele cresce sozinho assim que couber: quando o jogador o move no modo construir, ou quando o espaço em volta fica livre.
- **Nunca** é movido sozinho, **nunca** vai para o inventário e **nunca** perde número.
- **No painel do móvel:** quando o modelo maior não cabe onde o móvel está, o botão "Evoluir" vira "Sem espaço: mova o móvel · Ver onde cabe" e abre o modo construir. Ali o jogador escolhe o lugar e depois evolui.
- **A regra de cima cobre o resto:** saves antigos, compras feitas por outra tela e móveis que ficam apertados depois. Nesses casos o número vale na hora e o visual grande espera o espaço.
- **Mudança em relação à proposta:** a evolução de prateleira **não tem obra**. As obras ficam para a câmara fria.

### 5.3 Caixa
O passo do caixa sai dos itens da Loja:
- **T1** caixinha;
- **T2** "Caixa registradora": item novo, 3.000 ou 10 💎;
- **T3** "Caixa com esteira": a esteira de hoje, que agora pede a registradora;
- **T3 + leitor**: o leitor automático;
- **T4** "Caixa premium": item novo, 90.000 ou 90 💎, nível 30, a partir do Supermercado.

Regras:
- Do Minimercado em diante, todo save ganha a registradora de presente, assim como quem já tinha esteira ou leitor.
- O visual também tem teto por expansão: antes do Minimercado T2, antes do Supermercado T3.
- Na Conveniência e na Quitanda continua o balcão fixo do modelo.

### 5.4 Câmara fria
- **São itens da Loja, com obra:**

  | Item | Tier | Preço | Obra | Pede |
  |---|---|---|---|---|
  | `cold-room-2` | T2 | 8.000 ou 20 💎 | 30 min | Minimercado |
  | `cold-room-3` | T3 | 45.000 ou 60 💎 | 2 h | Supermercado e o T2 |
  | `cold-storage` "Câmara frigorífica" | T4 | 300.000 ou 150 💎 | 6 h | o T3 e a expansão "Armazém central" |

  - O T1 é grátis.
  - Quem já tinha o item antigo "Câmara Fria" fica no T4 (é o mesmo id).
- **O tier é o teto do upgrade de depósito só para os produtos gelados** (laticínios, queijos, frios, carnes, peixes, congelados, sorvetes). Upgrades e estoque acima do teto nunca são reduzidos.
- **A porta "refrigerados" do mini-jogo de repor não mudou.**
- **Onde aparece (conferido no mapa inteiro, foto de cada expansão):**

  | Expansão | Lugar |
  |---|---|
  | Conveniência / Quitanda | T1 dentro, atrás do balcão |
  | Minimercado | T2 na lateral da loja, no calçamento do lote B1 |
  | Mercadinho | **dentro do depósito** (não aparece): a loja ocupa A1+B1 inteiros, e não existe depósito nessa fase. Se o jogador tiver A2/B2 comprados e limpos, o T2 vai para lá, encostado no fundo da loja. |
  | Supermercado | **ala da câmara no próprio depósito** (decisão do Lucas, opção a): `coldroom_depotwing_T2/T3`, modelados no espaço da malha do depósito. A ala fica na parede leste, com no máximo 1,49 m de fundo (detalhes em 5.4.1), e passa da quina sudeste. As condensadoras ficam no telhado e a porta é por dentro. |
  | Hipermercado / Rede | T4 colado no armazém central, ao lado da rampa, com doca para o pátio dos caminhões |

- **Regras de lugar** (`CheckoutColdRoom.cs`):
  - só em lote do jogador ("seu" / ocupado), nunca na rua, na calçada nem em lote à venda;
  - a pegada inclui as condensadoras e a doca;
  - nada encosta na fila de caminhões, no corredor dos repositores nem na porta do depósito;
  - quando não há lugar, o log diz o motivo e a câmara fica "dentro do depósito".

#### 5.4.1 Medidas do depósito no Supermercado (para a ala)
- **Malha `Depot_74x71`:**
  - pivô no mundo em (11,971; 0,035; 13,968), yaw 90°;
  - limites locais x −3,932..6,742, y 0..5,28, z −4,721..3,786;
  - local +z = leste.
- **Lote C2:** x 5,75..17,25, z 4,75..18. O C3 ainda está à venda.
- **Cada lado:**
  - norte: 0,10 m;
  - oeste: corredor de 1,5 m e porta dos repositores;
  - sul: baia e entrada dos caminhões;
  - **leste: 1,49 m livre**.
- O depósito **não pode andar**.
- A porta da ala passa pela parede leste, por dentro do depósito.

### 5.4.2 Setores especiais (aprovados pelo Lucas, 30/10)
- **Os 7 setores evoluem em T1 / T2 / T3:** padaria, queijaria, açougue, bebidas (o "sucos" da arte), peixaria, sorvetes e adega.
- **Novo no save:** `sectorTiers` (v48; sem a chave, o setor é T1).
  - Todo setor já construído vira **T1**. O modelo é menor que o balcão antigo, então sempre cabe.
  - A fila de produção e o estoque não mudam.
- **Efeitos:**
  - **T2:** +1 linha de produção.
  - **T3:** produção 20% mais rápida e os produtos do setor 10% mais caros. A referência de preço do cliente sobe junto, então a demanda não cai.
- **Preço T2 / T3:**

  | Loja | Moedas |
  |---|---|
  | Mercadinho | 18.000 / 55.000 |
  | Supermercado | 30.000 / 90.000 |
  | Hiper e Rede | 70.000 / 200.000 |

  Ou 30 / 80 💎 em qualquer loja.
- **Sem obra.** O botão "Evoluir" fica na página do setor (Produção).
- **Telas sem texto no modelo.** O jogo escreve nelas (`CheckoutSectorScreens`):
  - **Painéis de preço:** pictograma do produto + moeda + preço real (o do balcão, já com o bônus do T3), escrito com os números do idioma. Com o balcão vazio, mostram o cardápio do setor.
  - **Senha:** "agora atendendo", sobe a cada cliente que compra no setor.
  - **Placa:** o nome do setor no idioma do jogador.
- **Desempenho no iPhone:**
  - um TextMeshPro por tela; os pictogramas e a moeda vêm de um atlas só, desenhado uma vez numa render texture;
  - a tela só é reescrita quando muda (preço, idioma ou senha) e quando está à vista.
- **Arte:**
  - os slots `E_PriceScreen`, `E_TicketScreen` e `E_NamePanel` nunca viram cor de brilho;
  - o atlas `FT_Sector` importa em 2048;
  - produtos e madeira não pintam com "Cores do mercado";
  - os cartões do modo construir usam a foto do T1 (as fotos antigas tinham o nome escrito).

### 5.5 Caixa eletrônico e máquinas
- **Caixa eletrônico:**
  - T2: 45.000, nível 25, +20% de moedas;
  - T3: 120.000, nível 33, +25%.
- **Máquina de chiclete** T2: 6.600, nível 18, ×1,5.
- **Máquina de pelúcia:**
  - T2: 30 💎, nível 28, ×1,5;
  - T3: 60 💎, nível 34, ×2.
- O tier fica em `interior.tiers`. O botão "Evoluir" fica no cartão da Loja → Decoração.

### 5.6 Cestinha, carrinho e carrinho grande (3 estações)

| Estação | Nível | Preço | Extra | Pede |
|---|---|---|---|---|
| Cestinha | 2 | 800 | +1 | – |
| Carrinho | 7 | 4.000 | +2 | Mercadinho |
| Carrinho grande | 17 | 22.000 | +4 | Mercadinho |

- As três estações convivem.
- **Plano do cliente:** cada cliente sorteia de 0 a +4 produtos a mais, pelo perfil (família leva mais, econômico menos). Ele pega o **menor** carregador que cobre o plano. Se nenhum cobre, leva o maior que tem e conta um "faltou carrinho".
- Com 5 faltas, aparece a dica "falta-carrinho", que aponta para a Loja.
- O sorteio usa um dado próprio, então a visita sem estações fica idêntica à de hoje.
- **Saves antigos:**
  - os itens "Cestinha" e "Carrinho grande" da Loja viram estações em "Para colocar";
  - os carrinheiros já colocados ficam;
  - o "Carrinho Turbo" não muda.
- **No Unity:** o cliente segura o que o plano escolheu (mãos vazias, cesta, carrinho, ou carrinho grande com 1,22× de comprimento e largura).
- **Quanto cada um compra** (simulação de 4.000 visitas, 16 produtos em estoque, com as três estações): mãos 1,26 produto por cliente, cestinha 2,13, carrinho 2,75, carrinho grande 3,15. Média geral: 1,42 sem estações → 2,00 só com cestinha → 2,32 com as três.

### 5.7 Arte no Unity
- **Origem:** os 47 FBX vão em `Assets/Art/Interior/Models/Tiers/`. O menu "Supermarket/Build fixture tiers" gera os prefabs em `Resources/CheckoutFixtureTiers/<tipo>_T<n>`.
- **Malhas e materiais:**
  - as malhas são unidas por material em `Art/Interior/Meshes/FT/`;
  - as cores chapadas que não pintam vão para uma paleta 32×32 (`FT_Palette_albedo.png`). Exemplo: bebidas T3 cai de 27 para 9 materiais.
- **Cores do mercado:** produtos, madeira e creme vão para materiais "Products" e nunca são repintados. Navy e dourado pintam.
- **Sprites:** os da Loja e do inventário são renderizados dos modelos e não têm texto.

### 5.8 Teste automático
- **Supermercado sem clientes (corrigido 30/10):** no NavMesh, o topo da rampa da entrada parava ~3 cm antes do piso. No Supermercado (profundidade 1,3) a fresta passou de um voxel e o piso inteiro ficou separado da rua: os clientes davam a volta por fora e ninguém entrava. Não tinha a ver com os móveis (bloqueado mesmo sem nenhuma peça). Uma faixa plana na altura do piso sobre a emenda resolveu (`MarketSimulation.BuildNavigation`). O Mercadinho não era afetado.
- **Fila do caixa (fora do merge, branch `queue-line-fixes`):** com muita gente, quem passava das 3 vagas do caixa ia todo para a última vaga, e o próximo a pagar podia ficar preso atrás de alguém que já estava na vaga 1 (um carrinho grande ficou 51 s parado). O problema já existe no main e não vem dos tiers. Há duas correções testadas: a fila continuar depois da última vaga, e o cliente entrar na fila só quando chega ao fim dela. Os resultados no teste de estresse foram mistos, então elas não entraram no merge de 31/10 e esperam um teste num dia normal com o Lucas.
- **Fluxo de clientes:** `eventscrowd-<loja>[.segundos[.clientes[.keep][.carts][.stock]]]`. Linhas `NAV` medem a entrada (caminhos, borda, o mesmo caminho sem móveis). `.carts` compra e coloca as 3 estações e conta por carregador; `.stock` repõe as prateleiras. Um dia que acabaria no meio da medição é fechado antes.
- **Cenário:** `eventstiers-<partes>` (flow, shelves, checkout, coldroom, carts, decor, depot) roda na **cópia QA** do save.
- **Saída:** linhas `RESULT tiers <parte>: PASS|FAIL` e fotos `Logs/ft_*.jpg` de cada móvel em cada tier dentro de uma loja de verdade, do caixa, da câmara em cada expansão, das 3 estações com clientes e do caixa eletrônico e das máquinas.
