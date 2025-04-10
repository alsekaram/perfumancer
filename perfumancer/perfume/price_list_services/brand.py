from thefuzz import process, fuzz

uniquie_brands = {"10 avenue", '100BON', '12 PARFUMEURS FRANCAIS', "SUPREME 24K", '27 87', '4711 WUNDERWASSER', 'ABERCROMBIE & FITCH', 'ACQUA DI PARMA', 'ACQUA DI STRESA', 'ADIDAS', 'AESOP', 'AFNAN', 'AGENT PROVOCATEUR', 'AJ ARABIA', 'AJ ARABIA WIDIAN', 'AJMAL', 'AKRO', 'AL HARAMAIN', 'ALEX SIMONE', 'ALEXANDER MCQUEEN', 'ALEXANDRE J.', 'AMOUAGE', 'AMOUROUD', 'ANDREE PUTMAN', 'ANGEL SCHLESSER', 'ANNA SUI', 'ANNE FONTAINE', 'ANTONIO BANDERAS', 'ANTONIO MARETTI', 'AQUALIS', 'ARABESQUE', 'ARABIAN OUD', 'ARAMIS', 'ARCADIA', 'ARMAND BASI', "ARMANI", 'ARNO SOREL', 'ATELIER COLOGNE', 'ATELIER DES ORS', 'ATELIER MATERI', 'ATKINSONS', 'ATTAR', 'ATTAR AL HAS', 'ATTAR COLLECTION', 'AZZARO', 'BALDESSARINI', 'BALDININI', 'BALENCIAGA', 'BALMAIN', 'BANANA REPUBLIC', 'BDK', 'BEL REBEL', 'BEN SHERMAN', 'BEVERLY HILLS', 'BILL BLASS', 'BLACKGLAMA', 'BLEND OUD', 'BLENDS', 'BLOOD CONCEPT', 'BLUMARINE', 'BOADICEA THE VICTORIOUS', 'BOGART', 'BOIS 1920', 'BOTTEGA VENETA', 'BOUCHERON', 'BOUGE', 'BRIONI', 'BRITNEY SPEARS', 'BRUNO BANANI', 'BUGATTI', 'BURBERRY', 'BVLGARI', 'BYBOZO', 'BYREDO', 'CACHAREL', 'CAFE-CAFE', 'CALVIN KLEIN', 'CARINE ROITFELD', 'CARLA FRACCI', 'CARNER BARCELONA', 'CAROLINA HERRERA', 'CARON', 'CARTIER', 'CASTELBAJAC', 'CERRUTI', 'CHANEL', 'CHANEL КОСМЕТИКА', 'CHANTAL', 'CHANTAL THOMASS', 'CHAUMET', 'CHEVIGNON', 'CHLOE', 'CHOPARD', 'CHRIS COLLINS', 'CHRISTIAN LOUBOUTIN', 'CHRISTIAN DIOR', 'CHRISTIAN LACROIX', 'CHRISTINA AGOILERA', 'CHRISTINA AGUILERA', 'CLARINS КОСМЕТИКА', 'CLINIQUE', 'CLINIQUE HAPPY', 'CLIVE CHRISTIAN', 'COACH', 'COMME DES GARCONS', 'COMME DES GARSONS', 'COMPTOIR SUD PACIFIQUE', 'COSTUME NATIONAL', 'COTY', 'COSMOGONY', 'CREED', 'CRISTIANO RONALDO', 'DAVID BECKHAM', 'DAVIDOFF', 'DESERT OUD', 'DIANA VON FURSTENBERG', 'DIESEL', 'DIOR КОСМЕТИКА', 'DIPTYQUE', 'DOLCE & GABBANA', 'DONNA KARAN', 'DORIN', 'DSQUARED2', 'DUNHILL', 'DUPONT', 'DUSITA', 'ED HARDY', 'EIGHT & BOB', 'EISENBERG', 'ELECTIMUSS', 'ELIE SAAB', 'ELIE SAAB LE PARFUM', 'ELIZABETH ARDEN', 'ELIZABETH TAYLOR', 'ELLA K PARFUMS', 'ELLEN TRACY', 'EMANUEL UNGARO', 'EMILIO PUCCI', 'ERMENEGILDO ZEGNA', 'ESCADA', 'ESCENTRIC MOLECULES', 'ESSENTIAL PARFUMS', 'ESTEE LAUDER', 'ETAT LIBRE D`ORANGE', 'EUTOPIE', 'EVAFLOR', 'EX NIHILO', 'FACONNABLE', 'FENDI', 'FERAUD', 'FERRE', 'FLORAIKU', 'FLORIS', 'FLY FALCON', 'FRANC OLIVIER', 'FRANCESCA BIANCHI', 'FRANCIS KURKDJIAN', 'FRANCK BOCLET', 'FRANCK MULLER', 'FRANCK OLIVIER', 'FRANK OLIVER', 'FRAPIN', 'FREDERIC MALLE', 'FUGAZZI', 'FURLA', 'GENYUM', 'GEOFFREY BEENE', 'GEORGES RECH', 'GHOST', 'GIAN MARCO VENTURI', 'GIANFRANCO FERRE', 'GIARDINO BENESSERE', 'GIORGIO ARMANI', 'GIVENCHY', 'GOLDFIELD & BANKS', 'GRES', 'GRITTI', 'GUCCI', 'GUERLAIN', 'GUESS', 'GUY LAROCHE', 'HACKETT LONDON', 'HANAE MORI', 'HAUTE FRAGRANCE COMPANY', 'HAYARI', 'HEADSPACE', 'HERMES', 'HERMETICA', 'HFC', 'HISTORIE DE PARFUMS', 'HOLLISTER CO.', 'HOMO ELEGANS', 'HUGO BOSS', 'ICEBERG', 'IL PROFVMO', 'ILLUMINUM', 'INITIO', 'ISABEY', 'ISSEY MIYAKE', 'J.DEL POZO', 'JACOMO', 'JACQUES BOGART', 'JACQUES FATH', 'JACQUES ZOLTY', 'JAMES BOND 007', 'JEAN COUTURIER', 'JEAN PATOU', 'JEAN PAUL GAULTIER', 'JENNIFER LOPEZ', 'JIL SANDER', 'JIMMY CHOO', 'JLS', 'JO MALONE', 'JOHN RICHMOND', 'JOHN VARVATOS', 'JOOP!', 'JOSE EISENBERG', 'JUDITH LEIBER', 'JUICY COUTURE', 'JULIETTE HAS A GUN', 'JUSBOX', 'J`AI OSE', 'KAJAL', 'KARL LAGERFELD', 'KATE SPADE', 'KEIKO MECHERI', 'KENNETH COLE', 'KENZO', 'KILIAN', 'KITON', 'KORLOFF PARIS', 'KRIZIA', "L'ARTISAN PARFUMEUR", 'LA PERLA', 'LACOSTE', 'LADY GAGA', 'LALIQUE', 'LANCOME', 'LANVIN', 'LAPIDUS', 'LATTAFA', 'LAURA BIAGIOTTI', 'LAURENT MAZZONE', 'LE LABO', 'LE PARFUMEUR', 'LES CONTES', 'LES COPAINS', 'LIQUIDES IMAGINAIRES', 'LM PARFUM', 'LOEWE', 'LOLITA LEMPICKA', 'LORIS AZZARO', 'LOUIS VUITTON', 'LPDO', 'LULU CASTAGNETTE', 'LUXVISAGE', 'M.INT', 'MAISON MICALLEF', 'MAISON CRIVELLI', 'MAISON FRANCIS KURKDJIAN', 'MAISON INCENS', 'MAISON MARGIELA', 'MAISON MARTIN MARGIELA', 'MAISSA', 'MANCERA', 'MANDARINA DUCK', 'MARC ANTOINE BARROIS', 'MARC JACOBS', 'MARC JOSEPH', 'MARINA DE BOURBON', 'MASAKI MATSUSHIMA', 'MAUBOUSSIN', 'MAX MARA', 'MAX PHILIP', 'MAXFACTOR', 'MAYBELLINE', 'MAZZOLARI', 'MCM', 'MEMO', 'MEXX', 'MICHAEL KORS', 'MIHAN AROMATICS', 'MILLER ET BERTAUX', 'MIN NEW YORK', 'MISSONI', 'MIU MIU', 'MIZENSIR', 'MOLECULE', 'MOLINARD', 'MONCLER', 'MONOTHEME', 'MONT  BLANC', 'MONT BLANC', 'MONTALE', 'MOOD', 'MORESQUE', 'MOSCHINO', 'MUGLER', 'NAN', 'NAOMI CAMPBELL', 'NARCISO RODRIGUEZ', 'NASOMATTO', 'NICOLE FARHI', 'NINA RICCI', 'NOBILE 1942', 'NORAN PERFUMES', 'NOUVEAU PARIS', 'NVDO', 'ODEJO', 'OJAR', 'OLFACTIVE STUDIO', 'ONCE', 'ONNO', 'ORENS', 'ORLANE', 'ORLOV', 'ORMONDE JAYNE', 'ORTO PARISI', 'OSCAR DE LA RENTA', 'PACO RABANNE', 'PALOMA PICASSO', 'PARADIS DES SENS', "PARFUM D'EMPIRE", 'PARFUMS BDK', 'PARFUMS  DE  MARLY', 'PARFUMS DE MARLY', 'PARFUMS DUSITA', 'PARIS HILTON', 'PARLE MOI DE PARFUM', 'PENHALIGON', "PENHALIGON'S", 'PEPE JEANS', 'PERROY', 'PIERRE GUILLAUME', 'PHARRELL  WILLIAMS', 'PHILIPP PLEIN', "PLUME IMPRESSION", 'POLICE', 'PRADA', 'PROFUMUM ROMA', 'PRUDENCE', 'PUPA', 'PUREDISTANCE', 'RALPH LAUREN', 'RANCE 1795', 'RASASI', 'REBATCHI', 'REMY LATOUR', 'REPLAY', 'REVILLON', 'ROBERTO CAVALLI', 'ROCHAS', 'ROJA DOVE', 'ROMEO GIGILI', 'ROOM 1015', 'ROSENDO MATEU', 'ROYAL CROWN', 'RUDROSS', 'S.T. DUPONT', 'SALVADOR DALI', 'FERRAGAMO', 'SALVADORE DALI', 'SANDALIA', 'SARA JESSICA PARKER', 'SARAH JESSICA PARKER', 'SAWALEF', 'SERGE  LUTENS', 'SERGE LUTENS', 'SERGIO NERO', 'SERGIO TACCHINI', 'SHAIK', 'SHAKIRA', 'SHISEIDO', 'SIMONE COSAC', 'SISLEY', 'SLAVA ZAITSEV', 'SLY JOHN`S LAB', 'SONIA RYKIEL', 'SOOUD', 'SOSPIRO PERFUMES', 'STEFANO RICCI', 'STELLA MC CARTNEY', 'STELLA MCCARTNEY', 'STEPHANIE DE BRUIJ', 'STERLING PARFUMS ARMAF', 'STRANGELOVE', 'SWEDOFT', 'SWISS ARABIAN', 'TACCHINI', 'TEATRO FRAGRANZE', 'TED LAPIDUS', 'TERESA HELBIG', 'THAMEEN LONDON', 'THE DIFFERENT COMPANY', 'THE FRAGRANCE KITCHEN', 'THE HOUSE OF OUD', 'THE MERCHANT OF VENICE', 'THOMAS KOSMALA', 'TIFFANY', 'TIZIANA TERENZI', 'TOM FORD', 'TOMMY HILFIGER', 'TORRENTE', 'TREE OF LIFE', 'TRUSSARDI', 'ULRIC DE VARENS', 'V CANTO', 'VALENTINO', 'VAN CLEEF & ARPELS', 'VAN GILS', 'VANDERBILT', 'VERA WANG', 'VERONIQUE GABA', 'VERSACE', 'VERTUS', "VICTORIA'S SECRET", 'VIKTOR & ROLF', 'VILHELM PARFUMERIE', 'WHAT WE DO IS SECRET (A LAB ON FIRE)', 'WILGERMAIN', "WOMEN'SECRET", 'XERJOFF', 'YOHJI YAMAMOTO', 'YVES ROCHER', 'YVES SAINT LAURENT', 'ZADIG & VOLTAIRE', 'ZARKOPERFUME', 'ZIELINSKI & ROZEN', 'ZIMAYA', 'ZLATAN IBRAHIMOVIC', 'НОВАЯ ЗАРЯ', 'ОСТАЛЬНОЕ', 'ПАКЕТЫ'}

