from thefuzz import process, fuzz

uniquie_brands = {'100BON', '12 PARFUMEURS FRANCAIS', "SUPREME 24K", '27 87', '4711 WUNDERWASSER', 'ABERCROMBIE & FITCH', 'ACQUA DI PARMA', 'ACQUA DI STRESA', 'ADIDAS', 'AESOP', 'AFNAN', 'AGENT PROVOCATEUR', 'AJ ARABIA', 'AJ ARABIA WIDIAN', 'AJMAL', 'AKRO', 'AL HARAMAIN', 'ALEX SIMONE', 'ALEXANDER MCQUEEN', 'ALEXANDRE J.', 'AMOUAGE', 'AMOUROUD', 'ANDREE PUTMAN', 'ANGEL SCHLESSER', 'ANNA SUI', 'ANNE FONTAINE', 'ANTONIO BANDERAS', 'ANTONIO MARETTI', 'AQUALIS', 'ARABESQUE', 'ARABIAN OUD', 'ARAMIS', 'ARCADIA', 'ARMAF', 'ARMAND BASI', 'ARNO SOREL', 'ATELIER COLOGNE', 'ATELIER DES ORS', 'ATELIER MATERI', 'ATKINSONS', 'ATTAR', 'ATTAR AL HAS', 'ATTAR COLLECTION', 'AZZARO', 'BALDESSARINI', 'BALENCIAGA', 'BALMAIN', 'BANANA REPUBLIC', 'BDK', 'BEL REBEL', 'BEN SHERMAN', 'BEVERLY HILLS', 'BILL BLASS', 'BLEND OUD', 'BLENDS', 'BLOOD CONCEPT', 'BLUMARINE', 'BOADICEA THE VICTORIOUS', 'BOGART', 'BOIS 1920', 'BOTTEGA VENETA', 'BOUCHERON', 'BOUGE', 'BRIONI', 'BRITNEY SPEARS', 'BRUNO BANANI', 'BUGATTI', 'BURBERRY', 'BVLGARI', 'BYBOZO', 'BYREDO', 'CACHAREL', 'CAFE-CAFE', 'CALVIN KLEIN', 'CARINE ROITFELD', 'CARLA FRACCI', 'CARNER BARCELONA', 'CAROLINA HERRERA', 'CARON', 'CARTIER', 'CASTELBAJAC', 'CERRUTI', 'CHANEL', 'CHANEL КОСМЕТИКА', 'CHANTAL', 'CHANTAL THOMASS', 'CHAUMET', 'CHEVIGNON', 'CHLOE', 'CHOPARD', 'CHRIS COLLINS', 'CHRISTIAN  LOUBOUTIN', 'CHRISTIAN DIOR', 'CHRISTIAN LACROIX', 'CHRISTINA AGOILERA', 'CHRISTINA AGUILERA', 'CLARINS КОСМЕТИКА', 'CLINIQUE', 'CLINIQUE HAPPY', 'CLIVE CHRISTIAN', 'COACH', 'COMME DES GARCONS', 'COMME DES GARSONS', 'COMPTOIR SUD PACIFIQUE', 'COSTUME NATIONAL', 'COTY', 'CREED', 'CRISTIANO RONALDO', 'DAVID BECKHAM', 'DAVIDOFF', 'DESERT OUD', 'DIANA VON FURSTENBERG', 'DIESEL', 'DIOR КОСМЕТИКА', 'DIPTYQUE', 'DOLCE & GABBANA', 'DONNA KARAN', 'DORIN', 'DSQUARED2', 'DUNHILL', 'DUPONT', 'DUSITA', 'ED HARDY', 'EIGHT & BOB', 'EISENBERG', 'ELECTIMUSS', 'ELIE SAAB', 'ELIE SAAB LE PARFUM', 'ELIZABETH ARDEN', 'ELIZABETH TAYLOR', 'ELLA K PARFUMS', 'ELLEN TRACY', 'EMANUEL UNGARO', 'EMILIO PUCCI', 'ERMENEGILDO ZEGNA', 'ESCADA', 'ESCENTRIC MOLECULES', 'ESSENTIAL PARFUMS', 'ESTEE LAUDER', 'ETAT LIBRE D`ORANGE', 'EUTOPIE', 'EVAFLOR', 'EX NIHILO', 'FACONNABLE', 'FENDI', 'FERAUD', 'FERRAGAMO SALVATORE', 'FERRE', 'FLORAIKU', 'FLORIS', 'FLY FALCON', 'FRANC OLIVIER', 'FRANCESCA BIANCHI', 'FRANCIS KURKDJIAN', 'FRANCK BOCLET', 'FRANCK MULLER', 'FRANCK OLIVIER', 'FRANK OLIVER', 'FRAPIN', 'FREDERIC MALLE', 'FUGAZZI', 'FURLA', 'GENYUM', 'GEOFFREY BEENE', 'GEORGES RECH', 'GHOST', 'GIAN MARCO VENTURI', 'GIANFRANCO FERRE', 'GIARDINO BENESSERE', 'GIORGIO ARMANI', 'GIVENCHY', 'GOLDFIELD & BANKS', 'GRES', 'GRITTI', 'GUCCI', 'GUERLAIN', 'GUESS', 'GUY LAROCHE', 'HACKETT LONDON', 'HANAE MORI', 'HAUTE FRAGRANCE COMPANY', 'HAYARI', 'HEADSPACE', 'HERMES', 'HERMETICA', 'HFC', 'HISTORIE DE PARFUMS', 'HOLLISTER CO.', 'HOMO ELEGANS', 'HUGO BOSS', 'ICEBERG', 'IL PROFVMO', 'ILLUMINUM', 'INITIO', 'ISABEY', 'ISSEY MIYAKE', 'J.DEL POZO', 'JACOMO', 'JACQUES BOGART', 'JACQUES FATH', 'JACQUES ZOLTY', 'JAMES BOND 007', 'JEAN COUTURIER', 'JEAN PATOU', 'JEAN PAUL GAULTIER', 'JENNIFER LOPEZ', 'JIL SANDER', 'JIMMY CHOO', 'JLS', 'JO MALONE', 'JOHN RICHMOND', 'JOHN VARVATOS', 'JOOP!', 'JOSE EISENBERG', 'JUDITH LEIBER', 'JUICY COUTURE', 'JULIETTE HAS A GUN', 'JUSBOX', 'J`AI OSE', 'KAJAL', 'KARL LAGERFELD', 'KATE SPADE', 'KEIKO MECHERI', 'KENNETH COLE', 'KENZO', 'KILIAN', 'KITON', 'KORLOFF PARIS', 'KRIZIA', "L'ARTISAN PARFUMEUR", 'LA PERLA', 'LACOSTE', 'LADY GAGA', 'LALIQUE', 'LANCOME', 'LANVIN', 'LAPIDUS', 'LATTAFA', 'LAURA BIAGIOTTI', 'LAURENT MAZZONE', 'LE LABO', 'LE PARFUMEUR', 'LES CONTES', 'LES COPAINS', 'LIQUIDES IMAGINAIRES', 'LM PARFUM', 'LOEWE', 'LOLITA LEMPICKA', 'LORIS AZZARO', 'LOUIS VUITTON', 'LPDO', 'LULU CASTAGNETTE', 'LUXVISAGE', 'M.INT', 'M.MICALLEF', 'MAISON CRIVELLI', 'MAISON FRANCIS KURKDJIAN', 'MAISON INCENS', 'MAISON MARGIELA', 'MAISON MARTIN MARGIELA', 'MAISSA', 'MANCERA', 'MANDARINA DUCK', 'MARC ANTOINE BARROIS', 'MARC JACOBS', 'MARC JOSEPH', 'MARINA DE BOURBON', 'MASAKI MATSUSHIMA', 'MAUBOUSSIN', 'MAX MARA', 'MAX PHILIP', 'MAXFACTOR', 'MAYBELLINE', 'MAZZOLARI', 'MCM', 'MEMO', 'MEXX', 'MICHAEL KORS', 'MIHAN AROMATICS', 'MILLER ET BERTAUX', 'MIN NEW YORK', 'MISSONI', 'MIU MIU', 'MIZENSIR', 'MOLECULE', 'MOLINARD', 'MONCLER', 'MONOTHEME', 'MONT  BLANC', 'MONT BLANC', 'MONTALE', 'MOOD', 'MORESQUE', 'MOSCHINO', 'MUGLER', 'NAN', 'NAOMI CAMPBELL', 'NARCISO RODRIGUEZ', 'NASOMATTO', 'NICOLE FARHI', 'NINA RICCI', 'NOBILE 1942', 'NORAN PERFUMES', 'NOUVEAU PARIS', 'NVDO', 'ODEJO', 'OJAR', 'OLFACTIVE STUDIO', 'ONCE', 'ONNO', 'ORENS', 'ORLANE', 'ORLOV', 'ORMONDE JAYNE', 'ORTO PARISI', 'OSCAR DE LA RENTA', 'PACO RABANNE', 'PALOMA PICASSO', 'PARADIS DES SENS', 'PARFUMS  DE  MARLY', 'PARFUMS DE MARLY', 'PARFUMS DUSITA', 'PARIS HILTON', 'PARLE MOI DE PARFUM', 'PENHALIGON', "PENHALIGON'S", 'PEPE JEANS', 'PERROY', 'PHARRELL  WILLIAMS', 'PHILIPP PLEIN', 'POLICE', 'PRADA', 'PROFUMUM ROMA', 'PRUDENCE', 'PUPA', 'PUREDISTANCE', 'RALPH LAUREN', 'RANCE 1795', 'RASASI', 'REBATCHI', 'REMY LATOUR', 'REPLAY', 'REVILLON', 'ROBERTO CAVALL', 'ROBERTO CAVALLI', 'ROCHAS', 'ROJA DOVE', 'ROMEO GIGILI', 'ROOM 1015', 'ROSENDO MATEU', 'ROYAL CROWN', 'RUDROSS', 'S.T. DUPONT', 'SALVADOR DALI', 'SALVATORE FERRAGAMO', 'SANDALIA', 'SARA JESSICA PARKER', 'SARAH JESSICA PARKER', 'SAWALEF', 'SERGE  LUTENS', 'SERGE LUTENS', 'SERGIO NERO', 'SERGIO TACCHINI', 'SHAIK', 'SHAKIRA', 'SHISEIDO', 'SIMONE COSAC', 'SISLEY', 'SLAVA ZAITSEV', 'SLY JOHN`S LAB', 'SONIA RYKIEL', 'SOOUD', 'SOSPIRO PERFUMES', 'STEFANO RICCI', 'STELLA MC CARTNEY', 'STELLA MCCARTNEY', 'STEPHANIE DE BRUIJ', 'STRANGELOVE', 'SWEDOFT', 'TACCHINI', 'TEATRO FRAGRANZE', 'TED LAPIDUS', 'TERESA HELBIG', 'THAMEEN LONDON', 'THE DIFFERENT COMPANY', 'THE FRAGRANCE KITCHEN', 'THE HOUSE OF OUD', 'THE MERCHANT OF VENICE', 'THOMAS KOSMALA', 'TIFFANY', 'TIZIANA TERENZI', 'TOM FORD', 'TOMMY HILFIGER', 'TORRENTE', 'TREE OF LIFE', 'TRUSSARDI', 'ULRIC DE VARENS', 'V CANTO', 'VALENTINO', 'VAN CLEEF & ARPELS', 'VAN GILS', 'VANDERBILT', 'VERA WANG', 'VERONIQUE GABA', 'VERSACE', 'VERTUS', "VICTORIA'S SECRET", 'VIKTOR & ROLF', 'VILHELM PARFUMERIE', 'WHAT WE DO IS SECRET (A LAB ON FIRE)', 'WILGERMAIN', "WOMEN'SECRET", 'XERJOFF', 'YOHJI YAMAMOTO', 'YVES ROCHER', 'YVES SAINT LAURENT', 'ZADIG & VOLTAIRE', 'ZARKOPERFUME', 'ZIELINSKI & ROZEN', 'ZIMAYA', 'ZLATAN IBRAHIMOVIC', 'НОВАЯ ЗАРЯ', 'ОСТАЛЬНОЕ', 'ПАКЕТЫ'}


