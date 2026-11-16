import re

from main import parse_data


# Основні та альтернативні регіональні коди.
REGION_CODES = {
    "AA KA": "м. Київ",
    "AI KI": "Київська область",
    "AB KB": "Вінницька область",
    "AC KC": "Волинська область",
    "AE KE": "Дніпропетровська область",
    "AH KH": "Донецька область",
    "AM KM": "Житомирська область",
    "AO KO": "Закарпатська область",
    "AP KP": "Запорізька область",
    "AT KT": "Івано-Франківська область",
    "AK KK": "АР Крим",
    "BA HA": "Кіровоградська область",
    "BB HB": "Луганська область",
    "BC HC": "Львівська область",
    "BE HE": "Миколаївська область",
    "BH HH": "Одеська область",
    "BI HI": "Полтавська область",
    "BK HK": "Рівненська область",
    "BM HM": "Сумська область",
    "BO HO": "Тернопільська область",
    "AX KX": "Харківська область",
    "BT HT": "Херсонська область",
    "BX HX": "Хмельницька область",
    "CA IA": "Черкаська область",
    "CB IB": "Чернігівська область",
    "CE IE": "Чернівецька область",
    "CH IH": "м. Севастополь",
}

# Перетворюємо "AA KA": "м. Київ" на окремі записи для AA і KA.
REGIONS = {}
for codes, region in REGION_CODES.items():
    for code in codes.split():
        REGIONS[code] = region


PLATE_LETTERS = str.maketrans("АВЕКМНОРСТІХ", "ABEKMHOPCTIX")
PLATE_PATTERN = re.compile(
    r"[ABCEHIKMOPTX]{2}[0-9]{4}[ABCEHIKMOPTX]{2}"
)

MEME_PATTERNS = {
    "52": 8,
    "42": 10,
    "228": 15,
    "1337": 5,
    "67": 25,
    "69": 15,
}


def evaluate_plate(value: str) -> dict:
    """Рахуємо бал 0–100, умовну вартість та визначаємо регіон."""
    plate = "".join(value.upper().split()).translate(PLATE_LETTERS)

    result = {
        "plate": plate,
        "digits": None,
        "region": None,
        "is_standard": False,
        "score": None,
        "estimated_price_uah": None,
        "reasons": [],
    }

    if not PLATE_PATTERN.fullmatch(plate):
        result["reasons"] = ["Нестандартний або порожній номер"]
        return result

    digits = plate[2:6]
    region = REGIONS.get(plate[:2])

    # Базовий бал — найбільший із відповідних шаблонів.
    rules = []

    if len(set(digits)) == 1:
        rules.append((90, "Чотири однакові цифри"))

    if digits.count("0") == 3:
        rules.append((75, "Три нулі"))

    if digits[:3] == digits[0] * 3 or digits[1:] == digits[1] * 3:
        rules.append((60, "Три однакові цифри підряд"))

    if digits in ("0123", "1234", "2345", "3456", "4567",
                  "5678", "6789", "9876", "8765", "7654",
                  "6543", "5432", "4321", "3210"):
        rules.append((65, "Послідовні цифри"))

    if digits == digits[::-1]:
        rules.append((50, "Дзеркальний номер"))

    if digits[:2] == digits[2:]:
        rules.append((50, "Повтор двох цифр"))

    if digits[0] == digits[1] and digits[2] == digits[3]:
        rules.append((45, "Дві пари однакових цифр"))

    if digits.endswith("00"):
        rules.append((30, "Кругле число"))

    score, _ = max(rules, default=(0, ""), key=lambda rule: rule[0])
    reasons = [description for _, description in rules]

    # Кожен молодіжний шаблон додає бонус один раз.
    # Загальний бонус обмежений, щоб не завищувати оцінку.
    meme_bonus = 0
    for pattern, bonus in MEME_PATTERNS.items():
        if pattern in digits:
            meme_bonus += bonus
            reasons.append(f"Популярна комбінація {pattern}")

    score = min(100, score + min(meme_bonus, 25))

    # Прозора умовна модель ціни для порівняння номерів.
    price = 1000 + score * score * 10

    result.update({
        "digits": digits,
        "region": region,
        "is_standard": True,
        "score": score,
        "estimated_price_uah": price,
        "reasons": reasons or ["Звичайна комбінація"],
    })

    return result


def analyze_regions(file_path: str, encoding: str = "utf-8-sig") -> dict:
    """Рахуємо статистику за унікальними номерами в кожному регіоні."""
    regions = {}
    seen_plates = set()

    records_read = 0
    duplicate_records = 0
    nonstandard_records = 0

    for car in parse_data(file_path, encoding=encoding):
        records_read += 1
        plate = evaluate_plate(car["N_REG_NEW"])

        year = car.get("MAKE_YEAR", "").strip()

        plate.update({
            "brand": car.get("BRAND", "").strip() or None,
            "model": car.get("MODEL", "").strip() or None,
            "make_year": int(year) if year.isdecimal() else None,
        })

        if not plate["is_standard"]:
            nonstandard_records += 1
            continue

        if plate["plate"] in seen_plates:
            duplicate_records += 1
            continue

        seen_plates.add(plate["plate"])

        # Нові, спеціальні або невідомі коди не приписуємо області.
        region_name = plate["region"] or "Невідомий регіон"

        if region_name not in regions:
            regions[region_name] = {
                "unique_plates": 0,
                "total_score": 0,
                "capitalization_uah": 0,
                "most_expensive_plate": None,
            }

        stats = regions[region_name]
        stats["unique_plates"] += 1
        stats["total_score"] += plate["score"]
        stats["capitalization_uah"] += plate["estimated_price_uah"]

        current_best = stats["most_expensive_plate"]

        # За однакової ціни обираємо номер за алфавітом.
        if (
            current_best is None
            or plate["estimated_price_uah"] > current_best["estimated_price_uah"]
            or (
                plate["estimated_price_uah"] == current_best["estimated_price_uah"]
                and plate["plate"] < current_best["plate"]
            )
        ):
            stats["most_expensive_plate"] = plate

    for stats in regions.values():
        stats["average_score"] = round(
            stats.pop("total_score") / stats["unique_plates"], 2
        )
        stats["average_price_uah"] = round(
            stats["capitalization_uah"] / stats["unique_plates"], 2
        )

    return {
        "records_read": records_read,
        "duplicate_records": duplicate_records,
        "nonstandard_records": nonstandard_records,
        "unique_plates": len(seen_plates),
        "regions": regions,
    }

import json