brand_synonyms = {
    "100BON": ["100bon", "100 bon"],
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
    "ANTONIO BANDERAS": ["antonio banderas", "a. banderas", "a.banderas", "ant. banderas"],
    "ARABESQUE": ["arabesque"],
    "ARAMIS": ["aramis"],
    "STERLING PARFUMS ARMAF": ["armaf", "(sterling parfums)", "sterling parfums"],
    "ARMAND BASI": ["armand basi"],
    "ARMANI": ["armani", "emporio armani",],
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
    "CHRISTIAN DIOR": ["christian dior", "c.dior", "dior", "c. dior", "c.d.", "cd", "DIOR CD"],
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
        "dolce gabbana", "d & g",
        "D & G",
        "dg",
        "dolce  gabbana"
    ],
    "DONNA KARAN": ["donna karan", "dkny", "d.karan", "DONNA KARAN DKNY"],
    "DSQUARED2": ["dsquared2"],
    "ELIZABETH ARDEN": ["elizabeth arden"],
    "ESCADA": ["escada"],
    "ESCENTRIC MOLECULES": ["escentric molecules"],

    "ESTEE LAUDER": ["estee lauder"],
    "ETAT LIBRE D`ORANGE": ["etat libre d'orange", "etat libre", "etat libre d orange", "etat libre d*orange", "etat libre d'orange"],
    "EX NIHILO": ["ex nihilo"],
    "FENDI": ["fendi"],
    "FERRAGAMO": ["SALVATORE FERRAGAMO", "FERRAGAMO SALVATORE", "ferragamo", "ferragamo salvatore", "s. ferragamo", "salvatore ferragamo", "salvatore", "s.ferragamo", "salvat.ferr."],
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
    "MAISON MICALLEF": ["m. micallef", "m.micallef"],
    "MONTALE": ["montale"],
    "MANCERA": ["mancera"],
    "MARINA DE BOURBON": ["m. de bourbon"],
    "MASAKI MATSUSHIMA": ["m. matsushima masaki", "m. matsushima"],

    "MEMO": ["memo"],
    "MOSCHINO": ["moschino"],
    "NAOMI CAMPBELL": ["naomi campbell", "n.campbell"],
    "NARCISO RODRIGUEZ": ["narciso rodriguez"],
    "NINA RICCI": [
        "nina ricci",
    ],
    "PACO RABANNE": ["paco rabbanne", "p.r.", "paco rabbane"],
    "PRADA": ["prada"],
    "SALVADOR DALI": ["salvador dali", "s.dali", 'sd'],
    "SERGE LUTENS": ["serge lutens"],
    "SUPREME 24K": ["supreme 24k", '24 K SUPREME', '24k supreme', "supreme 24 k"],
    "MUGLER": ["thierry mugler", "therry mugler", "t.mugler", "mugler", "t. mugler"],
    "TIZIANA TERENZI": ["tiziana terenzi"],
    "TOM FORD": ["tom ford"],
    "VAN CLEEF & ARPELS": ["van cleef & arpels", "van cleef", "vca"],
    "VICTORIA'S SECRET": ["victorias secret", "victoria's secret", "victoria's secret"],
    "VIKTOR & ROLF": [
        "viktor & rolf",
        "viktor&rolf",
        "viktor and rolf",
        "v&r",
        "v&r flowerbomb",
    ],
    "VERSACE": ["versace"],
    "VILHELM PARFUMERIE": ["vilhelm parfumerie", "vilhelm"],
    "WOMEN'SECRET": ["women' secret"],
    "XERJOFF": ["xerjoff", "xj"],
    "YVES SAINT LAURENT": [
        "yves saint laurent",
        "ysl",
        "y.saint laurent",
        "y.saint-laurent",
    ],
    "YOHJI YAMAMOTO": ["yohji yamamoto", "yohjii yamamoto", "yohji"],
    "ZADIG & VOLTAIRE": ["zadig & voltair", "zadig&voltaire", "zadig"],
    "ZARKOPERFUME": ["zarkoperfume"],
    "ZLATAN IBRAHIMOVIC": ["zlatan ibrahimovic", "zlatan", "ibrahimovic"],
}

