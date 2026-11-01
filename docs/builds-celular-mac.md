# Builds do celular pelo Mac (iPhone e Android)

O PC Windows fica fora de alcance até o fim de novembro de 2026, então os builds de celular saem do MacBook (`~/repos/checkout`, Unity 6000.5.7f1). Ver também [[ios-testflight-e-app-store]] e [[diamantes-aceleracao-e-compras]] (seção Google Play).

## Como o Claude gera no Mac
- **Sincronizar o Mac com o main:** pedido `gitsync` no tool runner (arquivo `Logs/tool_request_2.txt`, resultado em `Logs/tool_result.txt`).
  - Ele guarda as mudanças locais num stash "backup copias do Claude <data>" e avança para origin/main.
  - Só com o OK do Lucas, porque mexe na cópia do Mac.
  - O download pode ser grande: ~380 MB em 01/11.
- **Lógica do jogo:** pedido `embedded`, que gera `Assets/Resources/CheckoutGame/game.txt`.
- **Unity em segundo plano:** os menus do Unity funcionam pela barra de menus em segundo plano, mesmo com o Lucas em outro app em tela cheia. Por exemplo `Assets › Refresh`, `Checkout › iPhone › Build for TestFlight`, `TestFlight 2 - Archive`, `TestFlight 3 - Upload` e `Checkout › Android › Build AAB for Play`.
- **Acompanhar:** pedido `editorlog` (copia o fim do Editor.log para `Logs/editor_log.txt`) e os logs `unity/builds/iphone-store/testflight-*.log`.

## iPhone
- **1.0 (8)** enviado ao TestFlight em 01/11 às 19:57 (upload ~8 min a ~2 MB/s), commit 2cb2f19. Traz as evoluções com recompensa, tempo e animação de revelação, e 50 produtos novos (ver [[evolucoes-recompensas]]).

## Android
- **Chave de upload nova:** a keystore do PC ficou no Windows, então a chave de upload foi trocada no Play Console. A troca foi pedida e aprovada (Lucas, 01/11).
  - A keystore nova fica em `~/keys/checkout-upload-mac.keystore` (alias `checkout`), junto com o `upload_certificate.pem` enviado ao Google (29/10).
  - `ProjectSettings.asset` aponta para esse caminho (commit c5f9bd4). As senhas ficam só com o Lucas e o Unity esquece ao reiniciar: ele digita em Player Settings › Android › Publishing Settings antes de cada build.
- **Como gerar no Mac:**
  1. File › Build Profiles › Android › Switch Platform. A troca reimporta as texturas e leva alguns minutos.
  2. Senhas da keystore digitadas pelo Lucas.
  3. `Checkout › Android › Build AAB for Play`.
  4. Fechar com Cancel o aviso "App Bundle size warning".
- **Teste interno:** versão **12 (1.0)** enviada em 01/11 (AAB de 425 MB, commit c5f9bd4), com:
  - evoluções com recompensa, tempo e animação de revelação;
  - 50 produtos novos.
  - Antes dela: 11 (1.0) "Fixes checkout".
- Login com Google: os builds instalados pelo Play são assinados pela chave de assinatura do Play, então o cliente "Checkout Android (Play)" continua valendo. O cliente "(upload)" tem o SHA-1 da chave antiga e só importa para um AAB/APK instalado direto, sem passar pelo Play.
