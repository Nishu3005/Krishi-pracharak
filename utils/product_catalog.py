PRODUCT_CATALOG = {
    "Tilt 250 EC": {
        "type": "fungicide",
        "target": "leaf rust, powdery mildew, brown rust",
        "crop_fit": ["wheat", "barley"],
        "application": "foliar spray at first sign of disease or preventively at tillering",
    },
    "Score 250 EC": {
        "type": "fungicide",
        "target": "scab, alternaria blight, white rust",
        "crop_fit": ["mustard", "potato"],
        "application": "foliar spray at flowering and pod formation stages",
    },
    "Amistar 250 SC": {
        "type": "fungicide",
        "target": "sheath blight, blast, powdery mildew",
        "crop_fit": ["wheat", "maize", "barley"],
        "application": "foliar spray, systemic action, protects for 2-3 weeks",
    },
    "Alto 5 SC": {
        "type": "fungicide",
        "target": "powdery mildew, rust, scab",
        "crop_fit": ["wheat", "chickpea", "barley"],
        "application": "foliar spray, curative and preventive action",
    },
    "Kavach 75 WP": {
        "type": "fungicide",
        "target": "early blight, late blight, downy mildew",
        "crop_fit": ["potato", "tomato"],
        "application": "foliar spray every 7-10 days during humid conditions",
    },
    "Actara 25 WG": {
        "type": "insecticide",
        "target": "aphids, whitefly, jassids, thrips",
        "crop_fit": ["chickpea", "mustard", "potato"],
        "application": "foliar spray or soil drench, systemic action",
    },
    "Cruiser 350 FS": {
        "type": "seed treatment",
        "target": "soil insects, wireworms, aphids in early seedling stage",
        "crop_fit": ["wheat", "maize", "barley"],
        "application": "seed treatment before sowing — coats every seed",
    },
    "Vibrance Integral": {
        "type": "seed treatment",
        "target": "seed-borne diseases, damping off, seedling blight",
        "crop_fit": ["wheat", "barley", "lentil"],
        "application": "seed treatment before sowing for full season protection",
    },
    "Axial 50 EC": {
        "type": "herbicide",
        "target": "grassy weeds including wild oat, canary grass, ryegrass",
        "crop_fit": ["wheat", "barley"],
        "application": "post-emergence spray at 2-4 leaf stage of weeds",
    },
    "Topik 15 WP": {
        "type": "herbicide",
        "target": "wild oat, grassy weeds",
        "crop_fit": ["wheat"],
        "application": "post-emergence spray at 2-3 leaf stage of weeds",
    },
    "Vertimec 1.8 EC": {
        "type": "acaricide/insecticide",
        "target": "spider mites, leafminers, thrips",
        "crop_fit": ["potato", "vegetables", "safflower"],
        "application": "foliar spray, targets larvae and adults on leaves",
    },
    "Movondo": {
        "type": "fungicide",
        "target": "downy mildew, anthracnose, leaf spot",
        "crop_fit": ["maize", "sorghum", "cumin"],
        "application": "foliar spray, protective action — apply before infection",
    },
}

CAMPAIGN_PRODUCT_MAP = {
    "wheat":    "Topik 15 WP",
    "mustard":  "Score 250 EC",
    "chickpea": "Actara 25 WG",
    "potato":   "Kavach 75 WP",
}


def get_product_context(sku_name: str) -> dict:
    return PRODUCT_CATALOG.get(sku_name, {
        "type": "crop protection",
        "target": "pests and diseases",
        "crop_fit": [],
        "application": "consult your local agronomist for guidance",
    })


def get_campaign_product(crop: str) -> str | None:
    return CAMPAIGN_PRODUCT_MAP.get(crop.lower())
