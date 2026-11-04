# Evoluções com recompensa, tempo e animação

Pedido do Lucas (01/11): cada evolução de móvel e de setor tem que **valer o dinheiro**. O jogo fica mais rápido, o móvel tem mais opções de produto, cabe mais quantidade na exposição e cada evolução traz **produtos novos**. Evoluir **leva tempo** e termina com uma **animação de evolução bonita**.

**Status (01/11):**
- Aprovado pelo Lucas e implementado.
- No main desde 49dea05 (branch tier-rewards); save versão 49.
- Enviado aos testers:
  - iPhone TestFlight **1.0 (8)** (commit 2cb2f19);
  - Android teste interno **12 (1.0)** (commit c5f9bd4).
- As respostas dele às 3 perguntas:
  - o móvel continua vendendo enquanto evolui;
  - os lugares vêm de graça com o tier;
  - 1 produto novo por evolução, 50 no total.

## 1. Como está hoje

| Móvel | O que a evolução dá hoje | Tempo |
|---|---|---|
| Prateleiras, geladeiras, freezers, bancas (T1 → T4 → ★) | só mais unidades por produto (5 → 10 → 15 → 20 → 25) e o visual novo. Os lugares de produto (4 → 7) são comprados à parte, com limite pelo tier (5 / 6 / 7). | instantâneo |
| Setores (T1 → T3) | T2: +1 linha de produção. T3: produção 20% mais rápida e produtos 10% mais caros. | instantâneo |
| Caixa (T1 → T4) | atendimento mais rápido (×1,1 / ×1,25 / ×1,25 / ×1,2) | instantâneo |
| Caixa eletrônico, chiclete, pelúcia | mais moedas | instantâneo |
| Câmara fria (T1 → T4) | mais caixas de produto gelado no estoque | obra de 30 min / 2 h / 6 h |

Na troca, o modelo novo aparece de uma vez e surge o cartão "SEU MÓVEL EVOLUIU!". Ainda não existe animação no 3D.

## 2. Proposta: o que cada evolução dá

### 2.1 Prateleiras, geladeiras, freezers e bancas

Os preços **continuam os de hoje**: 1.200 / 6.000 / 22.000 / 70.000 moedas, ou 6 / 14 / 28 / 48 💎.

| | T1 | T2 | T3 | T4 | ★ |
|---|---|---|---|---|---|
| Unidades por produto na exposição | 5 | 10 | 15 | 20 | 25 |
| Produtos diferentes no móvel (lugares) | 4 | **5** | **6** | **7** | **8** |
| Atração (chance de o cliente pegar algo dele) | – | +5% | +10% | +15% | +25% |
| Reposição mais rápida (funcionário e mini-jogo) | – | −10% | −20% | −30% | −40% |
| **Produto novo exclusivo** | – | 1 | 1 | 1 | 1 |
| Tempo da evolução | – | 2 min | 10 min | 30 min | 1 h |

- Os **lugares passam a vir com a evolução**, de graça, e o botão separado "Mais um produto" sai. Quem já comprou lugares fica com o maior dos dois números.
- O ★ ganha um 8º lugar.

### 2.2 Setores especiais

Os preços **continuam os de hoje**.

| | T1 | T2 | T3 |
|---|---|---|---|
| Linhas de produção | as de hoje (2–3) | +1 | **+2** |
| Tempo de produção | 100% | **−15%** | **−30%** (hoje −20%) |
| Rendimento por fornada | o da receita | **+25%** | **+50%** (arredondado para cima: baguete 4 → 5 → 6) |
| Preço dos produtos do setor | – | – | +10% |
| Balcão | 4 produtos | 5 produtos, +5 unidades | 6 produtos, +10 unidades |
| **Receita nova exclusiva** | – | 1 | 1 |
| Tempo da evolução | – | 30 min | 2 h |

