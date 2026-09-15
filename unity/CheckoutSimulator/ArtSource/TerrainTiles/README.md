# Cidade do supermercado

O mapa ativo usa a imagem fornecida `Codex Image Sep 11, 2026, 01_52_56 AM.png`, copiada sem alterações para `Assets/Art/CityTiles/CityTileset.png`. Dez sprites foram recortados no Sprite Editor por metadados, sem modificar a imagem original. O Tilemap usa células de 4 × 4 unidades e normaliza os recortes de dimensões diferentes.

O shader desenha asfalto e sinalização em coordenadas globais: não repete as sombras de borda dos recortes. A máscara de vizinhos controla a mesma largura de rua e raio de esquina em todos os cruzamentos. As normais do chão apontam para cima; o asfalto usa cinza frio e variação fina contínua. Entradas conectam também ao asfalto do estacionamento e pátio. Calçadas e praças preservam a arte fornecida.

Rua e faixa de pedestres compartilham conexões de RuleTile: retas, curvas, cruzamentos T e cruzamentos completos, com rotação automática. Calçada, praça e asfalto completam os quarteirões. O cenário inclui estacionamento, fachadas comerciais, iluminação e árvores em canteiros. O cercado, animais e decoração rural estão desativados na cena; mercado, depósito e entregas são preservados.

Abra **Supermarket → Terrain Painter** para pintar Rua, Faixa de pedestres, Calçada, Praça ou Asfalto. Os recortes de borda e esquina de calçada também estão disponíveis para composição manual. Calçada substitui ruas; Cmd/Ctrl+Z desfaz a pintura. Salve a cena após editar.

**Apply city tileset** aplica a composição inicial somente uma vez (`MarketOutdoorLayout.cityVersion`); reaplicações preservam a pintura. **Preview current level** executa o jogo e verifica as rotas sem reconstruir os modelos. **Capture city preview** salva `CityPreview.png`.

O pincel altera o visual. Pintar ruas não cria novas rotas de gameplay automaticamente.

## Calçadas conectadas e ruas ampliadas

**Supermarket → Upgrade streets and sidewalks** aplica uma migração única à cena atual, mantendo os modelos e as alterações do mercado. `Connected City Sidewalks` contém 19 trechos navegáveis e seis acessos calculados a partir dos prédios existentes. Pedestres percorrem as calçadas e travessias até a entrada do mercado. O terreno usa `_WideStreets` para desenhar avenidas contínuas de 6 m, com duas faixas de 3 m e calçadas de 2 m.

Os carros têm largura de aproximadamente 2,1 m, com a orientação visual corrigida. A entrada está alinhada ao corredor x = -11,2, separada das vagas, e o antigo portal foi removido. As novas vagas preservam as posições atendidas pelo controlador. A ré é usada somente na manobra de saída da vaga; nas ruas os veículos seguem de frente.

## Modelos e clientes de carro

Os seis GLBs fornecidos ficam preservados em `ArtSource/MapModels`: CuteHouse, StylizedBuilding, StylizedHouse, CartoonCar, StylizedCar e ToyVan. `scripts/blender/prepare_map_models.py` converte os originais para FBX e texturas em `Assets/Art/Models/MapModels`, seguindo o fluxo existente do projeto.

**Supermarket → Apply supplied city buildings and traffic** substitui as fachadas e carros provisórios. Os novos modelos estão em `Supplied City Models`; mercado, depósito e caminhões de entrega permanecem separados.

`CheckoutCityTraffic` reserva um veículo e sua vaga, percorre a rua, estaciona e entrega o cliente ao `CheckoutWalker`. A malha de navegação inclui o corredor do estacionamento até a entrada. O cliente usa as animações existentes de compras e pagamento, volta ao carro e só então o veículo sai pelo bairro. As manobras têm acesso exclusivo e os carros cedem passagem aos pedestres. Uma nova sessão cancela visitas anteriores e libera as reservas.

As visitas continuam sendo projeções dos snapshots de `CheckoutBridge`: a Unity não credita dinheiro nem desconta estoque novamente. Com os carros ocupados, novas visitas aguardam na fila. Cenas sem o controlador mantêm a chegada a pé anterior.

**Supermarket → Preview city customer traffic** envia seis visitas de teste e verifica acesso às três vagas, pagamento e saída de todos os carros. Validação executada: `CITY_TRAFFIC_PLAYTEST_OK parked=6 paid=6 departed=6`, sem erros no Console. Durante essa verificação o tempo fica em 3×; ao concluir ou parar, volta a 1×. O jogo integrado recebe as visitas normalmente pelos snapshots do aplicativo.

## Histórico do terreno anterior

# Terreno pintado

As texturas `Grass.png`, `Road.png` e `Water.png` foram geradas separadamente com o Image Gen integrado. Os prompts completos estão em `prompts.json`; os PNGs usados no jogo estão em `Assets/Art/TerrainTiles`.