brand_synonyms = {
    "100BON": ["100bon"],
    "12 PARFUMEURS FRANCAIS": ["12 parfumeurs francais",'12 parfumeurs'],
    "27 87": ["27 87", "2787 perfumes"],
    "4711 WUNDERWASSER": ["4711 wunderwasser"],
    "DUNHILL": ["a.dunhill"],
    "ABERCROMBIE & FITCH": ["abercrombie & fitch", "abercrombie&fitch"],
    "ACQUA DI PARMA": ["acqua di parma"],
    "ACQUA DI STRESA": ["acqua di stresa"],
    "ACQUA DI PARISIS": ["acqua di parisis"],
    "ADIDAS": ["adidas"],
    "AESOP": ["aesop"],
    "AFNAN": ["afnan"],
    "AGENT PROVOCATEUR": ["agent provocateur"],
    "AJMAL": ["ajmal"],
    "AKRO": ["akro"],
    "ALEXANDRE J.": [
        "alexandre j.",
        "alexandre.j the collector",
        "alexandre j",
        "alexandre.j",
    ],
    "AMOUAGE": ["amouage"],
    "ANGEL SCHLESSER": ["angel schlesser"],
    "ANTONIO BANDERAS": ["antonio banderas"],
    "ARABESQUE": ["arabesque"],
    "ARAMIS": ["aramis"],
    "ARMAF": ["armaf"],
    "ARMAND BASI": ["armand basi"],
    "ARMANI": ["armani"],
    "ATKINSONS": ["atkinsons"],
    "ATELIER COLOGNE": ["atelier cologne"],
    "ATELIER MATERI": ["atelier materi"],
    "AZZARO": ["azzaro"],
    "BALENCIAGA": ["balenciaga"],
    "BANANA REPUBLIC": ["banana republic"],
    "BDK": ["bdk"],
    "BLEND OUD": ["blend oud"],
    "BOIS 1920": ["bois 1920"],
    "BVLGARI": ["bvlgari"],
    "BURBERRY": ["burberry", "burberrys"],
    "BYREDO": ["byredo"],
    "CALVIN KLEIN": ["calvin klein", "ck", "c.k."],
    "CARNER BARCELONA": ["carner barcelona"],
    "CAROLINA HERRERA": ["carolina herrera", "c.h."],
    "CARTIER": ["cartier"],
    "CERRUTI": ["cerruti"],
    "CHANEL": ["chanel"],
    "CHLOE": ["chloe"],
    "CHRISTIAN DIOR": ["christian dior", "c.dior", "dior", "c. dior", "c.d.", "cd"],
    "CLIVE CHRISTIAN": ["clive christian"],
    "COACH": ["coach"],
    "COMME DES GARCONS": ["comme des garcons"],
    "CREED": ["creed"],
    "DAVIDOFF": ["davidoff"],
    "DIESEL": ["diesel"],
    "DIPTYQUE": ["diptyque"],
    "DOLCE & GABBANA": [
        "dolce & gabbana",
        "d&g",
        "dolce&gabbana",
        "dolce and gabbana",
        "dolce gabbana" "d & g",
        "D & G",
        "dolce gabbana",
        "dg"
    ],
    "DONNA KARAN": ["donna karan", "dkny", "d.karan", "DONNA KARAN DKNY"],
    "DSQUARED2": ["dsquared2"],
    "ELIZABETH ARDEN": ["elizabeth arden"],
    "ESCADA": ["escada"],
    "ESCENTRIC MOLECULES": ["escentric molecules"],
    "ESTEE LAUDER": ["estee lauder"],
    "EX NIHILO": ["ex nihilo"],
    "FENDI": ["fendi"],
    "FRANCK BOCLET": ["franck boclet"],
    "FREDERIC MALLE": ["frederic malle"],
    "GIORGIO ARMANI": [
        "giorgio armani",
        "g.armani",
        "armani",
        "g. armani",
        "GIORGIO AMANI",
    ],
    "GRITTI": ["dr. gritti"],
    "GIAN MARCO VENTURI": ["gian marco venturi", "gmv"],
    "GIARDINO BENESSERE": ["GIARDINO BENESSERE (T.TERENZI)"],
    "GOLDFIELD & BANKS": ["goldfield & banks", 'goldfield banks'],
    "GUCCI": ["gucci"],
    "GUERLAIN": ["guerlain"],
    "HUGO BOSS": ["hugo boss", "boss", "hb boss", "hb", "boss hugo"],
    "INITIO": ["initio"],
    "ISSEY MIYAKE": ["issey miyake"],
    "JEAN PAUL GAULTIER": ["jean paul gaultier"],
    "JIMMY CHOO": ["jimmy choo"],
    "JO MALONE": ["jo malone"],
    "JENNIFER LOPEZ": [
        "jennifer lopez",
        "j.lo",
        "jlo",
        "j. lopez",
        "j.lopez",
        "jennifer lopes",
    ],
    "KENZO": ["kenzo"],
    "LALIQUE": ["lalique"],
    "LANCOME": ["lancome"],
    "LANVIN": ["lanvin"],
    "MONTALE": ["montale"],
    "MANCERA": ["mancera"],
    "MEMO": ["memo"],
    "MOSCHINO": ["moschino"],
    "NAOMI CAMPBELL": ["naomi campbell", "n.campbell"],
    "NARCISO RODRIGUEZ": ["narciso rodriguez"],
    "NINA RICCI": [
        "nina ricci",
    ],
    "PACO RABANNE": ["paco rabbanne", "p.r.", "paco rabbane"],
    "PRADA": ["prada"],
    "ROBERTO CAVALLI": ["roberto cavalli"],
    "SALVADOR DALI": ["salvador dali", "s.dali"],
    "SERGE LUTENS": ["serge lutens"],
    "SUPREME 24K": ["supreme 24k", '24 K SUPREME', '24k supreme', "supreme 24 k"],
    "MUGLER": ["thierry mugler", "therry mugler", "t.mugler", "mugler", "t. mugler"],
    "TIZIANA TERENZI": ["tiziana terenzi"],
    "TOM FORD": ["tom ford"],
    "VAN CLEEF & ARPELS": ["van cleef & arpels", "van cleef", "vca"],
    "VICTORIA'S SECRET": ["victorias secret"],
    "VIKTOR & ROLF": [
        "viktor & rolf",
        "viktor&rolf",
        "viktor and rolf",
        "v&r",
        "v&r flowerbomb",
    ],
    "VERSACE": ["versace"],
    "VILHELM PARFUMERIE": ["vilhelm parfumerie", "vilhelm"],
    "XERJOFF": ["xerjoff", "xj"],
    "YVES SAINT LAURENT": [
        "yves saint laurent",
        "ysl",
        "y.saint laurent",
        "y.saint-laurent",
    ],
    "YOHJI YAMAMOTO": ["yohji yamamoto", "yohjii yamamoto", "yohji"],
    "ZADIG & VOLTAIRE": ["zadig & voltaire", "zadig"],
    "ZARKOPERFUME": ["zarkoperfume"],
    "ZLATAN IBRAHIMOVIC": ["zlatan ibrahimovic", "zlatan", "ibrahimovic"],
}