**04/11 (Lucas: cada setor abre uma expansão antes):** a evolução segue a faixa de tempo da expansão em que o setor
abre — padaria (Minimercado) T2 30 min, T3 1 h 15; queijaria, açougue e bebidas (Mercadinho) T2 1 h, T3 2 h 30;
peixaria, sorvetes e adega (Supermercado) T2 1 h 30, T3 3 h (`src/data/fixture-evolution.ts`). O preço do T2/T3 no
Minimercado é 10.000 / 30.000 (`getSectorTierPrice`).

### 2.3 Caixa, caixa eletrônico e máquinas
Os efeitos continuam os de hoje, porque já dão recompensa. Eles também passam a ter **tempo e a animação de evolução**:
- caixa: T2 5 min, T3 20 min, T4 1 h;
- caixa eletrônico e pelúcia: 15 min / 1 h;
- chiclete: 10 min.

A câmara fria mantém as obras que já tem e ganha a mesma revelação no final.

### 2.4 Produtos novos (exclusivos de cada evolução)

Cada produto abre **quando o móvel chega no tier**. Ele só pode ser vendido nesse tipo de móvel, com margem um pouco melhor que a dos produtos normais do mesmo móvel naquela fase. Cada um ganha **ícone 3D no estilo dos atuais**, e você aprova as fotos antes.

| Móvel | T2 | T3 | T4 | ★ |
|---|---|---|---|---|
| Hortifrúti | Morango | Abacate | Cogumelos frescos | Frutas exóticas (pitaya e lichia) |
| Bebidas | Água de coco | Kombucha | Cerveja artesanal | Espumante rosé |
| Padaria (prateleira) | Bisnaguinha | Pão integral | Pão de fermentação natural | Brioche amanteigado |
| Laticínios e frios | Requeijão | Iogurte grego | Gorgonzola | Salame italiano |
| Doces | Pipoca doce | Brigadeiro gourmet | Macarons | Bombons belgas |
| Mercearia | Molho de tomate | Azeite extravirgem | Café em cápsulas | Azeite trufado |
| Casa e higiene | Sabonete | Amaciante | Perfume | Kit spa |
| Congelados | Nuggets | Polpa de fruta | Risoto congelado | Pizza napolitana |
| Sorvetes (freezer) | Picolé de frutas | Açaí na tigela | Picolé gourmet | Bolo de sorvete |

| Setor | T2 | T3 |
|---|---|---|
| Padaria | Pão de queijo | Torta de morango |
| Queijaria | Burrata | Queijo canastra maturado |
| Açougue | Linguiça artesanal | Picanha wagyu |
| Bebidas | Limonada suíça | Smoothie de açaí |
| Peixaria | Ceviche | Lagosta grelhada (do aquário do T3) |
| Sorvetes | Milkshake | Gelato de pistache |
| Adega | Vinho rosé da casa | Espumante da casa |

No total são 36 produtos de móvel e 14 receitas de setor. As receitas usam ingredientes que o jogador já tem nessa fase.

## 3. Tempo de evolução
- Ao pagar, chega a **equipe de evolução**. Ela é separada dos operários das obras, então a evolução não trava a construção de móveis e setores.
- Evolui **um móvel por vez**. Os outros esperam na fila, como as obras.
- Tudo pode ser pulado com diamantes, pela tabela de sempre (1 h ≈ 10 💎).
- O tempo corre com o jogo fechado. Ao voltar, a revelação toca quando o jogador olhar o móvel.
- **Durante a evolução, o móvel continua vendendo** com o visual antigo (confirmado pelo Lucas).

## 4. A animação de evolução

**Enquanto evolui:**
- um operário com caixa de ferramentas trabalha ao lado do móvel, martelando, com faísca e poeirinha;
- em cima flutua um **anel de progresso navy com filete dourado** e o tempo que falta (sem retângulo branco com "!");
- ao tocar no anel, abre a opção de pular com 💎.

