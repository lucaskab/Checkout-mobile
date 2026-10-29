# checkout-worker — contas Google e Apple e progresso na nuvem (Cloudflare, plano grátis)

O mesmo servidor de `server/` (Render), agora num **Cloudflare Worker** com **D1** (banco) e **R2** (arquivos).
Mesmas rotas, mesmos JSON e códigos de status, mesmo token de sessão: o jogo só precisa trocar o endereço.
`server/` continua no ar no Render, sem mudanças, para as versões antigas do jogo até os testers atualizarem.

- Endereço: **https://checkout-server.lucaslfurini.workers.dev** (`/health` mostra quais configurações existem, só os nomes)
- Worker `checkout-server` · D1 `checkout-saves` (`660aad42-3495-4b98-8e91-a727acecbae2`, Europa Ocidental) · R2 `checkout-saves` (Europa Ocidental)
- Sem dependências npm: TypeScript puro + WebCrypto. O pacote publicado tem ~34 KB (14 KB comprimido; o limite é 3 MB).

## Rotas (iguais às do Render)
| Rota | O que faz |
|---|---|
| `POST /v1/auth/google {idToken}` | Login do celular. Verifica o ID token do Google e devolve `{token, player, save}` |
| `POST /v1/auth/google-code {code, codeVerifier, redirectUri, client?}` | Login do PC/Editor (e `client: "ios"`: Google no iPhone) |
| `POST /v1/auth/apple {idToken, authorizationCode?, name?, nonce?}` | Entrar com Apple. Com `nonce`, o token tem que trazer o SHA-256 dele (builds de 29/10 em diante) |
| `GET /v1/save` | `{revision, updatedAt, summary, deviceId, data}` ou 404 |
| `PUT /v1/save {baseRevision, data, deviceId, force?}` | Substitui se a nuvem ainda está em `baseRevision`; senão 409 com o atual |
| `DELETE /v1/account` | Apaga conta, progresso e cópias (e revoga o login da Apple, se a chave estiver configurada) |
| `GET /health` | `{ok, settings: {NOME: true/false}, storage}` — nunca mostra valores |

Sessão: o mesmo token HMAC de 180 dias do Render, com o **mesmo `SESSION_SECRET`** — quem já entrou continua logado.

## Onde ficam os dados
- **D1** (`schema.sql`): `players` (mesmos ids do Render), `cloud_saves` (revisão, resumo, aparelho, data e *onde* está o save no R2), `save_history` (até 10 cópias).
- **R2**: o save em si (até 2 MB, mais do que uma linha do D1 aceita) e as cópias antigas. Cada envio grava um objeto
  novo; o D1 só passa a apontar para ele se a nuvem ainda estiver na revisão que o aparelho conhecia (dois celulares
  ao mesmo tempo: um ganha, o outro recebe 409). Só depois disso o objeto anterior é apagado — ou vira cópia (a cópia
  é o mesmo objeto, sem duplicar). Se algo falhar no meio, o save anterior continua lá.
- O save fica guardado já como texto JSON entre aspas (como viaja dentro da resposta), para o download não gastar
  CPU re-codificando 2 MB.

## Configuração (Workers › checkout-server › Settings › Variables and Secrets)
Variáveis (públicas, já configuradas): `GOOGLE_CLIENT_IDS`, `GOOGLE_DESKTOP_CLIENT_ID`, `APPLE_BUNDLE_IDS`,
`ADMIN_PUBLIC_KEY` (temporária, só durante a mudança — veja abaixo).

Segredos (tipo **Secret**, colados pelo Lucas, iguais aos do Render › Environment):
- `SESSION_SECRET` — **copiar exatamente o do Render** (senão todo mundo é deslogado)
- `GOOGLE_DESKTOP_CLIENT_SECRET` — login do PC/Editor
- `GOOGLE_IOS_CLIENT_ID` — se existir no Render (login do Google no iPhone)
- `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` — se existirem no Render (revogar login da Apple ao apagar conta)
- `OLD_DATABASE_URL` — temporário: o `DATABASE_URL` do Render (Prisma Postgres, `postgres://…`), só para copiar os dados. Apagar depois.

Enquanto `SESSION_SECRET` não existe, só `/health` responde (as rotas do jogo dão 503 `not-configured`).

## Mudança do Render para cá (cópia dos dados)
A cópia lê o banco antigo direto do Worker (cliente Postgres próprio em `src/pg.ts`: TLS + SCRAM) e só devolve
contagens. Rotas temporárias em `/admin/*` (`src/admin.ts`), que só existem enquanto `ADMIN_PUBLIC_KEY` existir e só
aceitam um token assinado com a chave privada correspondente (que nunca sai do computador de quem roda a cópia;
`node scripts/admin-token.ts <chave.pem> 120` gera um token de até 2 h). Nenhum segredo extra fica na Cloudflare.