new_unique_brands = {
    "ABSOLUMENT PARFUMEUR",
    "ABSOLUT",
    "ACCA KAPPA",
    "ACCENDIS",
    "ACQUA COLONIA",
    "ACQUA DI GENOVA",
    "ACQUA DI MONACO",
    "ACQUA DI PARISIS",
    "ACQUA DI PORTOFINO",
    "ADAM LEVINE",
    "ADDICTIVE ARTS",
    "ADJIUMI",
    "ADRIANO DOMIANNI",
    "ADRIENNE VITTADINI",
    "AEDES DE VENUSTAS",
    "AERIN",
    "AFFINESSENCE",
    "AGATHA",
    "AGONIST",
    "AIGNER",
    "AKARO",
    "AL AMBRA",
    "AL HAMATT",
    "AL JAZEERA PERFUMES",
    "AL KIMIYA",
    "AL-REHAB"
}

# Code to update your uniquie_brands set
uniquie_brands.update(new_unique_brands)

# New brand synonyms to add
new_brand_synonyms = {
    "ANTONIO BANDERAS": ["a banderas", "a. banderas", "a.banderas"],
    "ARMAND BASI": ["a. basi", "a.basi"],
    "ABERCROMBIE & FITCH": ["abercrombie fitch"],
    "ACQUA DI PARISIS": ["acqua di parisis"],
    "ACQUA DI GENOVA": ["acqua di genova"],
    "ACQUA DI MONACO": ["acqua di monaco"],
    "ACQUA DI PORTOFINO": ["acqua di portofino"],
    "ADIDAS": ["adidas"],
    "AJMAL": ["ajmal"],
    "WHAT WE DO IS SECRET (A LAB ON FIRE)": ["a lab on fire"],
    "ABSOLUMENT PARFUMEUR": ["absolument parfumeur"],
    "ABSOLUT": ["absolut"],
    "ACCA KAPPA": ["acca kappa"],
    "ACCENDIS": ["accendis"],
    "ACQUA COLONIA": ["acqua colonia"],
    "AEDES DE VENUSTAS": ["aedes de venustas"],
    "AERIN": ["aerin"],
    "AFFINESSENCE": ["affinessence"],
    "AGATHA": ["agatha"],
    "AGONIST": ["agonist"],
    "AIGNER": ["aigner"],
    "AKARO": ["akaro"],
    "AL AMBRA": ["al ambra"],
    "AL HAMATT": ["al hamatt"],
    "AL JAZEERA PERFUMES": ["al jazeera perfumes"],
    "AL-REHAB": ["al-rehab", "al rehab"],
    "AL KIMIYA": ["al kimiya"],
    "ADRIENNE VITTADINI": ["adrienne vittadini"],
    "ADAM LEVINE": ["adam levine"],
    "ADDICTIVE ARTS": ["addictive arts"],
    "ADJIUMI": ["adjiumi"],
    "ADOLFO DOMINGUEZ": ["adolfo dominguez"],
    "ADRIANO DOMIANNI": ["adriano domianni"],
}

