import json, math, sys
E=['mesinha','tenda','banca','conteiner','spati','quitanda','minimercado','mercadinho','supermercado','hipermercado','rede']
# Level a regular player has when each expansion opens (from the robot); products open from there.
BASE=[1,2,5,6,8,11,15,19,25,33,45]
for a in sys.argv[1:]:
    if a.startswith('['): BASE=json.loads(a)
S=[
(1,'Tomate','hortifruti',0,6,10,74,72,['familia','normal']),
(47,'Alface','hortifruti',0,3,6,62,58,['familia','premium']),
(46,'Banana','hortifruti',0,4,7,80,76,['familia','economico']),
(21,'Água mineral','aguas',0,2,4,90,70,['normal','impulsivo']),
(14,'Refrigerante','refrigerantes',0,5,9,84,82,['impulsivo','familia']),
(48,'Batata','hortifruti',1,4,7,76,70,['familia','economico']),
(3,'Cenoura','hortifruti',1,3,5,70,62,['familia','economico']),
(49,'Maçã','hortifruti',1,5,9,68,66,['familia','premium']),
(50,'Ovos','ovos',1,9,15,84,80,['familia','normal']),
(13,'Suco natural','bebidas',1,5,9,66,64,['normal','impulsivo']),
(9,'Pão francês','padaria',1,3,6,96,94,['familia','economico']),
(62,'Uva','hortifruti',1,6,11,56,58,['premium','familia']),
(5,'Leite integral','laticinios',2,5,8,92,90,['familia','normal']),
(8,'Iogurte','laticinios',2,6,11,57,58,['normal','premium']),
(7,'Manteiga','laticinios',2,9,15,46,48,['familia','normal']),
(2,'Brócolis','hortifruti',2,6,10,48,45,['premium','normal']),
(4,'Pimentão','hortifruti',2,5,9,42,40,['normal','premium']),
(56,'Pão de forma','padaria',2,7,12,70,68,['familia','normal']),
(22,'Energético','energeticos',3,7,13,62,60,['impulsivo','normal']),
(25,'Bolacha recheada','bolachas',3,4,8,76,74,['impulsivo','familia']),
(23,'Bala de gelatina','doces',3,2,5,79,70,['impulsivo']),
(12,'Waffle','doces',3,6,11,54,52,['impulsivo','premium']),
(6,'Queijo prato','queijos',3,14,24,52,54,['familia','premium']),
(60,'Cerveja','alcoolicos',4,4,8,86,84,['normal','impulsivo']),
(55,'Café em pó','mercearia',4,10,17,82,80,['familia','normal']),
(51,'Arroz','mercearia',4,15,24,88,86,['familia','economico']),
(52,'Feijão','mercearia',4,6,10,84,82,['familia','economico']),
(53,'Açúcar','mercearia',4,3,6,70,66,['familia','economico']),
(54,'Óleo de soja','mercearia',4,5,9,72,68,['familia','economico']),
(26,'Macarrão italiano','massas',4,4,8,65,64,['familia','normal']),
(43,'Farinha de trigo','mercearia',4,3,6,60,56,['familia','economico']),
(16,'Chá relaxante','mercearia',4,5,10,38,40,['premium','normal']),
(15,'Café especial','mercearia',4,16,28,48,52,['premium','normal']),
(17,'Pizza congelada','congelados',5,14,25,60,64,['familia','impulsivo']),
(20,'Batata frita','congelados',5,9,16,71,68,['familia','impulsivo']),
(18,'Pastel congelado','congelados',5,10,18,47,50,['familia','normal']),
(40,'Refeição pronta','congelados',5,12,22,64,62,['impulsivo','normal']),
(10,'Croissant','padaria',5,7,14,40,46,['premium','impulsivo']),
(28,'Presunto defumado','frios',5,12,22,44,48,['familia','normal']),
(29,'Cesta orgânica','organicos',5,28,48,36,40,['premium']),
(24,'Chocolate premium','chocolates',5,13,25,30,38,['premium','impulsivo']),
(35,'Detergente','limpeza',6,3,6,73,66,['familia','economico']),
(59,'Sabão em pó','limpeza',6,12,21,70,64,['familia','normal']),
(58,'Papel higiênico','higiene',6,10,18,86,80,['familia','economico']),
(34,'Shampoo','higiene',6,10,19,59,58,['normal','premium']),
(37,'Fralda','bebes',6,30,52,45,50,['familia']),
(36,'Ração premium','pets',6,26,46,39,44,['familia','premium']),
(38,'Pilha portátil','eletronicos',6,9,18,31,36,['impulsivo','normal']),
(39,'Caderno','papelaria',6,5,11,40,40,['familia']),
(19,'Lasanha premium','congelados',6,22,40,37,40,['premium','familia']),
(30,'Granola premium','mercearia',6,16,30,28,34,['premium']),
(41,'Panetone','sazonais',6,20,38,34,40,['familia','premium']),
(32,'Trufa gourmet','chocolates',7,28,55,18,30,['premium']),
(31,'Vinho importado','alcoolicos',7,45,85,24,34,['premium']),
(61,'Picolé','sorvetes',8,3,8,78,72,['impulsivo','familia']),
(57,'Frango','carnes',8,14,26,84,80,['familia','economico']),
(27,'Carne nobre','carnes',8,55,95,40,46,['premium','familia']),
(44,'Peixe fresco','peixes',9,22,40,38,42,['premium','familia']),
(45,'Camarão fresco','peixes',9,45,80,24,32,['premium']),
(33,'Champanhe reserva','alcoolicos',10,120,240,8,20,['premium']),
]
# crafted: id,name,category,tier,demand,pop,preferred
P=[
(101,'Baguete rústica','padaria',7,68,70,['familia','premium']),
(102,'Croissant premium','padaria',7,52,56,['premium','impulsivo']),
(103,'Bolo de vitrine','doces',7,34,46,['premium','familia']),
(104,'Queijo minas artesanal','queijos',8,60,62,['familia','normal']),
(105,'Brie maturado','queijos',8,40,44,['premium']),
(107,'Hambúrguer artesanal','carnes',8,62,66,['familia','impulsivo']),
(113,'Suco gelado da casa','bebidas',8,67,66,['impulsivo','familia']),
(114,'Chá gelado artesanal','bebidas',8,48,50,['premium','impulsivo']),
(106,'Tábua de queijos','queijos',9,22,34,['premium']),
(108,'Corte dry-aged','carnes',9,24,34,['premium']),
(109,'Kit churrasco premium','carnes',9,30,40,['familia','premium']),
(110,'Filé de peixe fresco','peixes',9,54,52,['familia','premium']),
(111,'Sushi especial','peixes',9,40,48,['premium','impulsivo']),
(115,'Vitamina cremosa','bebidas',9,41,48,['familia','premium']),
(116,'Sorvete de creme','sorvetes',9,69,70,['familia','impulsivo']),
(117,'Sundae de chocolate','sorvetes',9,44,52,['impulsivo','premium']),
(119,'Vinho tinto da casa','alcoolicos',9,40,46,['premium','normal']),
(112,'Barco de frutos do mar','peixes',10,16,30,['premium']),
(118,'Pote de sorvete família','sorvetes',10,40,48,['familia']),
(120,'Sangria da casa','alcoolicos',10,36,44,['premium','impulsivo']),
(121,'Kit harmonização','gourmet',10,20,32,['premium']),
]
# out -> (ingredients, outQty, minutes)
R={
101:([(43,2),(7,1)],4,1),
102:([(43,2),(7,1),(5,1)],3,2),
103:([(43,2),(5,2),(50,1),(24,1)],2,4),
104:([(5,4)],2,3),
105:([(5,3),(6,1)],2,6),
106:([(105,1),(104,2),(31,1)],2,12),
107:([(27,1),(1,2)],4,3),
108:([(27,3)],2,8),
109:([(27,2),(57,2),(60,2)],3,15),
110:([(44,2)],4,4),
111:([(44,2),(51,1)],3,8),
112:([(44,3),(45,2),(51,1)],3,18),
113:([(49,2),(46,2),(21,1)],3,2),
114:([(16,1),(53,1),(21,2)],3,4),
115:([(5,2),(8,1),(46,2)],3,6),
116:([(5,2),(8,1),(53,1)],3,5),
117:([(116,2),(24,1)],2,8),
118:([(116,3),(49,1)],1,14),
119:([(62,4),(53,1)],2,6),
120:([(119,2),(49,1),(14,1)],3,10),
121:([(31,1),(106,1),(32,1)],2,20),
}
SECTOR={101:'padaria',102:'padaria',103:'padaria',104:'queijaria',105:'queijaria',106:'queijaria',107:'acougue',108:'acougue',109:'acougue',110:'peixaria',111:'peixaria',112:'peixaria',113:'bebidas',114:'bebidas',115:'bebidas',116:'sorvetes',117:'sorvetes',118:'sorvetes',119:'adega',120:'adega',121:'adega'}
SLUG={101:'baguete-rustica',102:'croissant-premium',103:'bolo-de-vitrine',104:'queijo-minas',105:'brie-maturado',106:'tabua-de-queijos',107:'hamburguer-artesanal',108:'corte-dry-aged',109:'kit-churrasco',110:'file-de-peixe',111:'sushi-especial',112:'barco-de-frutos-do-mar',113:'suco-gelado',114:'cha-gelado',115:'vitamina-cremosa',116:'sorvete-creme',117:'sundae-chocolate',118:'pote-sorvete-familia',119:'vinho-da-casa',120:'sangria-da-casa',121:'kit-harmonizacao'}
CRAFT_MARKUP=1.4
# Coins per real: the list above is in reais; the game sells at about twice that.
PRICE_SCALE=2
price={}
for s in S: price[s[0]]=(s[4]*PRICE_SCALE,s[5]*PRICE_SCALE)
def craft(pid):
    if pid in price: return price[pid]
    ing,q,_=R[pid]
    buy=sum(craft(i)[0]*n for i,n in ing); sell=sum(craft(i)[1]*n for i,n in ing)
    price[pid]=(math.ceil(buy/q), round(sell*CRAFT_MARKUP/q))
    return price[pid]
