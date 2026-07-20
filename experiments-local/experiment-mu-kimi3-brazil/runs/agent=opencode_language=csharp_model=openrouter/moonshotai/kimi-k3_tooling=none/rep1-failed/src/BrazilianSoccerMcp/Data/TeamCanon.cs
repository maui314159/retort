namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Canonical team identity across the five match datasets.
///
/// Each source file names clubs differently:
///   "Vasco da Gama-RJ" (Brasileirão) / "Vasco" (histórico, Libertadores) / "Vasco Da Gama RJ" (BR-Football)
///   "Atletico-PR" / "Athletico-PR" / "Athletico Paranaense" / "Athletico" (Libertadores)
///
/// Naively stripping the state suffix is WRONG for clubs whose state is the only
/// distinguisher ("Atletico-PR" vs "Atletico-MG" vs "Atletico-GO", "Botafogo-RJ"
/// vs "Botafogo-PB", "Penarol-AM" vs Peñarol of Uruguay). So resolution is:
///
///   1. normalize (diacritics, case, punctuation)
///   2. exact alias lookup on the FULL normalized form  ("botafogo pb" -> botafogo-pb)
///   3. strip trailing state/UF token, alias lookup again ("vasco da gama" -> vasco)
///   4. fall back to the stripped normalized form
/// </summary>
public static class TeamCanon
{
    private static readonly string[] StateTokens =
    [
        "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
        "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
        "sp", "se", "to",
    ];

    /// <summary>Canonical slug -> preferred display name.</summary>
    public static readonly IReadOnlyDictionary<string, string> DisplayNames;

    /// <summary>Normalized variant -> canonical slug.</summary>
    private static readonly Dictionary<string, string> Aliases;

