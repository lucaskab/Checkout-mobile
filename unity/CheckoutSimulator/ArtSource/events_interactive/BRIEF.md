# Eventos interativos — Vigilância sanitária (18) e Venda pela janela (12)

Pedido do Lucas (05/10/2026): implementar as duas interações com assets, animações, rigs e bones impecáveis.
Fluxo: modelar no Blender → fotos para aprovação → só depois importar no Unity.

Regra nova para os assets: **nada de texto escrito na textura**. O jogo agora tem 5 idiomas; use pictogramas (✓, ✗, estrela, gota, lâmpada, termômetro). Os letreiros antigos ("VIGILÂNCIA SANITÁRIA" no carro) ficam como estão.

## 18 · Vigilância sanitária — "Checklist do fiscal" (volta a ser sorteado, a partir da banca)

### Jogo (TypeScript, `src/services/game-events.ts` + store)
- O evento dura 4 min e o fiscal visita **3 pontos**, cerca de 1 min cada.
- Em cada ponto, aparece um problema real usando os imprevistos que já existem (`store-incidents`):
  - etiqueta de preço errada (`etiqueta`);
  - lâmpada queimada (`lampada`);
  - chão molhado (`derramado`);
  - geladeira ou freezer quente (`geladeira_bebidas` / `freezer_sorvete`, só se o mercado tiver).
- O jogador tem **25 s** para resolver (o minigame que já existe no Unity). A equipe de limpeza/repositor também pode resolver, mas mais devagar.
- Resultado no fim:
  - 3/3: selo de aprovado na porta até o fim do dia, +3 de reputação e bônus em moedas;
  - 2/3: advertência, sem efeito;
  - 0–1: multa de 8% da meta do dia (o efeito `inspection` já existe).
- HUD: o banner do evento mostra a prancheta "Checklist 1/3" com o tempo do ponto atual. Clicar no balão do fiscal leva até o problema.

### Assets (Blender → `Assets/Resources/EventRigs/`)
- **Fiscal**: personagem do jogo, no mesmo esqueleto dos outros, para os clips de `EventMoves` funcionarem.
  - Roupa: jaleco branco por cima da camisa, boné azul-marinho com um escudo simples (pictograma, sem texto), crachá no cordão.
  - Prancheta na mão esquerda e caneta na direita, presas em bones de mão (`Prop_L` / `Prop_R`).
- **Props**:
  - prancheta com folha de checklist (3 caixinhas desenhadas, sem palavras);
  - carimbo;
  - **selo de aprovação** redondo verde com ✓ e estrela, para pendurar na porta;
  - aviso amarelo com "!" (advertência);
  - aviso vermelho com "✗" (multa);
  - **marcador de inspeção** flutuante (lupa + "!") que fica sobre o móvel com problema.
- **Animações**, no esqueleto dos personagens, com IK de pés:
  - `Inspect_LookAround`;
  - `Inspect_Write` (escreve na prancheta);
  - `Inspect_Point` (aponta para o móvel);
  - `Inspect_Stamp` (carimba);
  - `Inspect_ThumbsUp`;
  - `Inspect_HeadShake`;
  - `Inspect_HangSeal` (pendura o selo na porta).

## 12 · Engarrafamento — "Venda pela janela"

### Jogo
- Durante o engarrafamento, a cada 10–18 s um carro parado **buzina** e o motorista põe o braço para fora: quer **água** ou **refrigerante** (balão com o ícone do produto). O pedido vale por 15 s.
- O jogador clica no carro, e o repositor (ou o próprio dono, se não houver equipe) sai com o **isopor**, entrega a bebida e recebe o pagamento.
  - A venda gasta 1 unidade do estoque (depósito ou prateleira).
  - O motorista paga o preço da prateleira + 30% de gorjeta e conta como venda normal (XP, missões).
- Missão relâmpago: "Venda 6 bebidas para os motoristas" → bônus de moedas. Sem estoque daquele produto, o balão fica cinza ("acabou").

### Assets
- **Carros do engarrafamento** (`Rig_Car*`):
  - vidro do motorista separado, num bone `Window_Driver` que desce;
  - motorista visível (busto do personagem do jogo) com braço rigado (`Driver_Arm_L`) para acenar e pegar a garrafa;
  - "pulinho" da buzina na carroceria (`Body`).
- **Vendedor**: o repositor do jogo (Staff Clerk) com um **isopor** de alça no ombro, com tampa num bone que abre, gelo e garrafas de água e latas de refri dentro.
- **Props**: garrafa de água e lata de refri (as que já existem nos produtos), moedas, um ícone 3D de buzina (cone + ondas) para o balão.
- **Animações**:
  - vendedor: `Vendor_WalkCarry`, `Vendor_OpenCooler`, `Vendor_TakeBottle`, `Vendor_HandOver`, `Vendor_ReceiveCoin`;
  - motorista: `Driver_Honk`, `Driver_WaveOut`, `Driver_TakeBottle`, `Driver_Pay`;
  - carro: `Car_WindowDown` / `Car_WindowUp`, `Car_HonkBounce`.

## Ordem
1. Assets no Blender + fotos para aprovação.
2. Ao mesmo tempo, a regra de jogo em TS, com testes.
3. Depois da aprovação, exportação dos FBX, integração em `CheckoutEventVisuals.Scenes.cs` / `CheckoutEventDirector` (cliques, histórias) e QA por fotos em todos os estágios.
