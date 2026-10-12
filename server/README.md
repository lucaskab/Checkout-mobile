# checkout-server — contas Google e progresso na nuvem

Node 22 (sem etapa de build: TypeScript com type stripping) + Prisma 6 + Postgres (Prisma Postgres, Frankfurt).
Publicado no Render (render.yaml na raiz do repo): https://checkout-server-babc.onrender.com

## Rotas
| Rota | O que faz |
|---|---|
| `POST /v1/auth/google {idToken}` | Login do celular (Credential Manager). Verifica o ID token do Google (assinatura, emissor, cliente do jogo, validade) e devolve `{token, player, save}` |
| `POST /v1/auth/google-code {code, codeVerifier, redirectUri}` | Login do PC/Editor: o código do navegador é trocado aqui (o segredo do cliente desktop fica só no servidor) |
| `GET /v1/save` | Progresso atual `{revision, updatedAt, summary, deviceId, data}` ou 404 |
| `PUT /v1/save {baseRevision, data, deviceId, force?}` | Substitui o progresso se a nuvem ainda está em `baseRevision`; senão 409 com o atual (o jogador escolhe) |
| `DELETE /v1/account` | Apaga conta, progresso e cópias |
| `GET /health` | `{ok:true}` |

Sessão: token próprio assinado (HMAC, 180 dias) no header `Authorization: Bearer`.

## Banco (prisma/schema.prisma)
- `players`: id, google_sub (único), email, name, datas.
- `cloud_saves`: o save inteiro (texto JSON) + revisão + resumo (nível, fase, moedas, diamantes, dia).
- `save_history`: até 10 cópias anteriores (no máximo uma por hora, e sempre quando o jogador força a troca).
Cada envio normal custa 2 operações no Prisma Postgres (o plano grátis inclui 200 mil por mês).

## Configuração (Render › Environment)
- `DATABASE_URL` — Prisma Postgres (segredo, colado pelo Lucas)
- `SESSION_SECRET` — gerado pelo Render
- `GOOGLE_CLIENT_IDS` — clientes OAuth do projeto Google Cloud "Checkout Game" (web + desktop)
- `GOOGLE_DESKTOP_CLIENT_ID` / `GOOGLE_DESKTOP_CLIENT_SECRET` — login do PC/Editor (segredo colado pelo Lucas)

## Testes
`npm test` (sem banco: store em memória). Com `DATABASE_URL`, roda também o teste no Postgres de verdade
(GitHub Actions: .github/workflows/server.yml). Migrações: `prisma migrate deploy` no build do Render.
