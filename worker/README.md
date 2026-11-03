# checkout-worker — contas Google e Apple e progresso na nuvem (Cloudflare, plano grátis)

O mesmo servidor de `server/` (Render), agora num **Cloudflare Worker** com **D1** (banco) e **R2** (arquivos).
Mesmas rotas, mesmos JSON e códigos de status, mesmo token de sessão: o jogo só precisa trocar o endereço.
`server/` continua no ar no Render, sem mudanças, para as versões antigas do jogo até os testers atualizarem.

- Endereço: **https://checkout-server.lucaslfurini.workers.dev** (`/health` mostra quais configurações existem, só os nomes)
- Worker `checkout-server` · D1 `checkout-saves` (`660aad42-3495-4b98-8e91-a727acecbae2`, Europa Ocidental) · R2 `checkout-saves` (Europa Ocidental)
- Sem dependências npm: TypeScript puro + WebCrypto. O pacote publicado tem ~78 KB (25 KB comprimido; o limite é 3 MB).

## Rotas (iguais às do Render)
| Rota | O que faz |
|---|---|
| `POST /v1/auth/google {idToken}` | Login do celular. Verifica o ID token do Google e devolve `{token, player, save}` |
| `POST /v1/auth/google-code {code, codeVerifier, redirectUri, client?}` | Login do PC/Editor (e `client: "ios"`: Google no iPhone) |
| `POST /v1/auth/apple {idToken, authorizationCode?, name?, nonce?}` | Entrar com Apple. Com `nonce`, o token tem que trazer o SHA-256 dele (builds de 29/10 em diante) |
| `GET /v1/save` | `{revision, updatedAt, summary, deviceId, data}` ou 404 |
| `PUT /v1/save {baseRevision, data, deviceId, force?}` | Substitui se a nuvem ainda está em `baseRevision`; senão 409 com o atual |
| `DELETE /v1/account` | Apaga conta, progresso, cópias e tudo do social (e revoga o login da Apple, se a chave estiver configurada) |
| `/v1/social/*`, `GET /i/<código>` | Amigos, convites, visitas, ajudas, presentes e pedidos — veja **Social (v1)** abaixo |
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
| 14 KB (tamanho real hoje) | 3–6 ms | 2 ms |
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

**Decisão (29/10):** os saves reais têm ~14 KB (o único save copiado do Render: 13,5 KB na revisão 30, dia 12;
as 8 cópias antigas vão de 5,7 a 17 KB), então o plano grátis aguenta com folga e o envio em partes não é necessário
agora. Vale rever se um save passar de ~100 KB.

`npm run bench` estima localmente o mesmo cálculo (Node usa o mesmo V8); `npm run bench:social` mede as rotas sociais.

## Social (v1) — amigos, convites, visitas, ajudas, presentes, pedidos
O contrato com o jogo é `docs/social-api.md` (rotas, formatos, números). Código: `src/social.ts` (rotas),
`src/store.ts` (D1), `src/limits.ts` (**todos os números num bloco só**), `src/names.ts` (nome do mercado e filtro de
palavrões), `src/codes.ts` (códigos de convite), `src/landing.ts` (página do convite). Testes: `test/social.test.ts`.

O save continua sendo do aparelho: ninguém escreve no save de outro jogador. Tudo que um amigo faz (presente, curtida,
ajuda, entrega, recompensa de convite) vira um item da **caixa de entrada** (`inbox`), que o jogo aplica no próprio
save e depois confirma (`ack`).