# To update your existing brand_synonyms dictionary
brand_synonyms.update(new_brand_synonyms)


new_brands_from_list_4 = {
    "AL WATANIAH",
    "ALAIA",
    "ALAIN DELON",
    "ALAMBRA",
    "ALAN BRAY",
    "ALESSANDRO DELL'ACQUA",
    "ALEXA LIXFELD",
    "ALFRED DUNHILL",
    "ALFRED SUNG",
    "ALGHABRA",
    "ALHAMBRA",
    "ALLA PUGACHEVA",
    "ALLYRA",
    "ALSAYAD",
    "ALTAIA",
    "ALYSON OLDOINI",
    "ALYSSA ASHLEY",
    "AMATI",
    "AMBASSADOR",
    "AMEERAT AL ARAB",
    "AMERICAN EAGLE",
    "AMI ADRIAN",
    "AMIRIUS",
    "AMZAN",
    "ANDREA MAACK",
    "ANDY WARHOL",
    "ANFAS ALKHALEEJ",
    "ANGELA CIAMPAGNA",
    "ANIMALE",
    "ANIMA MUNDI",
    "ANNA PAGHERA",
    "ANNAELLE",
    "ANNAYAKE",
    "ANNICK GOUTAL",
    "ANTIGONE",
    "ANTONIO DMETRI",
    "ANTONIO FUSCO",
    "ANTONIO PUIG",
    "ANTONIO VISCONTI"
}