def get_standard_brand_fuzzy(brand, threshold=50):
    # Проверяем точное соответствие
    for standard, synonyms in brand_synonyms.items():
        if brand.lower() in [s.lower() for s in synonyms]:
            return standard
    # Ищем близкое совпадение
    match = process.extractOne(brand, uniquie_brands, scorer=fuzz.ratio)
    if match and match[1] >= threshold:
        return match[0]
    return brand.upper()


def get_brand_aliases(brand) -> tuple[str]:
    if brand_synonyms.get(brand.upper()):
        return tuple(brand_synonyms.get(brand.upper()))
    else:
        return tuple()


# функция которая возвращает множество все возможных алиасов бренда и сам бренд, включая уникальные бренды из uniquie_brands
def get_all_brand_aliases() -> set[str]:
    all_aliases = [brand.lower() for brand in uniquie_brands]
    for brand in all_aliases.copy():
        if brand_synonyms.get(brand.upper()):
            all_aliases.extend(brand_synonyms.get(brand.upper()))
    return set(all_aliases)


# проверяем что строка начинается с бренда или его алиаса и возвращаем бренд
def get_brand_from_name(string: str) -> str:
    # print(string)
    for brand in get_all_brand_aliases():
        if string.lower().startswith(brand):
            brand_name = get_standard_brand_fuzzy(brand)
            return brand_name
    return "NAN"