O terreno usa um Tilemap nativo no plano XZ, com células de 4 × 4 unidades. O nível melhorado tem 20 × 21 células (80 × 84 unidades). Os assets herdam de `RuleTile`, do pacote `com.unity.2d.tilemap.extras` 8.0.3, compatível com Unity 6000.5. Grama, rio e pátio têm 47 regras de oito vizinhos; estrada, caminho e ponte têm 16 regras de conexão. O rio pode ocupar várias células de largura sem margens internas. O material preserva as texturas existentes e acrescenta variação na grama, acostamentos, pavimento, margens e água animada.

## Pintar no Unity

1. Abra `Assets/Scenes/Supermarket.unity` e saia do Play Mode.
2. Abra **Supermarket → Terrain Painter**.
3. Escolha **Grama**, **Estrada**, **Rio**, **Pátio**, **Caminho** ou **Ponte**, ajuste o tamanho e marque **Ativar pintura**.
4. Clique e arraste sobre o chão na janela **Scene**. Grama remove estradas/rios; Cmd/Ctrl+Z desfaz o traço.
5. Salve a cena com Cmd/Ctrl+S. Desative a pintura para voltar a selecionar objetos normalmente; Alt continua disponível para navegar na cena.

**Apply painted terrain and expanded yard** preserva os tiles já pintados e não acumula deslocamentos do depósito/caminhões. **Build fresh scene** recria a composição inicial e substitui a cena inteira.

**Improve terrain with RuleTiles** aplica a melhoria uma única vez à cena ativa: passeio em frente ao mercado e ao lado do acesso de serviço, ligação rodoviária com ponte, travessia de pedestres e margens com pedras e juncos. Chamadas posteriores atualizam as regras sem repintar o nível. A versão aplicada fica em `MarketOutdoorLayout.terrainVersion`.

Para uma ponte nova, pinte Ponte sobre o rio, ligando os lados opostos a Estrada; o piso acompanha a conexão. Os corrimãos da ponte inicial são detalhes da cena em `Riverbank Details`. Os caminhos ligam suas pontas ao pavimento sem criar cruzamentos repetidos quando passam ao lado de uma estrada ou pátio.

Os sprites originais foram analisados em uma grade 3 × 3: as três texturas são superfícies pintadas, sem sprites de borda separados. Por isso, as regras usam o mesmo sprite e enviam a máscara de vizinhança ao shader. As regras mais específicas vêm primeiro; o ID da regra codifica a máscara. Use **Terrain Painter** para editar o nível e `CheckoutTerrainRules.Configure` para regenerar regras, preservando esses IDs.

**Validate terrain RuleTiles** verifica 1.024 vizinhanças pelo pipeline real do Tilemap, conexões entre terrenos, atualização ao apagar, compilação do shader, preservação do pátio e reaplicação sem mudanças na cena.

O depósito foi deslocado 8 unidades para trás e o conjunto de entregas 6 unidades, abrindo aproximadamente 9,7 unidades entre o mercado e o depósito. A área pavimentada, o acesso de serviço, a navegação e os limites da câmera acompanham o novo espaço.

O pátio tem três vagas demarcadas, batentes, faixa de carga, setas de circulação, travessia de pedestres, calçada, canteiro, banco e postes. Os caminhões foram deslocados também 1,5 unidade para a direita para liberar o corredor lateral de carga. As marcações acompanham as posições reais dos veículos. A decoração está agrupada em `Loading Yard Details`, com malhas combinadas por material.

Os modelos fornecidos de vaca, árvore e floreira estão integrados ao cercado e ao paisagismo: nove árvores e nove floreiras. Os modelos originais ficam em `ArtSource/MapModels`; as versões usadas no Unity em `Assets/Art/Models/MapModels`. A vaca mantém o movimento ambiente do objeto original.

O pincel altera o visual do terreno no editor. Rotas de clientes e funcionários continuam vinculadas aos acessos do mercado; pintar uma estrada não cria automaticamente novas rotas de gameplay.

## Correções de detalhes

A entrada usa uma superfície contínua entre a calçada (0,15 m) e o piso do mercado (0,74 m), acompanhada pela malha de navegação. A peixaria foi restaurada, a queijaria foi apoiada no piso e seu funcionário acompanha o balcão atual. Os produtos antigos soltos da padaria ficam com os renderizadores desativados para que novos snapshots não os façam reaparecer.

O banco danificado e a faixa do pátio assinalados na referência foram removidos. As nove árvores foram reposicionadas em canteiros fora das portas e dos corredores de pedestres. `CheckoutShoppingProps` oculta cestas nos pedestres da cidade e na chegada de carro; mostra durante a compra e oculta ao retornar ao veículo.

Validação: seis visitas completas com pagamento e saída, cestas dos pedestres ocultas, cestas removidas no retorno ao carro e caminhos válidos pela entrada até os balcões.