# New brand synonyms to add from this list
new_brand_synonyms_from_list_4 = {
    "AL WATANIAH": ["al wataniah"],
    "ALAIA": ["alaia"],
    "ALAIN DELON": ["alain delon"],
    "ALAMBRA": ["alambra"],
    "ALAN BRAY": ["alan bray"],
    "ALESSANDRO DELL'ACQUA": ["alessandro dell'acqua"],
    "ALEXA LIXFELD": ["alexa lixfeld"],
    "ALEXANDRE J.": ["alexande j", "alexander j"],
    "ALFRED DUNHILL": ["alfred dunhill", "dunhill"],
    "ALFRED SUNG": ["alfred sung"],
    "ALGHABRA": ["alghabra"],
    "ALHAMBRA": ["alhambra"],
    "ALLA PUGACHEVA": ["alla pugacheva", "alla pugachova"],
    "ALLYRA": ["allyra"],
    "ALSAYAD": ["alsayad"],
    "ALTAIA": ["altaia"],
    "ALYSON OLDOINI": ["alyson oldoini", "alyson"],
    "ALYSSA ASHLEY": ["alyssa ashley"],
    "AMATI": ["amati"],
    "AMBASSADOR": ["ambassador"],
    "AMEERAT AL ARAB": ["ameerat al arab"],
    "AMERICAN EAGLE": ["american eagle"],
    "AMI ADRIAN": ["ami adrian"],
    "AMIRIUS": ["amirius"],
    "AMZAN": ["amzan"],
    "ANDREA MAACK": ["andrea maack"],
    "ANDY WARHOL": ["andy warhol"],
    "ANFAS ALKHALEEJ": ["anfas alkhaleej"],
    "ANGELA CIAMPAGNA": ["angela ciampagna"],
    "ANIMALE": ["animale"],
    "ANIMA MUNDI": ["anima mundi"],
    "ANNA PAGHERA": ["anna paghera"],
    "ANNAELLE": ["annaelle"],
    "ANNAYAKE": ["annayake"],
    "ANNICK GOUTAL": ["annick goutal"],
    "ANTIGONE": ["antigone"],
    "ANTONIO DMETRI": ["antonio dmetri"],
    "ANTONIO FUSCO": ["antonio fusco"],
    "ANTONIO PUIG": ["antonio puig"],
    "ANTONIO VISCONTI": ["antonio visconti"]
}