for p in P: craft(p[0])
def rarity(sell):
    return 'comum' if sell<=10 else 'incomum' if sell<=25 else 'raro' if sell<=60 else 'epico' if sell<=130 else 'lendario'
def xp(sell): return max(1,round(0.5+0.5*math.sqrt(sell)))
rows=[]
def lvl(tier,k):
    base=BASE[tier]; top=BASE[tier+1]-1 if tier+1<len(BASE) else base+4
    return min(max(base,top), base+k//4)
count={}
for s in S:
    pid,name,cat,tier,buy,sell,dem,pop,pref=s
    buy,sell=price[pid]
    k=count.get(tier,0); count[tier]=k+1
    rows.append(dict(id=pid,name=name,category=cat,tier=tier,buy=buy,sell=sell,demand=dem,popularity=pop,pref=pref,acq='supplier',level=lvl(tier,k)))
for p in P:
    pid,name,cat,tier,dem,pop,pref=p
    k=count.get(tier,0); count[tier]=k+1
    b,s=price[pid]
    rows.append(dict(id=pid,name=name,category=cat,tier=tier,buy=b,sell=s,demand=dem,popularity=pop,pref=pref,acq='production',level=lvl(tier,k)))
if '--json' in sys.argv:
    print(json.dumps(dict(rows=rows,R={k:v for k,v in R.items()},SECTOR=SECTOR),ensure_ascii=False)); sys.exit()
lv={r['id']:r['level'] for r in rows}
rec=[]
for pid,(ing,q,mins) in R.items():
    ings=', '.join('{ productId: %d, quantity: %d }'%(i,n) for i,n in ing)
    rec.append('\t{ id: "%s", sectorId: "%s", outputProductId: %d, outputQuantity: %d, durationMs: %d * MINUTE, requiredLevel: %d, ingredients: [%s] },'%(SLUG[pid],SECTOR[pid],pid,q,mins,lv[pid],ings))
out=[]
for r in rows:
    out.append('\t{ id: %d, name: "%s", category: "%s", unlockEra: "%s", unlockLevel: %d, purchasePrice: %d, sellingPrice: %d, rarity: "%s", demand: %d, popularity: %d, preferredCustomers: %s, xpPerSale: %d%s },' % (
        r['id'],r['name'],r['category'],E[r['tier']],r['level'],r['buy'],r['sell'],rarity(r['sell']/PRICE_SCALE),r['demand'],r['popularity'],json.dumps(r['pref']),xp(r['sell']), ', acquisition: "production"' if r['acq']=='production' else ''))
if '--write' in sys.argv:
    import os
    here=os.path.dirname(os.path.abspath(__file__)); repo=os.path.dirname(os.path.dirname(here))
    t=open(os.path.join(here,'market-products.tpl')).read().replace('/*SEEDS*/','\n'.join(out))
    open(os.path.join(repo,'src/data/market-products.ts'),'w').write(t)
    t=open(os.path.join(here,'production-sectors.tpl')).read().replace('/*RECIPES*/','\n'.join(rec))
    for i,b in enumerate(BASE): t=t.replace('__L%d__'%i,str(b))
    open(os.path.join(repo,'src/data/production-sectors.ts'),'w').write(t)
    print('written; base levels',BASE)
else:
    print('\n'.join(out)); print('\n'.join(rec))
