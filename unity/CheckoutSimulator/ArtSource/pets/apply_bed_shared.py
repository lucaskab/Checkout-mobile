"""In-place edits to shared files (other sessions edit them too): the pet beds in the decor catalogue and the
translations of the new strings. Run on the Mac checkout root: python3 apply_shared.py <repo>"""
import sys, os

repo = sys.argv[1]


def edit(path, old, new):
    p = os.path.join(repo, path); s = open(p, encoding="utf-8").read()
    if new.strip() in s:
        print("already", path); return
    assert s.count(old) == 1, (path, s.count(old))
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok", path)


BEDS = '''	// Caramelo's beds (08/11/2026): placed anywhere inside or outside; he sleeps on the nearest one when the market
	// closes (Unity CheckoutPets). Fabric colours: the bedStyle cosmetics on the Caramelo page (src/data/pet.ts).
	{ id: "pet-bed-round", name: "Caminha redonda", description: "Almofadão fofinho para o Caramelo. Coloque onde quiser, dentro ou fora: ele dorme nela quando o mercado fecha.", coinPrice: 800, requiredLevel: 1, zone: "both" },
	{ id: "pet-bed-basket", name: "Cesta de vime", description: "Cesta de vime com almofada e mantinha para o Caramelo cochilar.", coinPrice: 1_600, requiredLevel: 3, zone: "both" },
	{ id: "pet-bed-house", name: "Casinha de madeira", description: "Casinha com telhado e almofada na porta. Fica linda na calçada.", coinPrice: 3_200, requiredLevel: 6, zone: "both" },
	{ id: "pet-bed-sofa", name: "Sofazinho retrô", description: "Sofá de botões com pés de madeira, só para ele.", coinPrice: 4_800, requiredLevel: 10, zone: "both" },
	{ id: "pet-bed-royal", name: "Cama real", description: "Cama com dossel e moldura dourada para o cachorro mais chique do bairro.", diamondPrice: 30, requiredLevel: 12, zone: "both" },
'''
edit("src/data/interior-decor.ts",
     '''	// Outside the market: the plaza and footways of the city block.''',
     BEDS + '''	// Outside the market: the plaza and footways of the city block.''')