# Code to update your uniquie_brands set
uniquie_brands.update(new_brands_from_list_4)

# To update your existing brand_synonyms dictionary
brand_synonyms.update(new_brand_synonyms_from_list_4)

# Additional brands from the new list that aren't in uniquie_brands
new_brands_from_list_5 = {
    "APPLE",
    "APRIL AROMATICS",
    "AQUA",
    "AQUOLINA",
    "ARABIA",
    "ARABIAN PRESTIGE",
    "ARABIAN WIND",
    "ARAXI",
    "ARD AL KHALEEJ",
    "ARD AL ZAAFARAN",
    "ARIANA GRANDE",
    "ARISTOCRAZY",
    "AROME",
    "ARROGANCE",
    "ART DE PARFUM",
    "ART OF SEDUCTION",
    "ARTE OLFATTO",
    "ARTEK",
    "ARTEOLFATTO",
    "ASDAAF",
    "ASGHARALI",
    "ASMR FRAGRANCES",
    "ATELIER FAYE",
    "ATELIER FLOU",
    "ATELIER REBUL",
    "ATELIER VERSACE",
    "ATHOOR AL ALAM",
    "ATTACHE",
    "AU PAYS DE LA FLEUR D'ORANGER",
    "AUBUSSON",
    "AUGUSTE",
    "AURORA SCENTS",
    "AVEC DEFI",
    "AZAGURY",
    "UNITOP"
}