    static TeamCanon()
    {
        // canonical slug, display name, variants (normalized forms)
        var table = new (string Canon, string Display, string[] Variants)[]
        {
            // ---------- Série A regulars ----------
            ("flamengo", "Flamengo", ["flamengo", "flamengo rj"]),
            ("flamengo-pi", "Flamengo do Piauí", ["flamengo pi", "flamengo do piaui", "flamengo do piaui pi"]),
            ("fluminense", "Fluminense", ["fluminense", "fluminense rj"]),
            ("fluminense-pi", "Fluminense-PI", ["fluminense pi"]),
            ("fluminense-de-feira", "Fluminense de Feira", ["fluminense de feira", "fluminense de feira ba"]),
            ("vasco", "Vasco da Gama", ["vasco", "vasco da gama", "vasco da gama rj"]),
            ("botafogo-rj", "Botafogo", ["botafogo", "botafogo rj"]),
            ("botafogo-pb", "Botafogo-PB", ["botafogo pb"]),
            ("botafogo-sp", "Botafogo-SP", ["botafogo sp"]),
            ("palmeiras", "Palmeiras", ["palmeiras", "palmeiras sp", "sociedade esportiva palmeiras"]),
            ("corinthians", "Corinthians", ["corinthians", "corinthians sp", "sport club corinthians paulista", "corinthians paulista"]),
            ("sao-paulo", "São Paulo", ["sao paulo", "sao paulo sp", "sao paulo fc"]),
            ("santos", "Santos", ["santos", "santos sp", "santos fc"]),
            ("santos-ap", "Santos-AP", ["santos ap"]),
            ("gremio", "Grêmio", ["gremio", "gremio rs", "gremio foot ball porto alegrense"]),
            ("internacional", "Internacional", ["internacional", "internacional rs", "sc internacional", "sport club internacional"]),
            ("internacional-sc", "Internacional de Lages", ["internacional sc", "ec internacional sc", "inter de lages"]),
            ("atletico-mg", "Atlético Mineiro", ["atletico mg", "atletico mineiro", "clube atletico mineiro", "galo"]),
            ("athletico-pr", "Athletico Paranaense", ["athletico pr", "atletico pr", "athletico paranaense", "atletico paranaense", "athletico", "athletico paranaense pr", "clube atletico paranaense", "ca parana"]),
            ("atletico-go", "Atlético Goianiense", ["atletico go", "atletico goianiense", "atletico clube goianiense"]),
            ("atletico-acreano", "Atlético Acreano", ["atletico ac", "atletico acreano"]),
            ("atletico-alagoinhas", "Atlético de Alagoinhas", ["atletico ba", "atletico alagoinhas"]),
            ("atletico-cearense", "Atlético Cearense", ["atletico cearense", "atletico cearense ce", "fc atletico cearense"]),
            ("cruzeiro", "Cruzeiro", ["cruzeiro", "cruzeiro mg", "cruzeiro esporte clube"]),
            ("bahia", "Bahia", ["bahia", "bahia ba", "ec bahia", "esporte clube bahia"]),
            ("bahia-de-feira", "Bahia de Feira", ["bahia de feira", "bahia de feira ba"]),
            ("vitoria", "Vitória", ["vitoria", "vitoria ba", "ec vitoria", "vitoria ec", "esporte clube vitoria"]),
            ("vitoria-es", "Vitória-ES", ["vitoria es", "vitoria f c", "vitoria f c es", "vitoria fc"]),
            ("vitoria-da-conquista", "Vitória da Conquista", ["vitoria da conquista", "vitoria da conquista ba"]),
            ("sport", "Sport Recife", ["sport", "sport pe", "sport recife", "sport club do recife"]),
            ("ceara", "Ceará", ["ceara", "ceara ce", "ceara sporting club"]),
            ("fortaleza", "Fortaleza", ["fortaleza", "fortaleza ce", "fortaleza ec", "fortaleza fc", "fortaleza esporte clube"]),
            ("coritiba", "Coritiba", ["coritiba", "coritiba pr", "coritiba foot ball club"]),
            ("athletic-club-mg", "Athletic Club-MG", ["athletic club", "athletic club mg"]),
            ("chapecoense", "Chapecoense", ["chapecoense", "chapecoense sc", "chapecoense af"]),
            ("avai", "Avaí", ["avai", "avai sc", "avai fc"]),
            ("goias", "Goiás", ["goias", "goias go", "goias esporte clube"]),
            ("cuiaba", "Cuiabá", ["cuiaba", "cuiaba mt", "cuiaba esporte clube"]),
            ("juventude", "Juventude", ["juventude", "juventude rs", "ec juventude", "esporte clube juventude"]),
            ("juventude-ma", "Juventude-MA", ["juventude ma"]),
            ("america-mg", "América Mineiro", ["america mg", "america mineiro", "america futebol clube mg"]),
            ("america-rn", "América de Natal", ["america rn", "america de natal", "america de natal rn", "america fc natal", "america futebol clube rn"]),
            ("rb-bragantino", "Red Bull Bragantino", ["red bull bragantino", "red bull bragantino sp", "bragantino", "bragantino sp", "clube atletico bragantino"]),
            ("bragantino-pa", "Bragantino-PA", ["bragantino pa"]),
            ("red-bull-brasil", "Red Bull Brasil", ["red bull brasil", "red bull brasil sp"]),
            ("csa", "CSA", ["csa", "csa al", "c s a", "c s a al", "centro sportivo alagoano"]),
            ("crb", "CRB", ["crb", "crb al", "c r b", "c r b al", "clube de regatas brasil"]),
            ("abc", "ABC", ["abc", "abc rn", "a b c", "a b c rn", "abc futebol clube"]),
            ("asa", "ASA", ["asa", "asa al", "a s a", "a s a al", "agremiacao sportiva arapiraquense"]),
            ("nautico", "Náutico", ["nautico", "nautico pe", "nautico capibaribe", "clube nautico capibaribe"]),
            ("nautico-rr", "Náutico-RR", ["nautico rr"]),
            ("santa-cruz", "Santa Cruz", ["santa cruz", "santa cruz pe", "santa cruz fc", "santa cruz futebol clube"]),
            ("santa-cruz-rn", "Santa Cruz-RN", ["santa cruz rn"]),
            ("santa-cruz-rs", "Santa Cruz-RS", ["santa cruz rs"]),
            ("figueirense", "Figueirense", ["figueirense", "figueirense sc", "figueirense fc"]),
            ("ponte-preta", "Ponte Preta", ["ponte preta", "ponte preta sp", "ponte preta campinas"]),
            ("portuguesa", "Portuguesa", ["portuguesa", "portuguesa sp", "portuguesa desportos", "associacao portuguesa de desportos"]),
            ("portuguesa-rj", "Portuguesa-RJ", ["portuguesa rj"]),
            ("parana", "Paraná Clube", ["parana", "parana pr", "parana clube"]),
            ("paysandu", "Paysandu", ["paysandu", "paysandu pa", "paysandu sport club"]),
            ("criciuma", "Criciúma", ["criciuma", "criciuma sc", "criciuma esporte clube"]),
            ("joinville", "Joinville", ["joinville", "joinville sc", "joinville esporte clube"]),
            ("brusque", "Brusque", ["brusque", "brusque sc", "brusque fc", "brusque futebol clube"]),
            ("londrina", "Londrina", ["londrina", "londrina pr", "londrina esporte clube"]),
            ("operario-pr", "Operário Ferroviário", ["operario pr", "operario ferroviario", "operario ferroviario esporte clube", "operario ferroviario esporte c", "operario ferroviario ec"]),
            ("operario-ms", "Operário-MS", ["operario ms", "operario fc ms", "operario fc"]),
            ("operario-mt", "Operário-MT", ["operario mt"]),
            ("guarani", "Guarani", ["guarani", "guarani sp", "guarani futebol clube", "guarani campinas"]),
            ("guarani-juazeiro", "Guarani de Juazeiro", ["guarani ce", "guarani de juazeiro", "guarani de juazeiro ce"]),
            ("guarany-sobral", "Guarany de Sobral", ["guarany", "guarany ce", "guarany de sobral", "guarany de sobral ce", "guarany sporting club"]),
            ("santo-andre", "Santo André", ["santo andre", "santo andre sp", "esporte clube santo andre"]),
            ("sao-caetano", "São Caetano", ["sao caetano", "sao caetano sp"]),
            ("sao-bento", "São Bento", ["sao bento", "sao bento sp", "esporte clube sao bento"]),
            ("brasiliense", "Brasiliense", ["brasiliense", "brasiliense df", "brasiliense futebol clube"]),
            ("gremio-barueri", "Grêmio Barueri", ["gremio barueri", "gremio barueri sp", "barueri", "gremio prudente barueri"]),
            ("gremio-prudente", "Grêmio Prudente", ["gremio prudente"]),
            ("ipatinga", "Ipatinga", ["ipatinga", "ipatinga mg", "ipatinga futebol clube"]),
            ("remo", "Remo", ["remo", "remo pa", "clube do remo"]),
            ("vila-nova", "Vila Nova", ["vila nova", "vila nova go", "vila nova futebol clube"]),
            ("villa-nova-mg", "Villa Nova-MG", ["villa nova", "villa nova mg", "villa nova atletico clube"]),
            ("sampaio-correa", "Sampaio Corrêa", ["sampaio correa", "sampaio correa ma", "sampaio correa futebol clube"]),
            ("crac", "CRAC", ["crac", "crac go", "c r a c", "c r a c go", "clube recreativo e atletico catalano"]),
            ("confianca", "Confiança", ["confianca", "confianca se", "ad confianca", "confianca futebol clube"]),
            ("mirassol", "Mirassol", ["mirassol", "mirassol sp", "mirassol futebol clube"]),
            ("novorizontino", "Novorizontino", ["novorizontino", "novorizontino sp", "gremio novorizontino", "gremio esportivo novorizontino"]),
            ("ituano", "Ituano", ["ituano", "ituano sp", "ituano futebol clube"]),
            ("oeste", "Oeste", ["oeste", "oeste sp", "oeste futebol clube"]),
            ("xv-piracicaba", "XV de Piracicaba", ["xv de piracicaba", "xv de piracicaba sp", "xv piracicaba"]),
            ("ferroviaria", "Ferroviária", ["ferroviaria", "ferroviaria sp", "ferroviaria araraquara"]),
            ("ferroviario-ce", "Ferroviário-CE", ["ferroviario", "ferroviario ce", "ferroviario atletico clube"]),
            ("tombense", "Tombense", ["tombense", "tombense mg", "tombense futebol clube"]),
            ("urt", "URT", ["urt", "urt mg", "u r t"]),
            ("tupi", "Tupi", ["tupi", "tupi mg", "tupi football club"]),
            ("caldense", "Caldense", ["caldense", "caldense mg", "caldense minas gerais"]),
            ("boa-esporte", "Boa Esporte", ["boa", "boa mg", "boa esporte", "boa esporte clube"]),
            ("madureira", "Madureira", ["madureira", "madureira rj", "madureira ec", "madureira esporte clube"]),
            ("volta-redonda", "Volta Redonda", ["volta redonda", "volta redonda rj", "volta redonda futebol clube"]),
            ("resende", "Resende", ["resende", "resende rj", "resende futebol clube"]),
            ("cabofriense", "Cabofriense", ["cabofriense", "cabofriense rj"]),
            ("duque-de-caxias", "Duque de Caxias", ["duque de caxias", "duque de caxias rj", "duque de caxias fc", "duque de caxias futebol clube"]),
            ("bangu", "Bangu", ["bangu", "bangu rj", "bangu atletico clube"]),
            ("boavista-rj", "Boavista-RJ", ["boavista", "boavista rj", "boavista sc", "boavista sport club", "boavista sc saquarema", "boavista sport club antigo esporte clube barreira"]),
            ("americano", "Americano", ["americano", "americano rj", "americano futebol clube"]),
            ("macae", "Macaé", ["macae", "macae rj", "macae esporte", "macae esporte fc", "macae esporte rj", "macae esporte futebol clube"]),
            ("nova-iguacu", "Nova Iguaçu", ["nova iguacu", "nova iguacu rj", "nova iguacu fc", "nova iguacu futebol clube"]),
            ("friburguense", "Friburguense", ["friburguense", "friburguense rj"]),
            ("caxias", "Caxias", ["caxias", "caxias rs", "caxias do sul", "ser caxias", "ser caxias do sul", "sociedade esportiva e recreativa caxias do sul"]),
            ("brasil-de-pelotas", "Brasil de Pelotas", ["brasil rs", "brasil de pelotas", "brasil de pelotas rs", "gremio esportivo brasil", "ge brasil"]),
            ("sao-jose-rs", "São José-RS", ["sao jose rs", "sao jose poa", "sao jose porto alegre", "esporte clube sao jose rs"]),
            ("sao-jose-pa", "São José-PA", ["sao jose pa"]),
            ("ypiranga-rs", "Ypiranga-RS", ["ypiranga", "ypiranga rs", "ypiranga futebol clube rs", "ypiranga de erechim"]),
            ("ypiranga-ap", "Ypiranga-AP", ["ypiranga ap", "ypiranga clube ap"]),
            ("sao-raimundo-pa", "São Raimundo-PA", ["sao raimundo pa"]),
            ("sao-raimundo-rr", "São Raimundo-RR", ["sao raimundo rr"]),
            ("sao-raimundo-am", "São Raimundo-AM", ["sao raimundo am"]),
            ("rio-branco-ac", "Rio Branco-AC", ["rio branco ac", "rio branco football club"]),
            ("rio-branco-es", "Rio Branco-ES", ["rio branco es", "rio branco vn", "rio branco vn es", "rio branco atletico clube"]),
            ("treze", "Treze", ["treze", "treze pb", "treze futebol clube"]),
            ("campinense", "Campinense", ["campinense", "campinense pb", "campinense clube"]),
            ("souza", "Sousa", ["souza", "souza pb", "sousa", "sousa ec", "sousa esporte clube"]),
            ("nacional-am", "Nacional-AM", ["nacional am", "nacional futebol clube", "nacional fc"]),
            ("manaus", "Manaus", ["manaus", "manaus am", "manaus futebol clube"]),
            ("fast-clube", "Fast Clube", ["fast clube", "fast clube am", "nacional fast clube"]),
            ("princesa-solimoes", "Princesa do Solimões", ["princesa do solimoes", "princesa do solimoes am"]),
            ("penarol-am", "Penarol-AM", ["penarol am"]),
            ("moto-club", "Moto Club", ["moto club", "moto club ma", "moto clube", "moto club de sao luis", "moto clube de sao luis"]),
            ("imperatriz", "Imperatriz", ["imperatriz", "imperatriz ma", "sociedade imperatriz de desportos"]),
            ("maranhao", "Maranhão", ["maranhao", "maranhao ma", "maranhao atletico clube"]),
            ("tocantinopolis", "Tocantinópolis", ["tocantinopolis", "tocantinopolis to", "tocantinopolis ec", "tocantinopolis esporte clube"]),
            ("sinop", "Sinop", ["sinop", "sinop mt", "sinop fc", "sinop futebol clube"]),
            ("mixto", "Mixto", ["mixto", "mixto mt", "mixto esporte clube"]),
            ("luverdense", "Luverdense", ["luverdense", "luverdense mt", "luverdense esporte clube"]),
            ("uniao-rondonopolis", "União de Rondonópolis", ["uniao rondonopolis", "uniao de rondonopolis", "uniao de rondonopolis mt", "uniao rondonopolis mt"]),
            ("uniao-mt", "União-MT", ["uniao mt"]),
            ("dom-bosco", "Dom Bosco", ["dom bosco", "dom bosco mt", "ce dom bosco", "clube esportivo dom bosco"]),
            ("gama", "Gama", ["gama", "gama df", "se gama", "sociedade esportiva do gama"]),
            ("brasilia", "Brasília FC", ["brasilia", "brasilia df", "brasilia fc", "brasilia futebol clube"]),
            ("ceilandia", "Ceilândia", ["ceilandia", "ceilandia df", "ceilandia esporte clube"]),
            ("sobradinho", "Sobradinho", ["sobradinho", "sobradinho df"]),
            ("luziania", "Luziânia", ["luziania", "luziania df", "luziania goias"]),
            ("anapolina", "Anapolina", ["anapolina", "anapolina go"]),
            ("anapolis", "Anápolis", ["anapolis", "anapolis go", "anapolis fc", "anapolis futebol clube"]),
            ("goianesia", "Goianésia", ["goianesia", "goianesia go"]),
            ("aparecidense", "Aparecidense", ["aparecidense", "aparecidense go"]),
            ("crac-go", "CRAC-GO (catalão)", ["crac catalano"]),
            ("jaragua", "Jaraguá", ["jaragua", "jaragua go", "jaragua ec", "jaragua esporte clube"]),
            ("icasa", "Icasa", ["icasa", "icasa ce", "ad icasa"]),
            ("horizonte", "Horizonte", ["horizonte", "horizonte ce", "horizonte futebol clube"]),
            ("floresta", "Floresta", ["floresta", "floresta ce", "floresta ec", "floresta esporte clube"]),
            ("caucaia", "Caucaia", ["caucaia", "caucaia ce", "caucaia esporte clube"]),
            ("barbalha", "Barbalha", ["barbalha", "barbalha ce"]),
            ("iguatu", "Iguatu", ["iguatu", "iguatu ce"]),
            ("uniclinic", "Uniclinic", ["uniclinic", "uniclinic ce", "uniclinic atletico clube"]),
            ("salgueiro", "Salgueiro", ["salgueiro", "salgueiro pe", "salgueiro atletico clube"]),
            ("afogados", "Afogados", ["afogados", "afogados pe", "afogados da ingazeira", "afogados da ingazeira fc", "afogados da ingazeira futebol clube"]),
            ("central", "Central-PE", ["central", "central pe", "central sc", "central sport club"]),
            ("retro", "Retrô", ["retro", "retro pe", "retro fc", "retro fc brasil", "retro futebol clube brasil"]),
            ("sergipe", "Sergipe", ["sergipe", "sergipe se", "club sportivo sergipe", "cs sergipe"]),
            ("itabaiana", "Itabaiana", ["itabaiana", "itabaiana se", "associacao olimpica de itabaiana"]),
            ("estanciano", "Estanciano", ["estanciano", "estanciano se"]),
            ("amadense", "Amadense", ["amadense", "amadense se", "amadense ec", "amadense esporte clube"]),
            ("coruripe", "Coruripe", ["coruripe", "coruripe al"]),
            ("murici", "Murici", ["murici", "murici al", "murici futebol clube"]),
            ("santa-rita", "Santa Rita", ["santa rita", "santa rita al"]),
            ("cs-alagoano", "CS Alagoano", ["cs alagoano", "cs alagoano al", "centro sportivo alagoano"]),
            ("4-de-julho", "4 de Julho", ["4 de julho", "4 de julho pi", "iv de julho", "iv de julho pi"]),
            ("altos", "Altos", ["altos", "altos pi", "ae altos", "associacao esportiva de altos"]),
            ("parnahyba", "Parnahyba", ["parnahyba", "parnahyba pi", "parnahyba s c", "parnahyba sport club"]),
            ("picos", "Picos", ["picos", "picos pi", "sociedade esportiva picos"]),
            ("piaui", "Piauí", ["piaui", "piaui pi", "piaui esporte clube"]),
            ("river-pi", "River-PI", ["river pi", "river atletico clube", "river piaui"]),
            ("flamengo-do-piaui", "Flamengo do Piauí (alt)", ["flamengo piaui"]),
            ("frei-paulistano", "Frei Paulistano", ["frei paulistano", "frei paulistano se", "ad frei paulistano", "associacao desportiva frei paulistano"]),
            ("galvez", "Galvez", ["galvez", "galvez ac", "galvez esporte clube"]),
            ("placido-de-castro", "Plácido de Castro", ["placido de castro", "placido de castro ac", "placido de castro fc"]),
            ("trem", "Trem", ["trem", "trem ap", "trem desportivo clube"]),
            ("oratorio", "Oratório", ["oratorio", "oratorio ap", "oratorio recreativo clube"]),
            ("santos-macapa", "Santos-AP (Macapá)", ["santos ap macapa"]),
            ("aguia-maraba", "Águia de Marabá", ["aguia pa", "aguia de maraba", "aguia de maraba pa"]),
            ("aguia-negra", "Águia Negra", ["aguia negra", "aguia negra ms"]),
            ("castanhal", "Castanhal", ["castanhal", "castanhal pa", "castanhal esporte clube"]),
            ("paragominas", "Paragominas", ["paragominas", "paragominas pa", "paragominas futebol clube"]),
            ("parauapebas", "Parauapebas", ["parauapebas", "parauapebas pa", "parauapebas futebol clube"]),
            ("independente-pa", "Independente de Tucuruí", ["independente", "independente pa", "independente de tucurui", "independente de tucurui pa"]),
            ("tuna-luso", "Tuna Luso", ["tuna luso", "tuna luso brasileira"]),
            ("ji-parana", "Ji-Paraná", ["ji parana", "ji parana ro", "ji parana futebol clube"]),
            ("rondoniense", "Rondoniense", ["rondoniense", "rondoniense ro"]),
            ("porto-velho", "Porto Velho", ["porto velho", "porto velho ro", "porto velho ec", "porto velho esporte clube"]),
            ("vilhena", "Vilhena", ["vilhena", "vilhena ro", "vilhena esporte clube"]),
            ("vilhenense", "Vilhenense", ["vilhenense", "vilhenense ro", "vilhenense ec"]),
            ("espigao", "Espigão", ["espigao", "espigao ro", "espigao do oeste"]),
            ("genus", "Genus", ["genus", "genus ro", "sc genus", "sport club genus de porto velho"]),
            ("real-arikemes", "Real Ariquemes", ["real ariquemes", "real ariquemes ro", "real ariquemes esporte clube"]),
            ("real-desportivo", "Real Desportivo", ["real desportivo", "real desportivo ro", "real desportivo ariquemes"]),
            ("real-noroeste", "Real Noroeste", ["real noroeste", "real noroeste es", "real noroeste capixaba", "real noroeste capixaba es", "real noroeste capixaba futebol clube"]),
            ("desportiva", "Desportiva Ferroviária", ["desportiva", "desportiva es", "desportiva ferroviaria", "desportiva ferroviaria es"]),
            ("estrela-do-norte", "Estrela do Norte", ["estrela do norte", "estrela do norte es"]),
            ("aracruz", "Aracruz", ["aracruz", "aracruz es"]),
            ("sao-mateus", "São Mateus", ["sao mateus", "sao mateus es", "sao mateus es es"]),
            ("serra", "Serra", ["serra", "serra es", "serra f c", "serra f c es", "serra fc"]),
            ("nova-venecia", "Nova Venécia", ["nova venecia", "nova venecia es", "nova venecia fc"]),
            ("sao-bernardo", "São Bernardo", ["sao bernardo", "sao bernardo sp", "sao bernardo futebol clube"]),
            ("audax", "Audax", ["audax", "audax sp", "gremio osasco audax"]),
            ("capivariano", "Capivariano", ["capivariano", "capivariano sp", "capivariano futebol clube"]),
            ("marilia", "Marília", ["marilia", "marilia sp", "marilia atletico clube"]),
            ("linense", "Linense", ["linense", "linense sp", "clube atletico linense"]),
            ("noroeste", "Noroeste", ["noroeste", "noroeste sp", "esporte clube noroeste"]),
            ("paulista", "Paulista de Jundiaí", ["paulista", "paulista sp", "paulista futebol clube", "paulista de jundiai"]),
            ("votuporanguense", "Votuporanguense", ["votuporanguense", "votuporanguense sp", "ca votuporanguense", "clube atletico votuporanguense"]),
            ("mogi-mirim", "Mogi Mirim", ["mogi mirim", "mogi mirim sp", "mogi mirim esporte clube"]),
            ("guaratingueta", "Guaratinguetá", ["guaratingueta", "guaratingueta sp", "guaratingueta futebol"]),
            ("guarulhos", "Guarulhos", ["guarulhos", "guarulhos sp"]),
            ("suzano", "Suzano", ["suzano", "suzano sp"]),
            ("inter-limeira", "Inter de Limeira", ["inter de limeira", "inter de limeira sp", "associacao atletica internacional limeira"]),
            ("cianorte", "Cianorte", ["cianorte", "cianorte pr", "cianorte futebol clube"]),
            ("maringa", "Maringá", ["maringa", "maringa pr", "maringa futebol clube"]),
            ("cascavel", "Cascavel", ["cascavel", "cascavel pr", "fc cascavel", "fc cascavel pr", "futebol clube cascavel"]),
            ("toledo", "Toledo", ["toledo", "toledo pr", "toledo ec", "toledo esporte clube", "toledo colonia work"]),
            ("pstc", "PSTC", ["pstc", "pstc pr", "parana soccer technical center"]),
            ("j-malucelli", "J. Malucelli", ["j malucelli", "j malucelli pr", "j malucelli futebol"]),
            ("arapongas", "Arapongas", ["arapongas", "arapongas pr", "arapongas esporte clube"]),
            ("foz-do-iguacu", "Foz do Iguaçu", ["foz do iguacu", "foz do iguacu pr", "foz do iguacu futebol clube"]),
            ("azuriz", "Azuriz", ["azuriz", "azuriz pr", "azuriz fc", "azuriz futebol clube"]),
            ("tubarao", "Tubarão", ["tubarao", "tubarao sc", "atletico tubarao"]),
            ("metropolitano", "Metropolitano", ["metropolitano", "metropolitano sc", "clube atletico metropolitano"]),
            ("marcilio-dias", "Marcílio Dias", ["marcilio dias", "marcilio dias sc", "clube nautico marcilio dias"]),
            ("camboriu", "Camboriú", ["camboriu", "camboriu sc", "camboriu futebol clube"]),
            ("aimore", "Aimoré", ["aimore", "aimore rs", "ce aimore", "clube esportivo aimore"]),
            ("esportivo", "Esportivo", ["esportivo", "esportivo rs", "esportivo bento goncalves", "clube esportivo bento goncalves"]),
            ("lajeadense", "Lajeadense", ["lajeadense", "lajeadense rs"]),
            ("veranopolis", "Veranópolis", ["veranopolis", "veranopolis rs", "veranopolis esporte clube"]),
            ("novo-hamburgo", "Novo Hamburgo", ["novo hamburgo", "novo hamburgo rs", "esporte clube novo hamburgo"]),
            ("sao-luiz-rs", "São Luiz-RS", ["sao luiz", "sao luiz rs", "esporte clube sao luiz"]),
            ("gloria", "Glória", ["gloria", "gloria rs", "ge gloria", "gremio esportivo gloria"]),
            ("bage", "Bagé", ["bage", "bage rs", "ge bage", "gremio esportivo bage"]),
            ("passo-fundo", "Passo Fundo", ["passo fundo", "passo fundo rs", "esporte clube passo fundo"]),
            ("gremio-anapolis", "Grêmio Anápolis", ["gremio anapolis", "gremio anapolis go"]),
            ("gremio-esportivo-sapucaiense", "Grêmio Sapucaiense", ["gremio esportivo sapucaiense", "gremio sapucaiense"]),
            ("gremio-osasco", "Grêmio Osasco", ["gremio osasco"]),
            ("ser-caxias", "SER Caxias (alt)", ["sociedade esportiva e recreativa caxias"]),
            ("cene", "CENE", ["cene", "cene ms", "clube esportivo nova esperanca"]),
            ("ceo-varzeagrandense", "CEO Varzeagrandense", ["ceo varzeagrandense", "ceo", "clube esportivo operario varzeagrandense"]),
            ("aquidauanense", "Aquidauanense", ["aquidauanense", "aquidauanense ms", "aquidauanense futebol clube"]),
            ("novoperario", "Novoperário", ["novoperario", "novoperario ms", "novoperario futebol clube"]),
            ("naviraiense", "Naviraiense", ["naviraiense", "naviraiense ms"]),
            ("ivinhema", "Ivinhema", ["ivinhema", "ivinhema ms", "ivinhema futebol clube"]),
            ("corumbaense", "Corumbaense", ["corumbaense", "corumbaense ms", "corumbaense futebol clube"]),
            ("comercial-ms", "Comercial-MS", ["comercial ms", "esporte clube comercial ms"]),
            ("sete-setembro", "Sete de Setembro", ["sete de setembro", "sete de setembro ms", "7 de setembro", "7 de setembro ms"]),
            ("operario-cg", "Operário de Campo Grande", ["operario campo grande"]),
            ("costa-rica-ec", "Costa Rica EC", ["costa rica", "costa rica ec", "costa rica ms"]),
            ("itaporã", "Itaporã", ["itapora", "itapora ms"]),
            ("gurupi", "Gurupi", ["gurupi", "gurupi to", "gurupi esporte clube"]),
            ("palmas", "Palmas", ["palmas", "palmas to", "palmas ltda", "palmas fr", "palmas futebol e regatas"]),
            ("interporto", "Interporto", ["interporto", "interporto to", "interporto futebol clube"]),
            ("tocantins-miracema", "Tocantins de Miracema", ["tocantins", "tocantins to", "tocantins de miracema"]),
            ("humaita", "Humaitá", ["humaita", "humaita ac", "humaita sport clube"]),
            ("amazonas", "Amazonas FC", ["amazonas", "amazonas fc", "amazonas futebol clube"]),
            ("peixe", "Peixe da Amazônia", ["peixe da amazonia", "peixe da amazonia ap", "peixe esporte clube"]),
            ("globo", "Globo FC", ["globo", "globo rn", "globo fc", "globo futebol clube"]),
            ("alecrim", "Alecrim", ["alecrim", "alecrim rn", "alecrim futebol clube"]),
            ("potiguar", "Potiguar", ["potiguar", "potiguar rn", "acesso potiguar"]),
            ("americano-rn", "Americano de Natal", ["americano de natal"]),
            ("botafogo-pb2", "Botafogo da Paraíba (alt)", ["botafogo joao pessoa"]),
            ("auto-esporte", "Auto Esporte-PB", ["auto esporte", "auto esporte pb", "auto esporte clube pb"]),
            ("sao-francisco-pa", "São Francisco-PA", ["sao francisco pa", "sao francisco futebol clube pa", "s francisco pa"]),
            ("sao-francisco-ac", "São Francisco-AC", ["sao francisco ac", "sao francisco futebol clube ac"]),
            ("cordino", "Cordino", ["cordino", "cordino ma", "cordino ec", "cordino esporte clube"]),
            ("santa-quiteria", "Santa Quitéria", ["santa quiteria", "santa quiteria ma", "santa quiteria futebol clube"]),
            ("sao-domingos", "São Domingos-SE", ["sao domingos", "sao domingos se", "sao domingos futebol clube"]),
            ("7-de-setembro-alt", "7 de Setembro (alt)", ["sete de setembro dourados"]),
            // ---------- Foreign clubs (Libertadores) ----------
            ("penarol-uru", "Peñarol", ["penarol", "penarol uru", "ca penarol"]),
            ("nacional-uru", "Nacional (URU)", ["nacional uru", "club nacional de football"]),
            ("nacional-par", "Nacional (PAR)", ["nacional par", "club nacional paraguay"]),
            ("olimpia", "Olimpia", ["olimpia", "olimpia par", "club olimpia"]),
            ("cerro-porteno", "Cerro Porteño", ["cerro porteno", "cerro porteno par"]),
            ("libertad", "Libertad", ["libertad", "libertad par"]),
            ("guarani-par", "Guaraní (PAR)", ["guarani par", "club guarani"]),
            ("boca-juniors", "Boca Juniors", ["boca juniors"]),
            ("river-plate", "River Plate", ["river plate", "club atletico river plate"]),
            ("river-plate-uru", "River Plate (URU)", ["river plate uru"]),
            ("river-plate-se", "River Plate-SE", ["river plate se", "river plate sergipe"]),
            ("racing", "Racing Club", ["racing", "racing club", "racing club avellaneda"]),
            ("san-lorenzo", "San Lorenzo", ["san lorenzo"]),
            ("independiente", "Independiente", ["independiente", "ca independiente", "club atletico independiente"]),
            ("velez", "Vélez Sarsfield", ["velez sarsfield", "velez"]),
            ("estudiantes", "Estudiantes", ["estudiantes", "estudiantes de la plata", "estudiantes lp"]),
            ("newells", "Newell's Old Boys", ["newells old boys", "newells"]),
            ("rosario-central", "Rosario Central", ["rosario central"]),
            ("lanus", "Lanús", ["lanus", "club lanus"]),
            ("argentinos-juniors", "Argentinos Juniors", ["argentinos juniors"]),
            ("arsenal-sarandi", "Arsenal Sarandí", ["arsenal sarandi", "arsenal de sarandi"]),
            ("defensa", "Defensa y Justicia", ["defensa y justicia", "defensa"]),
            ("godoy-cruz", "Godoy Cruz", ["godoy cruz"]),
            ("tigre", "Tigre", ["tigre", "club atletico tigre"]),
            ("huracan", "Huracán", ["huracan", "club atletico huracan"]),
            ("talleres", "Talleres", ["talleres", "talleres de cordoba"]),
            ("union-espanola", "Unión Española", ["union espanola"]),
            ("colo-colo", "Colo-Colo", ["colo colo"]),
            ("universidad-de-chile", "Universidad de Chile", ["universidad de chile", "u de chile"]),
            ("universidad-catolica", "Universidad Católica", ["universidad catolica", "u catolica"]),
            ("ohiggins", "O'Higgins", ["ohiggins", "o higgins"]),
            ("huachipato", "Huachipato", ["huachipato"]),
            ("cobresal", "Cobresal", ["cobresal"]),
            ("palestino", "Palestino", ["palestino"]),
            ("deportes-iquique", "Deportes Iquique", ["deportes iquique"]),
            ("universidad-concepcion", "Universidad de Concepción", ["universidad de concepcion", "universidad concepcion"]),
            ("union-la-calera", "Unión La Calera", ["union la calera"]),
            ("santiago-wanderers", "Santiago Wanderers", ["santiago wanderers"]),
            ("barcelona-guayaquil", "Barcelona SC", ["barcelona equ", "barcelona sc", "barcelona sporting club", "barcelona guayaquil"]),
            ("emelec", "Emelec", ["emelec", "club sport emelec"]),
            ("ldu", "LDU Quito", ["ldu", "ldu quito", "liga de quito", "liga deportiva universitaria"]),
            ("delfin", "Delfín", ["delfin", "delfin equ", "delfin sc"]),
            ("independiente-del-valle", "Independiente del Valle", ["independiente del valle", "ind del valle"]),
            ("el-nacional", "El Nacional", ["el nacional equ"]),
            ("deportivo-cuenca", "Deportivo Cuenca", ["deportivo cuenca"]),
            ("macara", "Macará", ["macara"]),
            ("universitario", "Universitario", ["universitario", "universitario per", "universitario de deportes"]),
            ("alianza-lima", "Alianza Lima", ["alianza lima"]),
            ("sporting-cristal", "Sporting Cristal", ["sporting cristal"]),
            ("cienciano", "Cienciano", ["cienciano"]),
            ("melgar", "Melgar", ["melgar", "fbc melgar"]),
            ("real-garcilaso", "Real Garcilaso", ["real garcilaso", "real atletico", "real atletico garcilaso"]),
            ("juan-aurich", "Juan Aurich", ["juan aurich"]),
            ("binacional", "Binacional", ["binacional"]),
            ("sport-boys", "Sport Boys", ["sport boys"]),
            ("deportivo-municipal", "Deportivo Municipal", ["deportivo municipal"]),
            ("san-jose-oruro", "San José de Oruro", ["san jose oruro", "san jose bol", "san jose de oruro"]),
            ("bolivar", "Bolívar", ["bolivar", "club bolivar"]),
            ("the-strongest", "The Strongest", ["the strongest"]),
            ("jorge-wilstermann", "Jorge Wilstermann", ["jorge wilstermann", "wilstermann"]),
            ("always-ready", "Always Ready", ["always ready"]),
            ("independiente-petrolero", "Independiente Petrolero", ["independiente petrolero"]),
            ("atletico-nacional", "Atlético Nacional", ["atletico nacional", "atletico nacional medellin"]),
            ("deportivo-cali", "Deportivo Cali", ["deportivo cali"]),
            ("america-de-cali", "América de Cali", ["america de cali"]),
            ("independiente-medellin", "Independiente Medellín", ["independiente medellin", "ind medellin"]),
            ("millonarios", "Millonarios", ["millonarios"]),
            ("junior", "Junior de Barranquilla", ["junior", "junior de barranquilla", "junior barranquilla", "atletico junior"]),
            ("santa-fe", "Independiente Santa Fe", ["santa fe", "ind santa fe", "independiente santa fe"]),
            ("deportes-tolima", "Deportes Tolima", ["deportes tolima", "tolima"]),
            ("once-caldas", "Once Caldas", ["once caldas"]),
            ("deportivo-lara", "Deportivo Lara", ["deportivo lara"]),
            ("deportivo-tachira", "Deportivo Táchira", ["deportivo tachira"]),
            ("caracas", "Caracas", ["caracas", "caracas fc"]),
            ("zamora", "Zamora", ["zamora", "zamora fc"]),
            ("monagas", "Monagas", ["monagas", "monagas sc"]),
            ("mineros", "Mineros de Guayana", ["mineros de guayana", "mineros"]),
            ("trujillanos", "Trujillanos", ["trujillanos", "trujillanos ven"]),
            ("zulia", "Zulia", ["zulia", "zulia fc"]),
            ("deportivo-anzoategui", "Deportivo Anzoátegui", ["deportivo anzoategui"]),
            ("la-guaira", "Deportivo La Guaira", ["la guaira", "deportivo la guaira"]),
            ("pumas", "Pumas UNAM", ["pumas", "pumas unam"]),
            ("tigres", "Tigres UANL", ["tigres", "tigres uanl"]),
            ("toluca", "Toluca", ["toluca", "deportivo toluca"]),
            ("leon", "León", ["leon", "club leon"]),
            ("atlas", "Atlas", ["atlas", "atlas fc"]),
            ("tijuana", "Tijuana", ["tijuana", "club tijuana", "xolos"]),
            ("santos-laguna", "Santos Laguna", ["santos laguna"]),
            ("cruz-azul", "Cruz Azul", ["cruz azul"]),
            ("danubio", "Danubio", ["danubio", "danubio fc"]),
            ("defensor-sporting", "Defensor Sporting", ["defensor sporting", "defensor"]),
            ("montevideo-wanderers", "Montevideo Wanderers", ["montevideo wanderers"]),
            ("rentistas", "Rentistas", ["rentistas"]),
            ("fenix", "Fénix", ["fenix"]),
            ("colon", "Colón", ["colon", "colon santa fe"]),
            ("estudiantes-merida", "Estudiantes de Mérida", ["estudiantes de merida", "estudiantes merida"]),
        };

        DisplayNames = table.ToDictionary(t => t.Canon, t => t.Display, StringComparer.Ordinal);
        Aliases = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (canon, _, variants) in table)
        {
            foreach (var v in variants)
                Aliases.TryAdd(v, canon);
            Aliases.TryAdd(canon.Replace('-', ' '), canon);
        }
    }

    /// <summary>
    /// Returns the canonical identity slug for any team name found in the
    /// datasets (or for a user query).
    /// </summary>
    public static string CanonicalKey(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;

        var s = TeamNameNormalizer.NormalizeKeepState(name); // keeps trailing state token
        if (s.Length == 0) return s;

        // 1) exact alias on the full normalized form (handles "botafogo pb", "penarol am", ...)
        if (Aliases.TryGetValue(s, out var hit)) return hit;

        // 2) strip trailing state token, then alias again ("vasco da gama rj" -> "vasco da gama")
        var stripped = StripTrailingState(s);
        if (stripped != s && Aliases.TryGetValue(stripped, out hit)) return hit;

        // 3) multi-word legal forms ("sport club corinthians paulista")
        var loose = TeamNameNormalizer.LooseKey(name);
        if (loose.Length > 0 && loose != s && Aliases.TryGetValue(loose, out hit)) return hit;

        return stripped.Length > 0 ? stripped : s;
    }

    /// <summary>True when two names resolve to the same canonical identity.</summary>
    public static bool IsSameTeam(string? a, string? b)
    {
        var ka = CanonicalKey(a);
        var kb = CanonicalKey(b);
        return ka.Length > 0 && ka == kb;
    }

    /// <summary>Preferred display name for a canonical slug (falls back to the slug).</summary>
    public static string DisplayName(string canonicalKey) =>
        DisplayNames.TryGetValue(canonicalKey, out var d) ? d : canonicalKey;

    private static string StripTrailingState(string s)
    {
        var result = s;
        foreach (var uf in StateTokens)
        {
            if (result.Length > uf.Length + 1 &&
                result.EndsWith(uf, StringComparison.Ordinal) &&
                result[result.Length - uf.Length - 1] == ' ')
            {
                result = result[..^(uf.Length + 1)];
                break; // strip at most one token
            }
        }
        return result;
    }
}
