# Rede de supermercados: marca + centro de distribuição (implementação, 05–06/11/2026)

Pedido do Lucas: ideias 2 (marca da rede) e 5 (centro de distribuição) da proposta `claude/rede-supermercados-proposta.md`. Para o CD, ele quis "mesclar as 3 opções": a frota abastece a loja, faz contratos na cidade e leva carga para filiais simples. A marca própria entra junto.

Branch: `rede-marca-cd`, feita a partir de `fix-friends-loading`.

## Como funciona

Tudo abre quando a obra da Rede termina. Saves que já estão na rede ganham tudo ao abrir o jogo.

### 1. Marca
- **Batizar a rede:** um cartão abre sozinho com um campo de nome (2 a 18 letras) e 12 logos para escolher. Na primeira vez é grátis. Depois, trocar só o logo continua grátis e um nome novo custa 50 diamantes.
- **Cores:** o logo usa as cores do mercado ("Cores do mercado", principal e destaque) e muda junto quando o jogador repinta.
- **Onde aparece hoje:**
  - letras grandes e medalhão da fachada do hipermercado;
  - marquise de vidro;
  - totem;
  - ícones da janela Rede;
  - embalagens da marca própria.
- **O nome é do jogador:** não passa pela tradução. No snapshot o campo se chama `brand`, não `name`.

### 2. Marca própria
São 8 produtos, ids 172–179: arroz, feijão, café, leite, biscoito, detergente, papel higiênico e macarrão.
- Custam cerca de 55% do produto comum e vendem por 85% do preço dele, então o lucro por unidade é maior.
- Clientes econômicos e famílias preferem esses produtos.
- Só vêm pelo CD: um carrinho que tem só esses produtos vai pela frota automaticamente.

### 3. Centro de distribuição e frota
- **Frota inicial:** 1 caminhão seco e 1 refrigerado.
- **Compra de caminhões:**
  - mais 3 secos: 180 mil, 320 mil e 520 mil;
  - mais 2 refrigerados: 350 mil e 600 mil.
- **Motor turbinado:** 3 níveis (250 mil, 500 mil e 900 mil), com viagens −15%, −28% e −40%.
- **Abastecer a loja pelo CD:**
  - preço −10%, tempo de entrega pela metade, até 30 caixas por caminhão;
  - não ocupa vaga de fornecedor;
  - produtos frios (carnes, peixes, laticínios, queijos, frios, congelados e sorvetes) precisam do refrigerado.
- **Pedido automático:** a cada minuto, se algo está acabando, sai um caminhão sozinho. O jogador sempre fica com pelo menos 50 mil moedas.

### 4. Contratos da cidade
- **Clientes:** restaurante, hotel, escola, hospital, lanchonete e buffet de festas.
- **Ofertas:** 3 por vez. A cada 30 min chegam novas, e uma oferta que ninguém pega sai depois de 2 h.
- **Pedido:** 2 ou 3 produtos que o jogador já vende, de preferência das categorias do cliente.
- **Entrega:** sai do estoque e é paga quando o caminhão chega (8 a 16 min de viagem).
- **Pagamento:**
  - 2× o preço de prateleira, mais XP;
  - 1 oferta em cada 6 dá 5 diamantes.

### 5. Filiais
Cada filial tem uma obra e rende por minuto, conforme as prateleiras estão cheias. Os valores abaixo são de uma filial de nível 1 com prateleiras cheias.

| Bairro | Preço | Obra | Rende por hora |
|---|---|---|---|
| Centro | 450 mil | 3 h | 15,6 mil |
| Praia | 600 mil | 4 h | 17,2 mil |
| Universitário | 750 mil | 5 h | 15,6 mil |
| Vila Residencial | 900 mil | 5 h | 17,9 mil |
| Bairro Nobre | 1,1 mi | 6 h | 21,8 mil |

- **Níveis:**
  - nível 2: 80% do preço, obra de 4 h, rende ×1,9;
  - nível 3: 140% do preço, obra de 8 h, rende ×3,2.
- **Prateleiras:** esvaziam em 12 h. As moedas ficam esperando a coleta por até 8 h de renda.
- **Carga:** leva 40 unidades por nível, tiradas do estoque da loja.
  - Com pelo menos metade dos produtos favoritos do bairro, as prateleiras enchem 100%; sem isso, 75%.
- **Diamantes:** aceleram a obra.

## Código
- **Lógica:**
  - `src/data/chain.ts` (números);
  - `src/services/chain.ts` (regras);
  - `src/@types/chain.ts` (tipos);
  - `src/services/chain.test.mjs` (12 testes).
- **Store:**
  - slice `chain`, save versão 51;
  - ações `nameChain`, `setChainAutoOrder`, `buyFleetTruck`, `upgradeFleetSpeed`, `orderFromDistributionCenter`, `acceptChainContract`, `buyChainBranch`, `finishChainBranchNow`, `sendChainBranchCargo`, `collectChainBranches`, `processChain` (a cada 1 s).
- **Pedidos:** `supplier-cart.ts` tem `via: "frota"` e o pedido ganha `fleetTruckId`.
- **Janela Rede:** `desktop/pages/rede.ts`, com as abas Marca · Frota · Contratos · Filiais. O botão "Rede" na barra só aparece na rede.
- **Unity:**
  - `CheckoutBrand.cs` tinge logos, produtos e filiais com as cores e o logo;
  - `CheckoutBrandWorld.cs` aplica o nome e o logo na fachada;
  - teste automático `eventsrede-phone`.
- **Arte:**
  - `scripts/art/rede_art.py` processa as imagens do Codex em máscaras magenta/ciano;
  - `scripts/art/unity_meta.py` grava os .meta com leitura ligada;
  - `scripts/blender/rede_assets.py` tem os modelos 3D.
- **Traduções:** en, es, fr e de em `scripts/i18n/rede_strings.py`.

## Assets 3D (rodada 1, aguardando aprovação do Lucas)
- caminhão da frota seco e refrigerado;
- totem da rede;
- letreiro do nome e medalhão de parede;
- guarita com cancela;
- caixa d'água com logo;
- posto de diesel da frota;
- sacola de papel.

Todos usam navy C_1D2B4F e dourado C_D3A53D, repintados pelas "Cores do mercado". Placas brancas têm empties `Brand_*`, onde o jogo desenha o logo e o nome.

## Pendente
- Levar os modelos 3D aprovados para o jogo:
  - caminhões da frota rodando no pátio do CD;
  - totem e letreiro;
  - guarita, caixa d'água e posto;
  - clientes saindo com a sacola;
  - logo no uniforme.
- Mapa da cidade e arte das filiais (Codex).
- Mostrar o logo no cartão de amigos (precisa de campo no servidor).
- Calibrar os números com o robô de economia.