**Quando termina, a revelação (~3 s):**
1. A câmera desliza até o móvel (0,6 s).
2. Um **pano navy com laço dourado** cai ondulando sobre o móvel, com um rufar de tambor.
3. O pano é **puxado para cima** e some num brilho dourado.
4. O modelo novo surge com "estica e encolhe" (0,85 → 1,08 → 1,0), raios de luz atrás e confete navy, dourado e creme.
5. Os produtos **caem nas prateleiras um a um, quicando**. Nos setores, o funcionário dá um pulinho e as telas do painel de preços acendem uma por uma.
6. Sobem chips flutuantes: "+5 por produto", "+1 lugar", "NOVO: Morango".
7. Toca um "ta-dá" com brilho de moedas.

**Depois aparece o cartão de comemoração:**
- foto do visual novo;
- **antes → depois com os números contando** (5 → 10 por produto, 4 → 5 lugares, −15% de tempo);
- os produtos novos com selo **NOVO**;
- botão **"Colocar à venda"**, que abre o móvel com o produto novo pronto para escolher.

### 4.1 Como ficou no jogo (aprovado em 01/11 depois de 3 rodadas de vídeo)
- **Câmera:** chega perto em ~0,8 s; o móvel ocupa ~40–47% da altura da tela. No fim volta exatamente para a vista do jogador.
- **HUD cinematográfico:** durante a revelação o HUD some e ficam só moedas e diamantes.
- **Pano e luz:** pano navy com dobras, laço dourado e balanço, puxado para cima em brilho dourado. Atrás do modelo, uma explosão curta de raios com luz de contorno; nenhuma coluna de luz tapa o modelo.
- **Confete:** sai na área real do móvel (64 peças numa prateleira, até 170 num setor). As peças são pequenas e variadas: tirinhas, bolinhas, serpentinas, estrelinhas e brilhos. Giram e balançam ao cair. Cores: navy, dourado, creme, branco e a cor de destaque do setor. Um único sistema de partículas.
- **Do pano ao cartão:** 3,77 s. O cartão só aparece depois que os produtos pousam, e os números terminam de contar 0,77 s depois.
- **Cartão:**
  - foto ao vivo do modelo 3D do tier novo;
  - nome do móvel com o tier em estrelas douradas numa pílula navy (sem frase de descrição);
  - 4 cartõezinhos de antes → depois;
  - bloco NOVO com o produto;
  - botões "Colocar à venda" (setor: "Produzir") e "Continuar".
- **Testes:** `RESULT tiers reveal` confere tempo, câmera, números do cartão contra a tabela, foto ao vivo e espaçamento.
- **Pendências pequenas:**
  - o pano da padaria fica um pouco quadrado;
  - na foto do cartão do setor, o funcionário nem sempre aparece.

## 5. Saves antigos (nada se perde)
- **Móvel ou setor que já está em T2/T3/T4:** ganha na hora os lugares, os bônus e os produtos novos dos tiers que já tem. Aparece um cartão "Novos produtos liberados".
- **Lugares já comprados:** nunca diminuem.
- **Produção e estoque:** não mudam.
- **Economia:** o robô de economia roda de novo para conferir que as expansões continuam chegando no dia certo com a renda extra.

## 6. Ordem de trabalho
1. Código:
   - recompensas das tabelas 2.1–2.3;
   - fila e tempo da evolução;
   - pular com diamantes;
   - saves antigos;
   - testes.
2. Arte:
   - 50 ícones de produto novos, com fotos para aprovação;
   - modelos dos produtos nas prateleiras.
3. Unity:
   - operário e anel de progresso;
   - revelação com o pano;
   - confete;
   - produtos caindo;
   - cartão com antes → depois;
   - fotos e vídeo para aprovação.
4. Economia (robô) e teste completo.
5. Merge depois da sua aprovação, sem build. (Feito em 01/11; em seguida o Lucas pediu os builds para os testers.)