### Rotas (todas com `Authorization: Bearer <token>`, menos `/i/`)
| Rota | O que faz |
|---|---|
| `GET /v1/social/me` · `PUT /v1/social/me {marketName?, avatar?}` | Perfil (criado na primeira chamada: código de 8 letras, nível/era do save) e troca de nome/avatar |
| `GET /v1/social/friends` | Amigos (com o bloco público, presente/curtida de hoje, pedidos abertos), pedidos de amizade recebidos e enviados |
| `POST /v1/social/friends/add {code}` · `accept {id}` · `decline {id}` · `DELETE /v1/social/friends/<id>` | Adicionar pelo código, aceitar, recusar, desfazer amizade |
| `GET /v1/social/friends/<id>/market` | Visita: perfil + bloco público + o save do amigo (repassado como está guardado, sem recodificar) |
| `POST /v1/social/gift {to}` · `like {to}` · `help {to, buildId}` | Presente, curtida, ajuda numa obra (−5 min) |
| `GET/POST /v1/social/requests` · `DELETE …/requests/<id>` · `POST …/requests/<id>/fulfill` | Pedidos de produto: listar, criar, cancelar, atender |
| `GET /v1/social/inbox` · `POST /v1/social/inbox/ack {ids}` | Caixa de entrada e confirmação |
| `POST /v1/social/report {id}` | Denunciar nome de mercado |
| `POST /v1/social/invite/redeem {code}` | Usar um código de convite (conta com menos de 7 dias) |
| `GET /i/<código>` | Página do convite (pt-BR, en, es, fr, de pelo idioma do navegador; sem scripts externos, sem rastreamento) |

`PUT /v1/save` aceita também o bloco `public` opcional (obras em andamento, estágio, nota do mercado; ≤ 4 KB, ≤ 12
obras), que deve ser o **último campo** do corpo para o envio continuar barato. Versões antigas do jogo (sem `public`)
funcionam exatamente como antes. A cada envio o perfil (se existir) recebe o nível e a era do save — só quando algo
mudou, para não gastar escritas — e a recompensa de convite sai quando o convidado chega ao nível 8.

### Tabelas novas (D1)
`profiles` (código, nome, avatar, nível, era, curtidas, bloco público, quem convidou, recompensas),
`friends` (duas linhas por amizade), `friend_requests`, `inbox`, `daily_actions` (presente/curtida por dia),
`build_helps` (ajudas por obra; conta também as ajudas do dia), `product_requests`, `name_reports`.
Limpeza sem cron: itens confirmados há mais de 7 dias, pedidos fechados há mais de 7 dias, ajudas de mais de 30 dias e
contadores de dias passados são apagados durante as escritas do próprio jogador.

### Limites (dia = dia UTC; em `src/limits.ts`)
| O quê | Valor |
|---|---|
| Amigos | 50 por jogador (verificado dentro da escrita: dois aceites ao mesmo tempo não passam de 50) |
| Pedidos de amizade pendentes enviados | 20 |
| Presente | 1 por amigo por dia; quem recebe abre no máximo 25 por dia (o resto espera no servidor) |
| Curtida | 1 por amigo por dia |
| Ajuda | 1 por ajudante por obra; no máximo 10 por obra (também com ajudas simultâneas); 30 por ajudante por dia; 5 min cada |
| Pedidos de produto | 2 abertos; 1–20 unidades; vencem em 24 h; um amigo atende o pedido inteiro (atômico: só um ganha) |
| Convite | só contas com menos de 7 dias, uma vez, não o próprio código (nem o de quem você convidou) |
| Recompensa de convite | convidado no nível 8: 30 💎 para cada; marcos 1/3/5 convites (decorações `invite-reward-1/3/5`); uma vez só |
| Nome do mercado | 3–20 caracteres (letras de qualquer alfabeto, números, espaço, `' - & .`), lista de palavrões pt/en/es/fr/de; 3 denúncias diferentes escondem o nome até ele ser trocado |

### Custo por jogador (plano grátis)
CPU por requisição medida com `npm run bench:social` (o código do Worker de verdade, descontado o tempo do SQLite
local, que na Cloudflare roda no D1 e não no Worker), no pior caso — 50 amigos, cada um com bloco público de 4 KB e
2 pedidos abertos, 100 itens na caixa de entrada:

