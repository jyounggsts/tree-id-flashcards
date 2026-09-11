"""
One-time data-migration script: adds the SoCal region to species.json.

1. Tags species already in the deck that also appear on the SoCal list
   (same species, just relevant to two regions) with region "socal" added
   to their existing region array, instead of duplicating them.
2. Adds every other named species from the SoCal source list as a new
   entry with region ["socal"].
3. Adds region: ["eastern-us"] to every pre-existing entry that didn't
   already get "socal" added.

Source: scientific-name index compiled from "A Californian's Guide to the
Trees Among Us" by Matt Ritter (user-supplied PDF). Only species explicitly
named with a specific epithet in that index are included — bare genus
mentions with no named species (e.g. "Rhus spp. -- sumac", "Taxus spp. --
yew") are skipped rather than guessing a specific species, and non-tree
entries (Cannabis sativa, Humulus lupulus, Ficus pumila as ground cover,
Ceanothus as a shrub genus) are excluded.

Run once: python scripts/build_socal.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECIES_PATH = ROOT / "data" / "species.json"

# Scientific names already in species.json that also appear on the SoCal
# list -- just add the region tag, don't duplicate.
SOCAL_OVERLAP = {
    "boxelder", "red-maple", "silver-maple", "sugar-maple", "river-birch",
    "hackberry", "eastern-redbud", "flowering-dogwood", "white-ash",
    "green-ash", "honey-locust", "sweetgum", "tulip-tree", "black-tupelo",
    "american-sycamore", "douglas-fir", "scarlet-oak", "bur-oak", "pin-oak",
    "northern-red-oak", "black-locust", "sassafras", "baldcypress",
    "american-basswood", "american-elm",
}

# New SoCal-only species. Fields match species.json's schema:
# id, common, scientific, family, group ("broadleaf" | "conifer" | "palm"),
# leafType, arrangement, search.
NEW_SPECIES = [
    # --- Acacia (Fabaceae) ---
    ("acacia-baileyana", "Bailey Acacia", "Acacia baileyana", "Fabaceae", "broadleaf", "compound (bipinnate)", "alternate"),
    ("acacia-cultriformis", "Knife-leaf Acacia", "Acacia cultriformis", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-cyclops", "Coastal Wattle", "Acacia cyclops", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-dealbata", "Silver Wattle", "Acacia dealbata", "Fabaceae", "broadleaf", "compound (bipinnate)", "alternate"),
    ("acacia-decurrens", "Green Wattle", "Acacia decurrens", "Fabaceae", "broadleaf", "compound (bipinnate)", "alternate"),
    ("acacia-longifolia", "Golden Wattle (Sydney)", "Acacia longifolia", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-mearnsii", "Black Wattle", "Acacia mearnsii", "Fabaceae", "broadleaf", "compound (bipinnate)", "alternate"),
    ("acacia-melanoxylon", "Blackwood Acacia", "Acacia melanoxylon", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-pendula", "Weeping Myall", "Acacia pendula", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-pycnantha", "Golden Wattle", "Acacia pycnantha", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-redolens", "Trailing Acacia", "Acacia redolens", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-retinodes", "Everblooming Acacia", "Acacia retinodes", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-saligna", "Blue-leaf Wattle", "Acacia saligna", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-stenophylla", "Shoestring Acacia", "Acacia stenophylla", "Fabaceae", "broadleaf", "simple (phyllode)", "alternate"),
    ("acacia-verticillata", "Star Acacia", "Acacia verticillata", "Fabaceae", "broadleaf", "simple (phyllode)", "whorled"),
    # --- Acer (Sapindaceae), non-overlapping ---
    ("acer-buergerianum", "Trident Maple", "Acer buergerianum", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-campestre", "Hedge Maple", "Acer campestre", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-macrophyllum", "Bigleaf Maple", "Acer macrophyllum", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-oblongum", "Evergreen Maple", "Acer oblongum", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-palmatum", "Japanese Maple", "Acer palmatum", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-paxii", "Evergreen Maple (Paxii)", "Acer paxii", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-platanoides", "Norway Maple", "Acer platanoides", "Sapindaceae", "broadleaf", "simple", "opposite"),
    ("acer-pseudoplatanus", "Sycamore Maple", "Acer pseudoplatanus", "Sapindaceae", "broadleaf", "simple", "opposite"),
    # --- Aesculus (Sapindaceae) ---
    ("aesculus-carnea", "Red Horsechestnut", "Aesculus × carnea", "Sapindaceae", "broadleaf", "compound (palmate)", "opposite"),
    ("aesculus-californica", "California Buckeye", "Aesculus californica", "Sapindaceae", "broadleaf", "compound (palmate)", "opposite"),
    ("aesculus-hippocastanum", "European Horsechestnut", "Aesculus hippocastanum", "Sapindaceae", "broadleaf", "compound (palmate)", "opposite"),
    ("aesculus-pavia", "Red Buckeye", "Aesculus pavia", "Sapindaceae", "broadleaf", "compound (palmate)", "opposite"),
    # --- misc A ---
    ("afrocarpus-falcatus", "African Fern Pine", "Afrocarpus falcatus", "Podocarpaceae", "conifer", "needle (flat)", "alternate"),
    ("agonis-flexuosa", "Australian Willow (Peppermint Willow)", "Agonis flexuosa", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("ailanthus-altissima", "Tree of Heaven", "Ailanthus altissima", "Simaroubaceae", "broadleaf", "compound", "alternate"),
    ("albizia-julibrissin", "Silk Tree (Mimosa)", "Albizia julibrissin", "Fabaceae", "broadleaf", "compound (bipinnate)", "alternate"),
    ("allocasuarina-verticillata", "Drooping Sheoak", "Allocasuarina verticillata", "Casuarinaceae", "broadleaf", "needle-like (jointed branchlets)", "whorled"),
    ("alnus-cordata", "Italian Alder", "Alnus cordata", "Betulaceae", "broadleaf", "simple", "alternate"),
    ("alnus-rhombifolia", "White Alder", "Alnus rhombifolia", "Betulaceae", "broadleaf", "simple", "alternate"),
    ("alnus-rubra", "Red Alder", "Alnus rubra", "Betulaceae", "broadleaf", "simple", "alternate"),
    ("angophora-costata", "Sydney Red Gum", "Angophora costata", "Myrtaceae", "broadleaf", "simple", "opposite"),
    ("araucaria-araucana", "Monkey Puzzle Tree", "Araucaria araucana", "Araucariaceae", "conifer", "needle (scale-like)", "spiral"),
    ("araucaria-bidwillii", "Bunya Bunya", "Araucaria bidwillii", "Araucariaceae", "conifer", "needle (broad)", "spiral"),
    ("araucaria-columnaris", "Cook Pine", "Araucaria columnaris", "Araucariaceae", "conifer", "needle (small, curved)", "spiral"),
    ("araucaria-cunninghamii", "Hoop Pine", "Araucaria cunninghamii", "Araucariaceae", "conifer", "needle", "spiral"),
    ("araucaria-heterophylla", "Norfolk Island Pine", "Araucaria heterophylla", "Araucariaceae", "conifer", "needle", "spiral"),
    ("arbutus-andrachne", "Grecian Strawberry Tree", "Arbutus andrachne", "Ericaceae", "broadleaf", "simple", "alternate"),
    ("arbutus-canariensis", "Canary Island Madrone", "Arbutus canariensis", "Ericaceae", "broadleaf", "simple", "alternate"),
    ("arbutus-menziesii", "Pacific Madrone", "Arbutus menziesii", "Ericaceae", "broadleaf", "simple", "alternate"),
    ("arbutus-unedo", "Strawberry Tree", "Arbutus unedo", "Ericaceae", "broadleaf", "simple", "alternate"),
    ("archontophoenix-alexandrae", "Alexandra Palm", "Archontophoenix alexandrae", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("archontophoenix-cunninghamiana", "King Palm", "Archontophoenix cunninghamiana", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    # --- B ---
    ("bauhinia-blakeana", "Hong Kong Orchid Tree", "Bauhinia × blakeana", "Fabaceae", "broadleaf", "simple (bilobed)", "alternate"),
    ("bauhinia-forficata", "Brazilian Orchid Tree", "Bauhinia forficata", "Fabaceae", "broadleaf", "simple (bilobed)", "alternate"),
    ("bauhinia-variegata", "Purple Orchid Tree", "Bauhinia variegata", "Fabaceae", "broadleaf", "simple (bilobed)", "alternate"),
    ("betula-pendula", "European White Birch", "Betula pendula", "Betulaceae", "broadleaf", "simple", "alternate"),
    ("brachychiton-acerifolius", "Illawarra Flame Tree", "Brachychiton acerifolius", "Malvaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("brachychiton-discolor", "Pink Flame Tree", "Brachychiton discolor", "Malvaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("brachychiton-populneus", "Bottle Tree (Kurrajong)", "Brachychiton populneus", "Malvaceae", "broadleaf", "simple", "alternate"),
    ("brachychiton-rupestris", "Queensland Bottle Tree", "Brachychiton rupestris", "Malvaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("brahea-armata", "Mexican Blue Palm", "Brahea armata", "Arecaceae", "palm", "frond (palmate)", "spiral"),
    ("brahea-edulis", "Guadalupe Palm", "Brahea edulis", "Arecaceae", "palm", "frond (palmate)", "spiral"),
    ("butia-capitata", "Pindo Palm (Jelly Palm)", "Butia capitata", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    # --- C ---
    ("callistemon-citrinus", "Lemon Bottlebrush", "Callistemon citrinus", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("callistemon-viminalis", "Weeping Bottlebrush", "Callistemon viminalis", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("calocedrus-decurrens", "Incense Cedar", "Calocedrus decurrens", "Cupressaceae", "conifer", "scale-like", "opposite"),
    ("calodendrum-capense", "Cape Chestnut", "Calodendrum capense", "Rutaceae", "broadleaf", "compound (palmate)", "opposite"),
    ("carpinus-betulus", "European Hornbeam", "Carpinus betulus", "Betulaceae", "broadleaf", "simple", "alternate"),
    ("carya-illinoinensis", "Pecan", "Carya illinoinensis", "Juglandaceae", "broadleaf", "compound", "alternate"),
    ("casuarina-cunninghamiana", "River Sheoak", "Casuarina cunninghamiana", "Casuarinaceae", "broadleaf", "needle-like (jointed branchlets)", "whorled"),
    ("casuarina-equisetifolia", "Horsetail Tree", "Casuarina equisetifolia", "Casuarinaceae", "broadleaf", "needle-like (jointed branchlets)", "whorled"),
    ("catalpa-bignonioides", "Southern Catalpa", "Catalpa bignonioides", "Bignoniaceae", "broadleaf", "simple", "whorled"),
    ("catalpa-speciosa", "Western Catalpa", "Catalpa speciosa", "Bignoniaceae", "broadleaf", "simple", "whorled"),
    ("chitalpa-tashkentensis", "Chitalpa", "×Chitalpa tashkentensis", "Bignoniaceae", "broadleaf", "simple", "opposite"),
    ("cedrela-sinensis", "Chinese Cedar (Chinese Toon)", "Cedrela sinensis", "Meliaceae", "broadleaf", "compound", "alternate"),
    ("cedrus-atlantica", "Atlas Cedar", "Cedrus atlantica", "Pinaceae", "conifer", "needle", "spiral"),
    ("cedrus-brevifolia", "Cyprus Cedar", "Cedrus brevifolia", "Pinaceae", "conifer", "needle", "spiral"),
    ("cedrus-deodara", "Deodar Cedar", "Cedrus deodara", "Pinaceae", "conifer", "needle", "spiral"),
    ("cedrus-libani", "Cedar of Lebanon", "Cedrus libani", "Pinaceae", "conifer", "needle", "spiral"),
    ("ceiba-speciosa", "Floss Silk Tree", "Ceiba speciosa", "Malvaceae", "broadleaf", "compound (palmate)", "alternate"),
    ("celtis-australis", "European Hackberry", "Celtis australis", "Cannabaceae", "broadleaf", "simple", "alternate"),
    ("celtis-laevigata", "Sugarberry", "Celtis laevigata", "Cannabaceae", "broadleaf", "simple", "alternate"),
    ("celtis-sinensis", "Chinese Hackberry", "Celtis sinensis", "Cannabaceae", "broadleaf", "simple", "alternate"),
    ("ceratonia-siliqua", "Carob Tree", "Ceratonia siliqua", "Fabaceae", "broadleaf", "compound", "alternate"),
    ("cercidiphyllum-japonicum", "Katsura Tree", "Cercidiphyllum japonicum", "Cercidiphyllaceae", "broadleaf", "simple", "opposite"),
    ("cercis-occidentalis", "California Redbud", "Cercis occidentalis", "Fabaceae", "broadleaf", "simple", "alternate"),
    ("cercis-siliquastrum", "Judas Tree", "Cercis siliquastrum", "Fabaceae", "broadleaf", "simple", "alternate"),
    ("chamaecyparis-lawsoniana", "Port Orford Cedar", "Chamaecyparis lawsoniana", "Cupressaceae", "conifer", "scale-like", "opposite"),
    ("chamaerops-humilis", "Mediterranean Fan Palm", "Chamaerops humilis", "Arecaceae", "palm", "frond (palmate)", "spiral"),
    ("chilopsis-linearis", "Desert Willow", "Chilopsis linearis", "Bignoniaceae", "broadleaf", "simple", "opposite"),
    ("chionanthus-retusus", "Chinese Fringe Tree", "Chionanthus retusus", "Oleaceae", "broadleaf", "simple", "opposite"),
    ("chionanthus-virginicus", "White Fringe Tree", "Chionanthus virginicus", "Oleaceae", "broadleaf", "simple", "opposite"),
    ("chiranthodendron-pentadactylon", "Monkey Hand Tree", "Chiranthodendron pentadactylon", "Malvaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("cinnamomum-camphora", "Camphor Tree", "Cinnamomum camphora", "Lauraceae", "broadleaf", "simple", "alternate"),
    ("cordyline-australis", "Cabbage Tree", "Cordyline australis", "Asparagaceae", "palm", "sword-shaped leaves", "spiral"),
    ("cornus-capitata", "Evergreen Dogwood", "Cornus capitata", "Cornaceae", "broadleaf", "simple", "opposite"),
    ("cornus-kousa", "Kousa Dogwood", "Cornus kousa", "Cornaceae", "broadleaf", "simple", "opposite"),
    ("cornus-mas", "Cornelian Cherry", "Cornus mas", "Cornaceae", "broadleaf", "simple", "opposite"),
    ("cornus-nuttallii", "Pacific Dogwood", "Cornus nuttallii", "Cornaceae", "broadleaf", "simple", "opposite"),
    ("corymbia-calophylla", "Marri", "Corymbia calophylla", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("corymbia-citriodora", "Lemon-scented Gum", "Corymbia citriodora", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("corymbia-ficifolia", "Red-flowering Gum", "Corymbia ficifolia", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("crataegus-lavallei", "Lavalle Hawthorn", "Crataegus × lavallei", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("crataegus-laevigata", "English Hawthorn", "Crataegus laevigata", "Rosaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("crataegus-phaenopyrum", "Washington Hawthorn", "Crataegus phaenopyrum", "Rosaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("crinodendron-patagua", "Lily-of-the-Valley Tree", "Crinodendron patagua", "Elaeocarpaceae", "broadleaf", "simple", "opposite"),
    ("cryptomeria-japonica", "Japanese Cedar (Sugi)", "Cryptomeria japonica", "Cupressaceae", "conifer", "needle (awl-like)", "spiral"),
    ("cupaniopsis-anacardioides", "Carrotwood", "Cupaniopsis anacardioides", "Sapindaceae", "broadleaf", "compound", "alternate"),
    # --- D-F ---
    ("dodonaea-viscosa", "Hopseed Bush", "Dodonaea viscosa", "Sapindaceae", "broadleaf", "simple", "alternate"),
    ("dracaena-draco", "Dragon Tree", "Dracaena draco", "Asparagaceae", "palm", "sword-shaped leaves", "spiral"),
    ("elaeagnus-angustifolia", "Russian Olive", "Elaeagnus angustifolia", "Elaeagnaceae", "broadleaf", "simple", "alternate"),
    ("elaeis-guineensis", "African Oil Palm", "Elaeis guineensis", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("eriobotrya-deflexa", "Bronze Loquat", "Eriobotrya deflexa", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("eriobotrya-japonica", "Loquat", "Eriobotrya japonica", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("erythrina-bidwillii", "Bidwill's Coral Tree", "Erythrina × bidwillii", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-caffra", "Coast Coral Tree", "Erythrina caffra", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-coralloides", "Naked Coral Tree", "Erythrina coralloides", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-crista-galli", "Cockspur Coral Tree", "Erythrina crista-galli", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-falcata", "Brazilian Coral Tree", "Erythrina falcata", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-humeana", "Dwarf Coral Tree", "Erythrina humeana", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-latissima", "Broad-leaved Coral Tree", "Erythrina latissima", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-lysistemon", "Common Coral Tree", "Erythrina lysistemon", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-speciosa", "Brazilian Fireman's Cap", "Erythrina speciosa", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("erythrina-sykesii", "Sykes' Coral Tree", "Erythrina × sykesii", "Fabaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("eucalyptus-camaldulensis", "River Red Gum", "Eucalyptus camaldulensis", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-cinerea", "Silver Dollar Gum (Argyle Apple)", "Eucalyptus cinerea", "Myrtaceae", "broadleaf", "simple", "opposite (juvenile)"),
    ("eucalyptus-cladocalyx", "Sugar Gum", "Eucalyptus cladocalyx", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-conferruminata", "Bushy Yate", "Eucalyptus conferruminata", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-globulus", "Blue Gum", "Eucalyptus globulus", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-grandis", "Rose Gum", "Eucalyptus grandis", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-gunnii", "Cider Gum", "Eucalyptus gunnii", "Myrtaceae", "broadleaf", "simple", "opposite (juvenile)"),
    ("eucalyptus-leucoxylon", "White Ironbark", "Eucalyptus leucoxylon", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-nicholii", "Narrow-leaved Black Peppermint", "Eucalyptus nicholii", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-polyanthemos", "Silver Dollar Gum (Red Box)", "Eucalyptus polyanthemos", "Myrtaceae", "broadleaf", "simple", "opposite (juvenile)"),
    ("eucalyptus-pulverulenta", "Silver-leaved Mountain Gum", "Eucalyptus pulverulenta", "Myrtaceae", "broadleaf", "simple", "opposite"),
    ("eucalyptus-robusta", "Swamp Mahogany", "Eucalyptus robusta", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-rudis", "Flooded Gum", "Eucalyptus rudis", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-saligna", "Sydney Blue Gum", "Eucalyptus saligna", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-sideroxylon", "Red Ironbark", "Eucalyptus sideroxylon", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-tereticornis", "Forest Red Gum", "Eucalyptus tereticornis", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-torquata", "Coral Gum", "Eucalyptus torquata", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("eucalyptus-viminalis", "Manna Gum", "Eucalyptus viminalis", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("euterpe-oleracea", "Açaí Palm", "Euterpe oleracea", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("fagus-sylvatica", "European Beech", "Fagus sylvatica", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("feijoa-sellowiana", "Pineapple Guava", "Feijoa sellowiana", "Myrtaceae", "broadleaf", "simple", "opposite"),
    ("ficus-auriculata", "Roxburgh Fig", "Ficus auriculata", "Moraceae", "broadleaf", "simple", "alternate"),
    ("ficus-benjamina", "Weeping Fig", "Ficus benjamina", "Moraceae", "broadleaf", "simple", "alternate"),
    ("ficus-carica", "Common Fig", "Ficus carica", "Moraceae", "broadleaf", "simple (lobed)", "alternate"),
    ("ficus-elastica", "Rubber Tree", "Ficus elastica", "Moraceae", "broadleaf", "simple", "alternate"),
    ("ficus-macrophylla", "Moreton Bay Fig", "Ficus macrophylla", "Moraceae", "broadleaf", "simple", "alternate"),
    ("ficus-microcarpa", "Indian Laurel Fig", "Ficus microcarpa", "Moraceae", "broadleaf", "simple", "alternate"),
    ("ficus-rubiginosa", "Rusty Fig (Port Jackson Fig)", "Ficus rubiginosa", "Moraceae", "broadleaf", "simple", "alternate"),
    ("firmiana-simplex", "Chinese Parasol Tree", "Firmiana simplex", "Malvaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("fraxinus-angustifolia", "Narrow-leaved Ash (Raywood)", "Fraxinus angustifolia", "Oleaceae", "broadleaf", "compound", "opposite"),
    ("fraxinus-holotricha", "Moraine Ash", "Fraxinus holotricha", "Oleaceae", "broadleaf", "compound", "opposite"),
    ("fraxinus-latifolia", "Oregon Ash", "Fraxinus latifolia", "Oleaceae", "broadleaf", "compound", "opposite"),
    ("fraxinus-uhdei", "Shamel Ash", "Fraxinus uhdei", "Oleaceae", "broadleaf", "compound", "opposite"),
    ("fraxinus-velutina", "Velvet Ash (Modesto Ash)", "Fraxinus velutina", "Oleaceae", "broadleaf", "compound", "opposite"),
    ("fraxinus-ornus", "Flowering Ash (Manna Ash)", "Fraxinus ornus", "Oleaceae", "broadleaf", "compound", "opposite"),
    # --- G-H ---
    ("geijera-parviflora", "Australian Willow", "Geijera parviflora", "Rutaceae", "broadleaf", "simple", "alternate"),
    ("ginkgo-biloba", "Ginkgo (Maidenhair Tree)", "Ginkgo biloba", "Ginkgoaceae", "broadleaf", "simple (fan-shaped)", "alternate (spurred)"),
    ("grevillea-robusta", "Silk Oak", "Grevillea robusta", "Proteaceae", "broadleaf", "compound (fern-like)", "alternate"),
    ("handroanthus-chrysotrichus", "Golden Trumpet Tree", "Handroanthus chrysotrichus", "Bignoniaceae", "broadleaf", "compound (palmate)", "opposite"),
    ("harpephyllum-caffrum", "Wild Plum (Kaffir Plum)", "Harpephyllum caffrum", "Anacardiaceae", "broadleaf", "compound", "alternate"),
    ("hesperocyparis-macrocarpa", "Monterey Cypress", "Hesperocyparis macrocarpa", "Cupressaceae", "conifer", "scale-like", "opposite"),
    ("hesperotropsis-leylandii", "Leyland Cypress", "×Hesperotropsis leylandii", "Cupressaceae", "conifer", "scale-like", "opposite"),
    ("heteromeles-arbutifolia", "Toyon (California Holly)", "Heteromeles arbutifolia", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("hymenosporum-flavum", "Sweetshade", "Hymenosporum flavum", "Pittosporaceae", "broadleaf", "simple", "alternate"),
    # --- I-L ---
    ("jacaranda-mimosifolia", "Jacaranda", "Jacaranda mimosifolia", "Bignoniaceae", "broadleaf", "compound (bipinnate)", "opposite"),
    ("koelreuteria-bipinnata", "Chinese Flame Tree", "Koelreuteria bipinnata", "Sapindaceae", "broadleaf", "compound (bipinnate)", "alternate"),
    ("koelreuteria-elegans", "Flamegold Tree", "Koelreuteria elegans", "Sapindaceae", "broadleaf", "compound", "alternate"),
    ("koelreuteria-paniculata", "Goldenrain Tree", "Koelreuteria paniculata", "Sapindaceae", "broadleaf", "compound", "alternate"),
    ("lagerstroemia-fauriei", "Japanese Crape Myrtle", "Lagerstroemia fauriei", "Lythraceae", "broadleaf", "simple", "opposite"),
    ("lagerstroemia-indica", "Crape Myrtle", "Lagerstroemia indica", "Lythraceae", "broadleaf", "simple", "opposite"),
    ("lagunaria-patersonia", "Norfolk Island Hibiscus", "Lagunaria patersonia", "Malvaceae", "broadleaf", "simple", "alternate"),
    ("laurus-nobilis", "Bay Laurel (Grecian Laurel)", "Laurus nobilis", "Lauraceae", "broadleaf", "simple", "alternate"),
    ("leptospermum-laevigatum", "Australian Tea Tree", "Leptospermum laevigatum", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("ligustrum-japonicum", "Japanese Privet", "Ligustrum japonicum", "Oleaceae", "broadleaf", "simple", "opposite"),
    ("lophostemon-confertus", "Brisbane Box", "Lophostemon confertus", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("lyonothamnus-floribundus", "Catalina Ironwood", "Lyonothamnus floribundus", "Rosaceae", "broadleaf", "compound", "opposite"),
    # --- M ---
    ("macadamia-integrifolia", "Macadamia", "Macadamia integrifolia", "Proteaceae", "broadleaf", "simple", "whorled"),
    ("magnolia-denudata", "Lily Magnolia (Yulan)", "Magnolia denudata", "Magnoliaceae", "broadleaf", "simple", "alternate"),
    ("magnolia-grandiflora", "Southern Magnolia", "Magnolia grandiflora", "Magnoliaceae", "broadleaf", "simple", "alternate"),
    ("magnolia-soulangeana", "Saucer Magnolia", "Magnolia × soulangeana", "Magnoliaceae", "broadleaf", "simple", "alternate"),
    ("magnolia-liliiflora", "Mulan Magnolia", "Magnolia liliiflora", "Magnoliaceae", "broadleaf", "simple", "alternate"),
    ("malus-floribunda", "Japanese Flowering Crabapple", "Malus floribunda", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("mangifera-indica", "Mango", "Mangifera indica", "Anacardiaceae", "broadleaf", "simple", "alternate"),
    ("markhamia-lutea", "Nile Tulip Tree", "Markhamia lutea", "Bignoniaceae", "broadleaf", "compound", "opposite"),
    ("maytenus-boaria", "Mayten Tree", "Maytenus boaria", "Celastraceae", "broadleaf", "simple", "alternate"),
    ("melaleuca-armillaris", "Bracelet Honey Myrtle", "Melaleuca armillaris", "Myrtaceae", "broadleaf", "simple (needle-like)", "alternate"),
    ("melaleuca-ericifolia", "Heath Melaleuca", "Melaleuca ericifolia", "Myrtaceae", "broadleaf", "simple (needle-like)", "alternate"),
    ("melaleuca-linariifolia", "Flaxleaf Paperbark", "Melaleuca linariifolia", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("melaleuca-nesophila", "Pink Melaleuca", "Melaleuca nesophila", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("melaleuca-quinquenervia", "Cajeput Tree (Punk Tree)", "Melaleuca quinquenervia", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("melaleuca-styphelioides", "Prickly-leaved Paperbark", "Melaleuca styphelioides", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("melia-azedarach", "Chinaberry (Bead Tree)", "Melia azedarach", "Meliaceae", "broadleaf", "compound", "alternate"),
    ("metasequoia-glyptostroboides", "Dawn Redwood", "Metasequoia glyptostroboides", "Cupressaceae", "conifer", "needle (deciduous)", "opposite"),
    ("metrosideros-excelsa", "New Zealand Christmas Tree", "Metrosideros excelsa", "Myrtaceae", "broadleaf", "simple", "opposite"),
    ("michelia-doltsopa", "Sweet Michelia", "Michelia doltsopa", "Magnoliaceae", "broadleaf", "simple", "alternate"),
    ("morus-alba", "White Mulberry", "Morus alba", "Moraceae", "broadleaf", "simple", "alternate"),
    ("morus-nigra", "Black Mulberry", "Morus nigra", "Moraceae", "broadleaf", "simple", "alternate"),
    ("myoporum-laetum", "Myoporum (Ngaio Tree)", "Myoporum laetum", "Scrophulariaceae", "broadleaf", "simple", "alternate"),
    # --- N-P ---
    ("nerium-oleander", "Oleander", "Nerium oleander", "Apocynaceae", "broadleaf", "simple", "whorled"),
    ("nolina-recurvata", "Ponytail Palm", "Nolina recurvata", "Asparagaceae", "palm", "sword-shaped leaves", "spiral"),
    ("olea-europaea", "Olive", "Olea europaea", "Oleaceae", "broadleaf", "simple", "opposite"),
    ("parkinsonia-aculeata", "Mexican Palo Verde", "Parkinsonia aculeata", "Fabaceae", "broadleaf", "compound", "alternate"),
    ("parkinsonia-florida", "Blue Palo Verde", "Parkinsonia florida", "Fabaceae", "broadleaf", "compound", "alternate"),
    ("parkinsonia-microphylla", "Foothill Palo Verde", "Parkinsonia microphylla", "Fabaceae", "broadleaf", "compound", "alternate"),
    ("parrotia-persica", "Persian Ironwood", "Parrotia persica", "Hamamelidaceae", "broadleaf", "simple", "alternate"),
    ("paulownia-tomentosa", "Empress Tree (Princess Tree)", "Paulownia tomentosa", "Paulowniaceae", "broadleaf", "simple", "opposite"),
    ("persea-americana", "Avocado", "Persea americana", "Lauraceae", "broadleaf", "simple", "alternate"),
    ("phoenix-canariensis", "Canary Island Date Palm", "Phoenix canariensis", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("phoenix-dactylifera", "Date Palm", "Phoenix dactylifera", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("phoenix-reclinata", "Senegal Date Palm", "Phoenix reclinata", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("phoenix-roebelenii", "Pygmy Date Palm", "Phoenix roebelenii", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("photinia-serrulata", "Chinese Photinia", "Photinia serrulata", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("pinus-canariensis", "Canary Island Pine", "Pinus canariensis", "Pinaceae", "conifer", "needle (3 per bundle)", "spiral"),
    ("pinus-eldarica", "Afghan Pine (Mondell)", "Pinus eldarica", "Pinaceae", "conifer", "needle (3 per bundle)", "spiral"),
    ("pinus-halepensis", "Aleppo Pine", "Pinus halepensis", "Pinaceae", "conifer", "needle (2 per bundle)", "spiral"),
    ("pinus-mugo", "Mugo Pine", "Pinus mugo", "Pinaceae", "conifer", "needle (2 per bundle)", "spiral"),
    ("pinus-nigra", "Austrian Pine", "Pinus nigra", "Pinaceae", "conifer", "needle (2 per bundle)", "spiral"),
    ("pinus-patula", "Jelecote Pine", "Pinus patula", "Pinaceae", "conifer", "needle (3-4 per bundle)", "spiral"),
    ("pinus-pinea", "Italian Stone Pine", "Pinus pinea", "Pinaceae", "conifer", "needle (2 per bundle)", "spiral"),
    ("pinus-ponderosa", "Ponderosa Pine", "Pinus ponderosa", "Pinaceae", "conifer", "needle (3 per bundle)", "spiral"),
    ("pinus-radiata", "Monterey Pine", "Pinus radiata", "Pinaceae", "conifer", "needle (3 per bundle)", "spiral"),
    ("pinus-thunbergii", "Japanese Black Pine", "Pinus thunbergii", "Pinaceae", "conifer", "needle (2 per bundle)", "spiral"),
    ("pinus-torreyana", "Torrey Pine", "Pinus torreyana", "Pinaceae", "conifer", "needle (5 per bundle)", "spiral"),
    ("pistacia-chinensis", "Chinese Pistache", "Pistacia chinensis", "Anacardiaceae", "broadleaf", "compound", "alternate"),
    ("pistacia-vera", "Pistachio", "Pistacia vera", "Anacardiaceae", "broadleaf", "compound", "alternate"),
    ("pittosporum-angustifolium", "Weeping Pittosporum", "Pittosporum angustifolium", "Pittosporaceae", "broadleaf", "simple", "alternate"),
    ("pittosporum-crassifolium", "Karo", "Pittosporum crassifolium", "Pittosporaceae", "broadleaf", "simple", "alternate"),
    ("pittosporum-eugenioides", "Tarata (Lemonwood)", "Pittosporum eugenioides", "Pittosporaceae", "broadleaf", "simple", "alternate"),
    ("pittosporum-rhombifolium", "Diamond-leaf Pittosporum", "Pittosporum rhombifolium", "Pittosporaceae", "broadleaf", "simple", "alternate"),
    ("pittosporum-tenuifolium", "Kohuhu", "Pittosporum tenuifolium", "Pittosporaceae", "broadleaf", "simple", "alternate"),
    ("pittosporum-tobira", "Japanese Mock Orange", "Pittosporum tobira", "Pittosporaceae", "broadleaf", "simple", "whorled"),
    ("platanus-acerifolia", "London Plane", "Platanus × acerifolia", "Platanaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("platanus-mexicana", "Mexican Sycamore", "Platanus mexicana", "Platanaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("platanus-racemosa", "California Sycamore", "Platanus racemosa", "Platanaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("podocarpus-macrophyllus", "Yew Pine (Buddhist Pine)", "Podocarpus macrophyllus", "Podocarpaceae", "conifer", "needle (flat)", "alternate"),
    ("populus-nigra-italica", "Lombardy Poplar", "Populus nigra", "Salicaceae", "broadleaf", "simple", "alternate"),
    ("prunus-campanulata", "Taiwan Flowering Cherry", "Prunus campanulata", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("prunus-caroliniana", "Carolina Laurel Cherry", "Prunus caroliniana", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("prunus-cerasifera", "Purple-leaf Plum", "Prunus cerasifera", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("prunus-ilicifolia", "Hollyleaf Cherry", "Prunus ilicifolia", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("prunus-laurocerasus", "English Laurel", "Prunus laurocerasus", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("prunus-lusitanica", "Portugal Laurel", "Prunus lusitanica", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("prunus-serrulata", "Japanese Flowering Cherry", "Prunus serrulata", "Rosaceae", "broadleaf", "simple", "alternate"),
    ("pyrus-calleryana", "Callery Pear (Bradford Pear)", "Pyrus calleryana", "Rosaceae", "broadleaf", "simple", "alternate"),
    # --- Q-R ---
    ("quercus-agrifolia", "Coast Live Oak", "Quercus agrifolia", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-chrysolepis", "Canyon Live Oak", "Quercus chrysolepis", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-douglasii", "Blue Oak", "Quercus douglasii", "Fagaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("quercus-engelmannii", "Engelmann Oak", "Quercus engelmannii", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-garryana", "Oregon White Oak", "Quercus garryana", "Fagaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("quercus-hypoleucoides", "Silverleaf Oak", "Quercus hypoleucoides", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-ilex", "Holm Oak", "Quercus ilex", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-kelloggii", "California Black Oak", "Quercus kelloggii", "Fagaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("quercus-lobata", "Valley Oak", "Quercus lobata", "Fagaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("quercus-parvula-shrevei", "Shreve Oak", "Quercus parvula var. shrevei", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-robur", "English Oak", "Quercus robur", "Fagaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("quercus-suber", "Cork Oak", "Quercus suber", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-tomentella", "Island Oak", "Quercus tomentella", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-virginiana", "Southern Live Oak", "Quercus virginiana", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("quercus-wislizeni", "Interior Live Oak", "Quercus wislizeni", "Fagaceae", "broadleaf", "simple", "alternate"),
    ("robinia-ambigua", "Idaho Locust", "Robinia × ambigua", "Fabaceae", "broadleaf", "compound", "alternate"),
    # --- S ---
    ("schefflera-actinophylla", "Umbrella Tree (Octopus Tree)", "Schefflera actinophylla", "Araliaceae", "broadleaf", "compound (palmate)", "alternate"),
    ("schinus-molle", "California Pepper Tree", "Schinus molle", "Anacardiaceae", "broadleaf", "compound", "alternate"),
    ("schinus-terebinthifolius", "Brazilian Pepper Tree", "Schinus terebinthifolius", "Anacardiaceae", "broadleaf", "compound", "alternate"),
    ("schinus-polygamus", "Huingan (Southern Peppertree)", "Schinus polygamus", "Anacardiaceae", "broadleaf", "simple", "alternate"),
    ("sclerocarya-birrea", "Marula", "Sclerocarya birrea", "Anacardiaceae", "broadleaf", "compound", "alternate"),
    ("sequoia-sempervirens", "Coast Redwood", "Sequoia sempervirens", "Cupressaceae", "conifer", "needle (flat, 2-ranked)", "spiral"),
    ("sequoiadendron-giganteum", "Giant Sequoia", "Sequoiadendron giganteum", "Cupressaceae", "conifer", "needle (awl-like)", "spiral"),
    ("styphnolobium-japonicum", "Japanese Pagoda Tree", "Styphnolobium japonicum", "Fabaceae", "broadleaf", "compound", "alternate"),
    ("spathodea-campanulata", "African Tulip Tree", "Spathodea campanulata", "Bignoniaceae", "broadleaf", "compound", "opposite"),
    ("stenocarpus-sinuatus", "Firewheel Tree", "Stenocarpus sinuatus", "Proteaceae", "broadleaf", "simple (lobed)", "alternate"),
    ("syagrus-romanzoffiana", "Queen Palm", "Syagrus romanzoffiana", "Arecaceae", "palm", "frond (pinnate)", "spiral"),
    ("syzygium-australe", "Brush Cherry", "Syzygium australe", "Myrtaceae", "broadleaf", "simple", "opposite"),
    ("syzygium-paniculatum", "Australian Brush Cherry", "Syzygium paniculatum", "Myrtaceae", "broadleaf", "simple", "opposite"),
    # --- T-V ---
    ("tamarix-aphylla", "Athel Tree (Tamarisk)", "Tamarix aphylla", "Tamaricaceae", "broadleaf", "scale-like (needle-like)", "alternate"),
    ("thuja-plicata", "Western Red Cedar", "Thuja plicata", "Cupressaceae", "conifer", "scale-like", "opposite"),
    ("tilia-cordata", "Littleleaf Linden", "Tilia cordata", "Malvaceae", "broadleaf", "simple", "alternate"),
    ("tilia-platyphyllos", "Bigleaf Linden", "Tilia platyphyllos", "Malvaceae", "broadleaf", "simple", "alternate"),
    ("tilia-tomentosa", "Silver Linden", "Tilia tomentosa", "Malvaceae", "broadleaf", "simple", "alternate"),
    ("toxicodendron-diversilobum", "Pacific Poison Oak", "Toxicodendron diversilobum", "Anacardiaceae", "broadleaf", "compound (trifoliate)", "alternate"),
    ("trachycarpus-fortunei", "Chinese Windmill Palm", "Trachycarpus fortunei", "Arecaceae", "palm", "frond (palmate)", "spiral"),
    ("triadica-sebifera", "Chinese Tallow Tree", "Triadica sebifera", "Euphorbiaceae", "broadleaf", "simple", "alternate"),
    ("tristaniopsis-laurina", "Water Gum (Swamp Myrtle)", "Tristaniopsis laurina", "Myrtaceae", "broadleaf", "simple", "alternate"),
    ("ulmus-glabra", "Scotch Elm (Wych Elm)", "Ulmus glabra", "Ulmaceae", "broadleaf", "simple", "alternate"),
    ("ulmus-minor", "Field Elm", "Ulmus minor", "Ulmaceae", "broadleaf", "simple", "alternate"),
    ("ulmus-hollandica", "Dutch Elm", "Ulmus × hollandica", "Ulmaceae", "broadleaf", "simple", "alternate"),
    ("ulmus-parvifolia", "Chinese Elm (Lacebark Elm)", "Ulmus parvifolia", "Ulmaceae", "broadleaf", "simple", "alternate"),
    ("ulmus-procera", "English Elm", "Ulmus procera", "Ulmaceae", "broadleaf", "simple", "alternate"),
    ("ulmus-pumila", "Siberian Elm", "Ulmus pumila", "Ulmaceae", "broadleaf", "simple", "alternate"),
    ("umbellularia-californica", "California Bay Laurel", "Umbellularia californica", "Lauraceae", "broadleaf", "simple", "alternate"),
    ("vitex-lucens", "New Zealand Chaste Tree (Puriri)", "Vitex lucens", "Lamiaceae", "broadleaf", "compound (palmate)", "opposite"),
    # --- W-Z ---
    ("washingtonia-filifera", "California Fan Palm", "Washingtonia filifera", "Arecaceae", "palm", "frond (palmate)", "spiral"),
    ("washingtonia-robusta", "Mexican Fan Palm", "Washingtonia robusta", "Arecaceae", "palm", "frond (palmate)", "spiral"),
    ("wollemia-nobilis", "Wollemi Pine", "Wollemia nobilis", "Araucariaceae", "conifer", "needle (flat, 2-ranked)", "spiral"),
    ("xylosma-congestum", "Shiny Xylosma", "Xylosma congestum", "Salicaceae", "broadleaf", "simple", "alternate"),
    ("yucca-brevifolia", "Joshua Tree", "Yucca brevifolia", "Asparagaceae", "palm", "sword-shaped leaves", "spiral"),
    ("yucca-elephantipes", "Giant Yucca", "Yucca elephantipes", "Asparagaceae", "palm", "sword-shaped leaves", "spiral"),
    ("zelkova-serrata", "Japanese Zelkova", "Zelkova serrata", "Ulmaceae", "broadleaf", "simple", "alternate"),
]


def main():
    species = json.loads(SPECIES_PATH.read_text(encoding="utf-8"))
    existing_ids = {s["id"] for s in species}

    for sp in species:
        sp.setdefault("region", [])
        if sp["id"] in SOCAL_OVERLAP:
            if "socal" not in sp["region"]:
                sp["region"].append("socal")
        if "eastern-us" not in sp["region"]:
            sp["region"].insert(0, "eastern-us")

    added = 0
    for sid, common, scientific, family, group, leaf_type, arrangement in NEW_SPECIES:
        if sid in existing_ids:
            print(f"[skip] duplicate id {sid}")
            continue
        species.append({
            "id": sid,
            "common": common,
            "scientific": scientific,
            "family": family,
            "group": group,
            "leafType": leaf_type,
            "arrangement": arrangement,
            "search": f"{scientific} leaf" if group != "conifer" else f"{scientific} needles",
            "region": ["socal"],
        })
        added += 1

    SPECIES_PATH.write_text(json.dumps(species, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added {added} new SoCal species. Total species now: {len(species)}")


if __name__ == "__main__":
    main()
