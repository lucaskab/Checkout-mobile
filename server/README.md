# checkout-server — contas Google e Apple e progresso na nuvem

Node 22 (sem etapa de build: TypeScript com type stripping) + Prisma 6 + Postgres (Prisma Postgres, Frankfurt).
Publicado no Render (render.yaml na raiz do repo): https://checkout-server-babc.onrender.com

## Rotas
| Rota | O que faz |
|---|---|
| `POST /v1/auth/google {idToken}` | Login do celular (Credential Manager). Verifica o ID token do Google (assinatura, emissor, cliente do jogo, validade) e devolve `{token, player, save}` |
| `POST /v1/auth/google-code {code, codeVerifier, redirectUri, client?}` | Login do PC/Editor: o código do navegador é trocado aqui (o segredo do cliente desktop fica só no servidor). `client: "ios"` = login do Google no iPhone (cliente iOS, sem segredo, redirect `com.googleusercontent.apps.<id>:/oauth2redirect`) |
| `POST /v1/auth/apple {idToken, authorizationCode?, name?}` | Entrar com Apple (iPhone). Verifica o token da Apple (assinatura, emissor, bundle id, validade). O nome vem do celular (a Apple só manda no primeiro login). Com a chave da Apple configurada, guarda o refresh token para revogar quando a conta for apagada |
| `GET /v1/save` | Progresso atual `{revision, updatedAt, summary, deviceId, data}` ou 404 |
| `PUT /v1/save {baseRevision, data, deviceId, force?}` | Substitui o progresso se a nuvem ainda está em `baseRevision`; senão 409 com o atual (o jogador escolhe) |
| `DELETE /v1/account` | Apaga conta, progresso e cópias |
| `GET /health` | `{ok:true}` |

Sessão: token próprio assinado (HMAC, 180 dias) no header `Authorization: Bearer`.

## Banco (prisma/schema.prisma)
- `players`: id, google_sub ou apple_sub (únicos), apple_refresh (para revogar), email, name, datas.
- `cloud_saves`: o save inteiro (texto JSON) + revisão + resumo (nível, fase, moedas, diamantes, dia).
- `save_history`: até 10 cópias anteriores (no máximo uma por hora, e sempre quando o jogador força a troca).
Cada envio normal custa 2 operações no Prisma Postgres (o plano grátis inclui 200 mil por mês).

## Configuração (Render › Environment)
- `DATABASE_URL` — Prisma Postgres (segredo, colado pelo Lucas)
- `SESSION_SECRET` — gerado pelo Render
- `GOOGLE_CLIENT_IDS` — clientes OAuth do projeto Google Cloud "Checkout Game" (web + desktop)
- `GOOGLE_DESKTOP_CLIENT_ID` / `GOOGLE_DESKTOP_CLIENT_SECRET` — login do PC/Editor (segredo colado pelo Lucas)
- `GOOGLE_IOS_CLIENT_ID` — opcional: login do Google no iPhone (cliente "iOS" do Google Cloud; também vai em `GOOGLE_CLIENT_IDS`)
- `APPLE_BUNDLE_IDS` — Entrar com Apple: bundle ids do app (o primeiro é o client id da API de tokens da Apple)
- `APPLE_TEAM_ID` / `APPLE_KEY_ID` / `APPLE_PRIVATE_KEY` — opcional: chave "Sign in with Apple" do Apple Developer (o texto do .p8), para revogar o login da Apple ao apagar a conta (regra 5.1.1(v) da App Store)

## Testes
`npm test` (sem banco: store em memória). Com `DATABASE_URL`, roda também o teste no Postgres de verdade
(GitHub Actions: .github/workflows/server.yml). Migrações: `prisma migrate deploy` no build do Render.