| Rota | CPU do Worker |
|---|---|
| `GET /v1/social/friends` (50 amigos) | ~2–2,5 ms |
| `GET /v1/social/inbox` (100 itens) | ~1 ms |
| `GET /v1/social/friends/<id>/market` (save de 14 KB) | ~0,7–0,8 ms |
| `GET /v1/social/requests`, `PUT /v1/social/me` | ~1 ms |
| `help`, `like`, `fulfill`, `GET me`, `/i/<código>` | ~0,3–0,7 ms |
| `PUT /v1/save` com bloco público | igual a sem (o bloco é recortado do fim do corpo) |

Tudo bem abaixo dos 10 ms. Cada rota social faz 2 idas ao D1 (perfil + ação; adicionar/aceitar/convite fazem 3) e a
visita faz 1 leitura no R2.

Estimativa por hora de jogo de um jogador com ~10 amigos (o jogo atualiza caixa de entrada + amigos a cada 5 min e
faz ~10 ações por hora):
- **Requisições Worker:** +15–25 por hora (além das ~12–15 do save) → os 100 mil/dia dão para ~2.500–3.500 horas de
  jogo por dia.
- **D1 linhas lidas:** ~1–1,5 mil por hora (a lista de amigos lê ~6 linhas por amigo) → 5 milhões/dia dão para
  ~3.500 horas de jogo. Com 50 amigos a lista custa ~300 linhas: vale o jogo atualizar a lista de amigos só com a
  página Amigos aberta (ou a cada 15 min) e a caixa de entrada a cada 5 min.
- **D1 linhas escritas:** ~2–4 por ação (item da caixa + marca do dia + índice) e ~2 por item confirmado → ~40–60 por
  hora; somadas às do save, as 100 mil/dia dão para ~1.500–2.000 horas de jogo por dia. É o primeiro limite a
  apertar com muitos jogadores.
- `PUT /v1/save`: +1 linha lida por envio (o perfil vem junto com o jogador, na mesma ida ao D1); escreve no perfil só
  quando nível, era ou bloco público mudam.
- Apagar conta lê as tabelas `inbox`, `daily_actions`, `product_requests` e `name_reports` inteiras (raro).

### Aplicar a migração no D1 (antes de publicar esta versão)
1. Cloudflare › **Storage & Databases › D1 › checkout-saves › Console**.
2. Colar o conteúdo inteiro de `worker/migrations/0002_social.sql` e executar. Se o console reclamar das linhas de
   comentário (`--`), apague-as e execute de novo; se reclamar de vários comandos juntos, execute um `CREATE` por vez.
   Pode rodar quantas vezes quiser: só cria o que falta (`CREATE TABLE/INDEX IF NOT EXISTS`) e nunca mexe nos dados.
3. Conferir: `SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;` deve listar `build_helps`,
   `daily_actions`, `friend_requests`, `friends`, `inbox`, `name_reports`, `product_requests` e `profiles` (além de
   `players`, `cloud_saves`, `save_history`).

Com wrangler logado, o mesmo: `npx wrangler d1 execute checkout-saves --remote --file=migrations/0002_social.sql`.
Se a versão nova for publicada antes da migração, os saves continuam funcionando normalmente (o Worker percebe que
as tabelas não existem e ignora o social); só as rotas sociais dão erro até a migração rodar.

## Rankings (v1) — amigos, liga semanal, mundo e país
Contrato: `docs/rankings-api.md` (com "Details settled"). Código: `src/rankings.ts` (rotas), `src/ranking-store.ts`
(SQL dos placares e da liga, fechamento da semana), números em `src/limits.ts` (`RANKINGS`, `MAX_LEVEL`, divisões,
prêmios). `PUT /v1/save` passa a gravar no perfil nível, XP, país (de `request.cf.country`) e os avisos do anti-cheat
no mesmo lote do envio (sem ida extra ao D1).