# New brand synonyms to add from this list
new_brand_synonyms_from_list_5 = {
    "APPLE": ["apple"],
    "APRIL AROMATICS": ["april aromatics"],
    "AQUA": ["aqua"],
    "AQUOLINA": ["aquolina"],
    "ARABIA": ["arabia"],
    "ARABIAN PRESTIGE": ["arabian prestige"],
    "ARABIAN WIND": ["arabian wind"],
    "ARAXI": ["araxi"],
    "ARD AL KHALEEJ": ["ard al khaleej"],
    "ARD AL ZAAFARAN": ["ard al zaafaran", "ard zaafaran"],
    "ARIANA GRANDE": ["ariana grande"],
    "ARISTOCRAZY": ["aristocrazy"],
    "ARMAND BASI": ["armand basi"],
    "AROME": ["arome", "arome arthes"],
    "ARROGANCE": ["arrogance"],
    "ART DE PARFUM": ["art de parfum"],
    "ART OF SEDUCTION": ["art of seduction"],
    "ARTE OLFATTO": ["arte olfatto"],
    "ARTEK": ["artek"],
    "ARTEOLFATTO": ["arteolfatto"],
    "ASDAAF": ["asdaaf"],
    "ASGHARALI": ["asgharali"],
    "ASMR FRAGRANCES": ["asmr fragrances"],
    "ATELIER FAYE": ["atelier faye"],
    "ATELIER FLOU": ["atelier flou"],
    "ATELIER REBUL": ["atelier rebul"],
    "ATELIER VERSACE": ["atelier versace"],
    "ATHOOR AL ALAM": ["athoor al alam"],
    "ATTACHE": ["attache"],
    "AU PAYS DE LA FLEUR D'ORANGER": ["au pays de la fleur d'oranger"],
    "AUBUSSON": ["aubusson"],
    "AUGUSTE": ["auguste"],
    "AURORA SCENTS": ["aurora scents"],
    "AVEC DEFI": ["avec defi"],
    "AZAGURY": ["azagury"],
    "CACHAREL": ["cacharel", "amor amor (cacharel)"],
    "ELIZABETH ARDEN": ["arden"],
    "UNITOP": ["unitop"],
}

# Code to update your uniquie_brands set
uniquie_brands.update(new_brands_from_list_5)

# To update your existing brand_synonyms dictionary
brand_synonyms.update(new_brand_synonyms_from_list_5)

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
    string = string.replace("fragrance world ", "").strip()  # Убираем неразрывные пробелы и лишние пробелы
    string = string.replace("\xa0", " ").strip()  # Убираем неразрывные пробелы и лишние пробелы

    for brand in get_all_brand_aliases():
        if string.lower().startswith(brand):
            brand_name = get_standard_brand_fuzzy(brand)
            return brand_name
    return "NAN"