T = {
    "Caminha redonda": ("Round dog bed", "Cama redonda", "Panier rond", "Rundes Hundebett"),
    "Almofadão fofinho para o Caramelo. Coloque onde quiser, dentro ou fora: ele dorme nela quando o mercado fecha.": (
        "A big fluffy cushion for Caramelo. Put it anywhere, inside or outside: he sleeps on it when the market closes.",
        "Un cojín grande y mullido para Caramelo. Ponlo donde quieras, dentro o fuera: duerme en él cuando cierra el mercado.",
        "Un gros coussin moelleux pour Caramelo. Place-le où tu veux, dedans ou dehors : il y dort quand le magasin ferme.",
        "Ein großes, flauschiges Kissen für Caramelo. Stell es auf, wo du willst, drinnen oder draußen: Er schläft darauf, wenn der Markt schließt."),
    "Cesta de vime": ("Wicker basket bed", "Cesta de mimbre", "Panier en osier", "Weidenkorb"),
    "Cesta de vime com almofada e mantinha para o Caramelo cochilar.": (
        "A wicker basket with a cushion and a blanket for Caramelo's naps.",
        "Cesta de mimbre con cojín y mantita para la siesta de Caramelo.",
        "Un panier en osier avec coussin et petite couverture pour les siestes de Caramelo.",
        "Ein Weidenkorb mit Kissen und Decke für Caramelos Nickerchen."),
    "Casinha de madeira": ("Wooden dog house", "Caseta de madera", "Niche en bois", "Holzhundehütte"),
    "Casinha com telhado e almofada na porta. Fica linda na calçada.": (
        "A little house with a roof and a cushion at the door. Looks lovely on the sidewalk.",
        "Una casita con tejado y cojín en la puerta. Queda preciosa en la acera.",
        "Une petite niche avec toit et coussin devant la porte. Superbe sur le trottoir.",
        "Ein Häuschen mit Dach und Kissen vor der Tür. Sieht auf dem Gehweg toll aus."),
    "Sofazinho retrô": ("Retro dog sofa", "Sofá retro", "Petit canapé rétro", "Retro-Hundesofa"),
    "Sofá de botões com pés de madeira, só para ele.": (
        "A buttoned sofa with wooden legs, just for him.",
        "Un sofá capitoné con patas de madera, solo para él.",
        "Un canapé capitonné aux pieds en bois, rien que pour lui.",
        "Ein Knopfsofa mit Holzbeinen, nur für ihn."),
    "Cama real": ("Royal bed", "Cama real", "Lit royal", "Königsbett"),
    "Cama com dossel e moldura dourada para o cachorro mais chique do bairro.": (
        "A canopy bed with a golden frame for the fanciest dog in the neighbourhood.",
        "Cama con dosel y marco dorado para el perro más elegante del barrio.",
        "Un lit à baldaquin au cadre doré pour le chien le plus chic du quartier.",
        "Ein Himmelbett mit goldenem Rahmen für den schicksten Hund im Viertel."),
    "Tecido azul-marinho": ("Navy fabric", "Tela azul marino", "Tissu bleu marine", "Marineblauer Stoff"),
    "As caminhas nas cores do mercado, com debrum creme.": (
        "The beds in the market's colours, with cream piping.",
        "Las camas con los colores del mercado, con ribete crema.",
        "Les paniers aux couleurs du magasin, avec passepoil crème.",
        "Die Betten in den Farben des Markts, mit cremefarbener Paspel."),
    "Tecido verde-água": ("Teal fabric", "Tela verde agua", "Tissu vert d'eau", "Türkiser Stoff"),
    "Verde-água fresquinho em todas as caminhas.": (
        "Fresh teal on every bed.", "Verde agua fresquito en todas las camas.",
        "Un vert d'eau tout frais sur tous les paniers.", "Frisches Türkis auf allen Betten."),
    "Tecido caramelo": ("Caramel fabric", "Tela caramelo", "Tissu caramel", "Karamellfarbener Stoff"),
    "Combina com o pelo dele.": ("Matches his fur.", "Combina con su pelaje.", "Assorti à son pelage.", "Passt zu seinem Fell."),
    "Tecido rosê": ("Rosé fabric", "Tela rosa palo", "Tissu rosé", "Altrosa Stoff"),
    "Rosa antigo, delicado e chique.": ("Dusty pink, soft and stylish.", "Rosa palo, delicado y elegante.",
                                         "Vieux rose, doux et chic.", "Altrosa, zart und schick."),
    "TECIDO DAS CAMINHAS": ("BED FABRIC", "TELA DE LAS CAMAS", "TISSU DES PANIERS", "BETTSTOFF"),
    "CAMINHA": ("BED", "CAMA", "PANIER", "BETT"),
    "No mercado": ("In the market", "En el mercado", "Au magasin", "Im Markt"),
    "Mudar de lugar": ("Move it", "Cambiar de lugar", "Déplacer", "Umstellen"),
}
for i, loc in enumerate(("en", "es", "fr", "de")):
    p = f"src/i18n/locales/{loc}.ts"
    s = open(os.path.join(repo, p), encoding="utf-8").read()
    lines = []
    for k, v in T.items():
        key = '\t"%s": ' % k.replace('"', '\\"')
        if key in s:
            continue
        lines.append(key + '"%s",' % v[i].replace('"', '\\"'))
    if not lines:
        print("already", p); continue
    block = "\t// Caramelo's beds (08/11/2026).\n" + "\n".join(lines) + "\n"
    end = "};\n\nexport default catalog;"
    assert s.count(end) == 1, p
    open(os.path.join(repo, p), "w", encoding="utf-8").write(s.replace(end, block + end))
    print("ok", p, len(lines))
