"""
scripts/seed_nutrition.py — Seed all 9 nutritional guides from the spec.

Run with:
    cd backend
    flask shell -c "from scripts.seed_nutrition import seed; seed()"
  OR
    python -m scripts.seed_nutrition
"""

from __future__ import annotations

GUIDES = [
    # ── Dogs ──────────────────────────────────────────────────────────────────
    {
        "species": "dog", "category": "puppy",
        "title": "Puppy Nutrition Guide (0–12 months)",
        "description": "Growing puppies need energy-dense food for rapid development.",
        "protein_min": 22, "protein_max": 28,
        "fat_min": 8, "fat_max": 12,
        "fiber_min": 3, "fiber_max": 5,
        "moisture_min": 10, "moisture_max": 15,
        "calories_min_per_day": 200, "calories_max_per_day": 600,
        "meals_per_day": 4,
        "serving_size_description": "½ to 2 cups per meal depending on breed size",
        "water_needs": "Fresh water available at all times",
        "recommended_foods": ["High-quality puppy kibble", "Wet puppy food", "Raw diet (BARF)", "Boiled chicken & rice"],
        "forbidden_foods": [
            {"food": "Chocolate", "reason": "Contains theobromine — toxic to dogs"},
            {"food": "Grapes & Raisins", "reason": "Can cause acute kidney failure"},
            {"food": "Onions & Garlic", "reason": "Destroy red blood cells"},
            {"food": "Xylitol", "reason": "Causes dangerous insulin spike"},
        ],
        "health_notes": ["DHA for brain & eye development", "Calcium-phosphorus balance crucial for bones", "Avoid adult food — insufficient nutrients for growth"],
        "display_config": {"primary_color": "#FF8C42", "accent_color": "#FFF3E0", "icon": "dog-puppy"},
    },
    {
        "species": "dog", "category": "adult",
        "title": "Adult Dog Nutrition Guide (1–7 years)",
        "description": "Balanced nutrition to maintain healthy weight, coat, and energy.",
        "protein_min": 18, "protein_max": 25,
        "fat_min": 5, "fat_max": 8,
        "fiber_min": 3, "fiber_max": 6,
        "moisture_min": 10, "moisture_max": 15,
        "calories_min_per_day": 400, "calories_max_per_day": 1200,
        "meals_per_day": 2,
        "serving_size_description": "1 to 3 cups per meal depending on size and activity",
        "water_needs": "Fresh water always available",
        "recommended_foods": ["Balanced adult kibble", "Wet food", "Homemade balanced diet", "Raw diet"],
        "forbidden_foods": [
            {"food": "Chocolate", "reason": "Theobromine toxicity"},
            {"food": "Grapes & Raisins", "reason": "Kidney failure risk"},
            {"food": "Onions & Garlic", "reason": "Haemolytic anaemia"},
            {"food": "Xylitol", "reason": "Hypoglycaemia"},
            {"food": "Macadamia Nuts", "reason": "Neurological symptoms"},
        ],
        "health_notes": ["Monitor weight regularly", "Joint supplements for large breeds", "Dental chews for oral health"],
        "display_config": {"primary_color": "#E85D04", "accent_color": "#FEF3C7", "icon": "dog-adult"},
    },
    {
        "species": "dog", "category": "senior",
        "title": "Senior Dog Nutrition Guide (7+ years)",
        "description": "Easily digestible, lower-calorie food supporting joints and kidney health.",
        "protein_min": 20, "protein_max": 28,
        "fat_min": 4, "fat_max": 7,
        "fiber_min": 4, "fiber_max": 7,
        "moisture_min": 12, "moisture_max": 18,
        "calories_min_per_day": 300, "calories_max_per_day": 800,
        "meals_per_day": 2,
        "serving_size_description": "¾ to 2 cups per meal",
        "water_needs": "Increased hydration important — consider wet food",
        "recommended_foods": ["Senior formula kibble", "Wet food (easier to chew)", "Easily digestible proteins", "Omega-3 supplements"],
        "forbidden_foods": [
            {"food": "Chocolate", "reason": "Theobromine toxicity"},
            {"food": "High-sodium foods", "reason": "Worsens heart and kidney disease"},
            {"food": "Grapes & Raisins", "reason": "Kidney failure risk"},
        ],
        "health_notes": ["Lower phosphorus to protect kidneys", "Glucosamine & chondroitin for joints", "Regular vet check-ups every 6 months", "Dental care critical in senior years"],
        "display_config": {"primary_color": "#9B5DE5", "accent_color": "#F5F0FF", "icon": "dog-senior"},
    },
    # ── Cats ──────────────────────────────────────────────────────────────────
    {
        "species": "cat", "category": "kitten",
        "title": "Kitten Nutrition Guide (0–12 months)",
        "description": "High-protein food essential for rapid growth. Taurine is critical.",
        "protein_min": 30, "protein_max": 40,
        "fat_min": 9, "fat_max": 15,
        "fiber_min": 2, "fiber_max": 4,
        "moisture_min": 12, "moisture_max": 20,
        "calories_min_per_day": 200, "calories_max_per_day": 400,
        "meals_per_day": 4,
        "serving_size_description": "¼ to ½ cup per meal",
        "water_needs": "Fresh water always; consider wet food for hydration",
        "recommended_foods": ["Kitten formula kibble", "Wet kitten food", "High-protein wet food"],
        "forbidden_foods": [
            {"food": "Chocolate", "reason": "Theobromine toxicity"},
            {"food": "Onions & Garlic", "reason": "Causes haemolytic anaemia in cats"},
            {"food": "Grapes & Raisins", "reason": "Kidney toxicity"},
            {"food": "Cow's Milk", "reason": "Most cats are lactose intolerant"},
        ],
        "health_notes": ["Taurine essential — deficiency causes heart disease", "DHA for brain development", "Never feed adult cat food — insufficient nutrients"],
        "display_config": {"primary_color": "#F72585", "accent_color": "#FFF0F6", "icon": "cat-kitten"},
    },
    {
        "species": "cat", "category": "adult",
        "title": "Adult Cat Nutrition Guide (1–10 years)",
        "description": "Obligate carnivores need animal protein. Taurine remains essential.",
        "protein_min": 26, "protein_max": 35,
        "fat_min": 9, "fat_max": 12,
        "fiber_min": 2, "fiber_max": 5,
        "moisture_min": 12, "moisture_max": 20,
        "calories_min_per_day": 200, "calories_max_per_day": 300,
        "meals_per_day": 2,
        "serving_size_description": "½ to 1 cup per meal",
        "water_needs": "Cats often drink little — wet food is recommended",
        "recommended_foods": ["High-protein adult kibble", "Wet food (>70% moisture)", "Raw diet", "Cooked lean meat"],
        "forbidden_foods": [
            {"food": "Chocolate & Caffeine", "reason": "Theobromine and caffeine toxicity"},
            {"food": "Onions, Garlic, Leeks", "reason": "Haemolytic anaemia"},
            {"food": "Grapes & Raisins", "reason": "Kidney failure"},
            {"food": "Dairy", "reason": "Lactose intolerance"},
            {"food": "Raw Fish in excess", "reason": "Thiamine deficiency over time"},
        ],
        "health_notes": ["Obligate carnivore — cannot thrive on plant-based diet", "Taurine must come from food", "Monitor for urinary tract issues — hydration key"],
        "display_config": {"primary_color": "#7209B7", "accent_color": "#F3E8FF", "icon": "cat-adult"},
    },
    {
        "species": "cat", "category": "senior",
        "title": "Senior Cat Nutrition Guide (10+ years)",
        "description": "Higher protein to prevent muscle loss, lower fat, and kidney-friendly formulas.",
        "protein_min": 28, "protein_max": 38,
        "fat_min": 8, "fat_max": 11,
        "fiber_min": 3, "fiber_max": 6,
        "moisture_min": 15, "moisture_max": 22,
        "calories_min_per_day": 180, "calories_max_per_day": 280,
        "meals_per_day": 2,
        "serving_size_description": "⅓ to ¾ cup per meal",
        "water_needs": "Critical — wet food strongly recommended",
        "recommended_foods": ["Senior cat formula", "High-moisture wet food", "Kidney-support formula (vet-prescribed if needed)"],
        "forbidden_foods": [
            {"food": "Chocolate & Caffeine", "reason": "Toxic"},
            {"food": "High-phosphorus foods", "reason": "Worsens kidney disease common in seniors"},
            {"food": "Onions & Garlic", "reason": "Toxic"},
        ],
        "health_notes": ["Kidney disease very common in senior cats — low phosphorus diet helps", "Dental disease management critical", "Bi-annual vet blood work recommended"],
        "display_config": {"primary_color": "#3A0CA3", "accent_color": "#EDE9FE", "icon": "cat-senior"},
    },
    # ── Parrots ───────────────────────────────────────────────────────────────
    {
        "species": "parrot", "category": "budgerigar",
        "title": "Budgerigar Nutrition Guide (Small Parrots)",
        "description": "Small seeds, pellets, and fresh veggies for active little birds.",
        "protein_min": 10, "protein_max": 15,
        "fat_min": 5, "fat_max": 8,
        "fiber_min": 10, "fiber_max": 15,
        "moisture_min": 10, "moisture_max": 15,
        "calories_min_per_day": 20, "calories_max_per_day": 40,
        "meals_per_day": 2,
        "serving_size_description": "1–2 tablespoons per meal",
        "water_needs": "Fresh water changed daily — critical to prevent bacterial growth",
        "recommended_foods": ["Quality seed mix (millet, canary)", "Pellets (40-60% of diet)", "Fresh vegetables (spinach, carrot, broccoli)", "Small fruit portions"],
        "forbidden_foods": [
            {"food": "Avocado", "reason": "Persin causes cardiac distress and death"},
            {"food": "Chocolate", "reason": "Theobromine and caffeine toxic to birds"},
            {"food": "Onions & Garlic", "reason": "Can cause haemolytic anaemia"},
            {"food": "Caffeine & Alcohol", "reason": "Highly toxic to birds"},
            {"food": "Apple Seeds", "reason": "Contain cyanide compounds"},
        ],
        "health_notes": ["Calcium deficiency common — cuttlebone recommended", "Vitamin A important — feed orange/yellow veggies", "No all-seed diet — leads to obesity and malnutrition"],
        "display_config": {"primary_color": "#06D6A0", "accent_color": "#E8FFF9", "icon": "parrot-small"},
    },
    {
        "species": "parrot", "category": "african_grey",
        "title": "African Grey Nutrition Guide (Medium Parrots)",
        "description": "Intelligent birds need varied, nutrient-rich diet. High calcium requirements.",
        "protein_min": 12, "protein_max": 18,
        "fat_min": 6, "fat_max": 10,
        "fiber_min": 12, "fiber_max": 18,
        "moisture_min": 10, "moisture_max": 15,
        "calories_min_per_day": 60, "calories_max_per_day": 100,
        "meals_per_day": 2,
        "serving_size_description": "¼ to ½ cup per meal",
        "water_needs": "Fresh water daily — consider filtered water",
        "recommended_foods": ["High-quality pellets (Harrison's, Zupreem)", "Fresh vegetables (dark leafy greens)", "Fruits (berries, mango, papaya)", "Small amounts of nuts", "Cooked legumes"],
        "forbidden_foods": [
            {"food": "Avocado", "reason": "Fatal — persin toxicity"},
            {"food": "Chocolate & Coffee", "reason": "Toxic"},
            {"food": "Onions & Garlic", "reason": "Toxic"},
            {"food": "High-salt foods", "reason": "Causes kidney damage"},
        ],
        "health_notes": ["Calcium & Vitamin D3 crucial — supplementation may be needed", "Feather destructive behaviour can signal nutritional deficiency", "Mental stimulation is as important as nutrition"],
        "display_config": {"primary_color": "#118AB2", "accent_color": "#E0F4FF", "icon": "parrot-medium"},
    },
    {
        "species": "parrot", "category": "macaw",
        "title": "Macaw Nutrition Guide (Large Parrots)",
        "description": "Large active birds need calorie-dense food and plenty of exercise.",
        "protein_min": 12, "protein_max": 18,
        "fat_min": 8, "fat_max": 12,
        "fiber_min": 15, "fiber_max": 20,
        "moisture_min": 10, "moisture_max": 15,
        "calories_min_per_day": 80, "calories_max_per_day": 150,
        "meals_per_day": 2,
        "serving_size_description": "½ to 1 cup per meal",
        "water_needs": "Large fresh water dish changed twice daily",
        "recommended_foods": ["Large parrot pellets", "Fresh fruits (mango, papaya, pomegranate)", "Fresh vegetables", "Nuts (walnut, almond — in moderation)", "Cooked grains and legumes"],
        "forbidden_foods": [
            {"food": "Avocado", "reason": "Fatal — persin toxicity"},
            {"food": "Chocolate & Caffeine", "reason": "Toxic"},
            {"food": "Onions & Garlic", "reason": "Toxic"},
            {"food": "Salty & Processed foods", "reason": "Kidney damage"},
        ],
        "health_notes": ["Zinc deficiency possible — avoid galvanised cages", "High activity level — adequate space and exercise essential", "Proper protein intake critical for feather quality"],
        "display_config": {"primary_color": "#EF233C", "accent_color": "#FFE8EA", "icon": "parrot-large"},
    },
]


def seed():
    """Insert all nutrition guides into the database (skips existing)."""
    from app import create_app
    from app.extensions import db
    from app.models.nutrition_guide import NutritionGuide

    app = create_app("production")
    with app.app_context():
        created = 0
        skipped = 0
        for guide_data in GUIDES:
            existing = NutritionGuide.query.filter_by(
                species=guide_data["species"],
                category=guide_data["category"],
            ).first()
            if existing:
                skipped += 1
                continue
            guide = NutritionGuide(**guide_data)
            db.session.add(guide)
            created += 1
        db.session.commit()
        print(f"✅ Nutrition guides seeded: {created} created, {skipped} skipped")


if __name__ == "__main__":
    seed()