### CPU estimada (`npm run bench:rankings`: 20 mil perfis, 50 amigos, grupo de 30, 500 grupos para fechar)
| Rota | Worker (CPU) | SQLite local (≈ trabalho do D1) |
|---|---|---|
| `GET /v1/rankings/world` sem cache, logado | ~1,4 ms | ~2,8 ms |
| `GET /v1/rankings/world` com o top na memória | ~0,6 ms | ~0,9 ms |
| `GET /v1/rankings/country` sem cache | ~0,8 ms | ~1,2 ms |
| `GET /v1/rankings/friends` (50 amigos) | ~0,6 ms | ~1,2 ms |
| `GET /v1/rankings/league` | ~0,6 ms | ~0,7 ms |
| `POST /v1/rankings/league/points` | ~0,5 ms | ~0,6 ms |
| cron: fechar 500 grupos (15 mil jogadores, 6 lotes) | ~1,4 ms no total | ~145 ms no total |

Custos D1: o "minha posição" (`me.rank`) lê ~1 linha por jogador à minha frente (quem está em #10 000 lê ~10 mil
linhas por abertura da aba Mundo); o top 100 e o total ficam 10 min em cache (memória do isolate + Cache API — que pode
não guardar nada em `*.workers.dev`; a memória já basta para segurar o D1). O fechamento da semana escreve ~4 linhas por
jogador da liga (lugar, divisão, item da caixa de entrada) uma vez por semana.

### Antes de publicar esta versão
1. **Migração (uma vez só):** Cloudflare › Storage & Databases › D1 › checkout-saves › Console. Conferir antes:
   `SELECT name FROM pragma_table_info('profiles') WHERE name = 'league_division';` — sem linhas = ainda não rodou.
   Colar o conteúdo inteiro de `worker/migrations/0003_rankings.sql` e executar (se o console reclamar dos comentários
   `--`, apague-os). **Não rode duas vezes:** o D1 não tem `ADD COLUMN IF NOT EXISTS`; a segunda vez para no primeiro
   `ALTER` com "duplicate column name: xp" (sem estragar nada, mas o que vem depois não roda). Se parar no meio, rode só
   as linhas que faltam. Conferir depois: `SELECT name FROM sqlite_master WHERE name LIKE 'league_%' OR name LIKE 'profiles_rank%';`
   deve listar `league_groups`, `league_members`, os índices `league_*` e `profiles_rank`, `profiles_rank_country`.
   Com wrangler: `npx wrangler d1 execute checkout-saves --remote --file=migrations/0003_rankings.sql`.
2. **Cron:** Workers › checkout-server › Settings › Triggers › Cron Triggers › Add → `5 0 * * 1` (segunda 00:05 UTC).
   Sem o cron a liga fecha mesmo assim, aos poucos, nas primeiras chamadas da liga da semana nova.
3. Publicar o Worker. Se for publicado antes da migração, saves, social e exclusão de conta seguem normais; só as
   rotas `/v1/rankings/*` dão erro 500 até a migração rodar.

## Testes
`npm test` — roda o código do Worker no Node 22 com substitutos de D1 (SQLite do Node, com o `schema.sql` de
verdade), R2 (memória) e sockets (node:net/tls). Os testes do Render (`server/test/api.test.ts`) estão portados.
Com `OLD_TEST_DATABASE_URL` (um Postgres com senha SCRAM e TLS), roda também a cópia de ponta a ponta contra as
migrações do Prisma do Render (`test/migrate.test.ts`). `test/social.test.ts` cobre todas as rotas sociais e limites
(com o relógio injetável `now`), a migração rodando duas vezes sobre o banco de hoje e a exclusão de conta.

## Publicar
`npm run build` (bun) gera `dist/index.js`. Com o wrangler logado: `npx wrangler deploy` (usa `wrangler.jsonc`).
Sem wrangler: upload pela API da Cloudflare (`PUT /accounts/<id>/workers/scripts/checkout-server`, multipart com o
módulo e os bindings de `wrangler.jsonc`, `keep_bindings: ["secret_text"]` para não apagar os segredos).