1. `GET /admin/migrate/plan` — quantos jogadores/saves/cópias há de cada lado, e os tamanhos.
2. `POST /admin/migrate/players` — todos os jogadores (mesmo id: os tokens continuam valendo).
3. `POST /admin/migrate/saves?after=<id>&limit=N` — os saves, alguns por chamada (repetir com `after = next` até `finished`).
4. `POST /admin/migrate/history?after=<id>&limit=N` — as cópias antigas.
5. `GET /admin/migrate/verify-saves` e `verify-history` — prova jogador por jogador: mesma revisão, mesmo resumo e
   **mesmos bytes** (o etag do R2 é o MD5 do conteúdo e é comparado com o `md5` que o próprio Postgres calcula).

Tudo pode rodar de novo quantas vezes quiser (nada é copiado duas vezes) e nunca apaga progresso:
- jogador ainda sem save aqui → o save do Render vira o save (mesma revisão: o jogo vê "sincronizado");
- save aqui ainda é a cópia e o Render tem revisão mais nova (versão antiga do jogo) → a mais nova entra, a anterior vira cópia;
- o jogador já jogou aqui **e** o Render recebeu outra revisão (outro celular com versão antiga) → a do Render vira cópia (`old_id "s:…"`), nunca é descartada;
- alguém que entrou aqui primeiro com a mesma conta Google/Apple de um jogador do Render → é a mesma conta.

Roteiro: copiar → verificar → publicar a versão do jogo com o endereço novo → rodar a cópia de novo de vez em quando
enquanto houver versões antigas jogando → no fim apagar `OLD_DATABASE_URL` e `ADMIN_PUBLIC_KEY` (as rotas somem) e
desligar o Render.

## Custos e limites (plano Workers Free + R2 com franquia)
| Limite | Grátis | Uso |
|---|---|---|
| Requisições Worker | 100 mil/dia | ~12–15 por hora de jogo por jogador (envio a cada 5 min + login) |
| CPU por requisição | 10 ms | ver medições abaixo |
| D1 | 5 milhões linhas lidas, 100 mil escritas por dia, 5 GB | 1–3 linhas por envio |
| R2 | 10 GB, 1 milhão de escritas (classe A) e 10 milhões de leituras (B) por mês; apagar é grátis | 1 escrita por envio, 1 leitura por download |
| Corpo da requisição | 100 MB | save ≤ 2 MB |

O que acaba primeiro com muitos jogadores: escritas do R2 (1 milhão/mês ≈ 33 mil envios/dia) e o espaço (save + 10
cópias por jogador).

### CPU medida no Worker publicado (Workers Logs, `cpuTimeMs`, saves sintéticos no formato do jogo)
| Save | PUT /v1/save | GET /v1/save |
|---|---|---|
| 50 KB | 6–15 ms | 3–5 ms |
| 200 KB | 11–17 ms | 3–4 ms |
| 500 KB | 20–52 ms | 4–5 ms |
| 1 MB | 38–61 ms | 5–7 ms |
| 2 MB | 78–133 ms | 7–9 ms |

(Inclui ~1–3 ms de verificação do token de admin, que as rotas do jogo não têm. A linha de 2 MB foi medida antes de
uma otimização que tirou duas recodificações do envio; nas outras faixas ela mudou pouco, porque o custo é ler o JSON.) O download é barato em qualquer
tamanho. O envio passa dos 10 ms a partir de ~100–200 KB, porque o Worker precisa ler o JSON (e o save dentro
dele) para validar e tirar o resumo. Nas medições a Cloudflare não derrubou nenhuma requisição (todas "ok"), mas
isso não é garantido no plano grátis: se derrubar, o jogo mostra erro de sincronização e tenta de novo — o progresso
local nunca se perde, só a cópia na nuvem fica para trás. Se isso acontecer, o caminho é o envio em partes (o jogo
manda o save em pedaços de ~256 KB sem precisar o Worker ler o JSON inteiro) — exige mudar o jogo.

`npm run bench` estima localmente o mesmo cálculo (Node usa o mesmo V8).

## Testes
`npm test` — roda o código do Worker no Node 22 com substitutos de D1 (SQLite do Node, com o `schema.sql` de
verdade), R2 (memória) e sockets (node:net/tls). Os testes do Render (`server/test/api.test.ts`) estão portados.
Com `OLD_TEST_DATABASE_URL` (um Postgres com senha SCRAM e TLS), roda também a cópia de ponta a ponta contra as
migrações do Prisma do Render (`test/migrate.test.ts`).

## Publicar
`npm run build` (bun) gera `dist/index.js`. Com o wrangler logado: `npx wrangler deploy` (usa `wrangler.jsonc`).
Sem wrangler: upload pela API da Cloudflare (`PUT /accounts/<id>/workers/scripts/checkout-server`, multipart com o
módulo e os bindings de `wrangler.jsonc`, `keep_bindings: ["secret_text"]` para não apagar os segredos).
