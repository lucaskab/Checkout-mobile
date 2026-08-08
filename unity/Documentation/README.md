# Checkout Unity

Protótipo mobile do supermercado em Unity 6, com câmera ortográfica isométrica fixa e um mapa 3D estilizado inspirado nas referências fornecidas.

## Rodar no editor

Abra esta pasta no Unity `6000.5.7f1` e abra `Assets/Scenes/Supermarket.unity`. A cena também é criada automaticamente pelo menu `Checkout > Build Supermarket Scene`.

No editor, clique no mapa e use os mesmos botões da HUD para testar:

- `ABRIR MERCADO`: ativa clientes, vendas, XP e satisfação.
- `REABASTECER`: move unidades do estoque para a gôndola selecionada.
- `PEDIR CARGA`: agenda uma entrega do fornecedor.
- `PRODUZIR`: inicia a receita da Padaria e coloca baguetes no estoque ao terminar.
- `CONSTRUIR`: entra no modo de customização; toque/clique em um marcador para comprar e posicionar uma ilha promocional.

O projeto começa com quatro áreas desbloqueadas: Hortifruti, Laticínios, Padaria e Mercearia. O quinto slot é liberado ao chegar no nível 2 e custa moedas para ser colocado.

## Direção de arte integrada

O cenário jogável é construído em runtime com geometria 3D: terreno contínuo de grama, piso cerâmico texturizado, paredes baixas com acabamento, entrada, árvores, canteiros, estoque, caixa, padaria e fornecedor. `Assets/Resources/Art/market-floor-tile-v1.png` é aplicado ao piso e `Assets/Resources/Art/market-wall-teal-v1.png` às paredes, estoque e caixa; eles dão a variação suave de cor e acabamento da referência sem transformar o mapa em uma imagem 2D. `Assets/Resources/Art/market-map-v2.png` permanece como referência visual e não é usado como chão do jogo.

O pacote visual adicional `Assets/Resources/Art/market-asset-sheet-v1.png` reúne a padaria, plantações e cercas em estilo low-poly isométrico, com fundo removido e objetos separados. Ele serve como fonte visual para os próximos prefabs 3D; o mapa jogável continua usando meshes 3D independentes para preservar profundidade, iluminação e customização. Os clientes usam billboards com alpha em `Assets/Resources/Characters/`; os clientes coral e mostarda possuem ciclos de caminhada em `customer-coral-walk-v1.png` e `customer-mustard-walk-v1.png`, e os expositores dos setores usam o atlas `Assets/Resources/Sectors/sector-display-atlas-v1.png`.

Se o Unity ainda estiver aberto enquanto esses arquivos forem adicionados, aguarde o import terminar ou reabra a cena para atualizar os assets.

## Integração futura com React Native

`Assets/Scripts/Runtime/UnityGameBridge.cs` define uma ponte pequena e agnóstica de engine:

- `ApplySnapshot(string json)` recebe o estado persistido pelo Zustand/MMKV.
- `RequestAction(string json)` recebe ações do app host.
- `UnityActionEmitted` publica vendas, entregas, produção e construção para o host.

O contrato usa arrays em vez de dicionários para funcionar com `JsonUtility` e com a serialização do lado TypeScript. O arquivo `bridge/game-state-contract.json` documenta o payload inicial.

O protótipo standalone salva em `Application.persistentDataPath`; no produto integrado, o snapshot do app host deve ser a fonte de verdade e esse save local deve ser desativado.
