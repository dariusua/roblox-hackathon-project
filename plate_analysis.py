import re
from datetime import datetime

from main import parse_data


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

REGIONS = {}

for codes, region in REGION_CODES.items():
    for code in codes.split():
        REGIONS[code] = region


PLATE_LETTERS = str.maketrans(
    "АВЕКМНОРСТІХ",
    "ABEKMHOPCTIX",
)

PLATE_PATTERN = re.compile(
    r"[ABCEHIKMOPTX]{2}[0-9]{4}[ABCEHIKMOPTX]{2}"
)

MEME_PATTERNS = {
    "52": 8,
    "42": 8,
    "228": 15,
    "1337": 25,
    "67": 8,
    "69": 10,
}

DIGIT_PREFERENCES = {
    "0": 1,
    "1": 8,
    "2": 4,
    "3": 3,
    "4": 2,
    "5": 5,
    "6": 0,
    "7": 10,
    "8": 7,
    "9": 6,
}


def get_mvs_price(digits: str):
    """Тариф цифрової комбінації за таблицею МВС.

    Це не повна вартість реєстрації.
    None — комбінації немає серед наведених спеціальних тарифів.
    """
    if digits == "0000":
        return None

    if digits in ("7777", "0001", "0007"):
        return 96000

    if digits in ("6666", "0006"):
        return 12000

    if len(set(digits)) == 1:
        return 60000

    if digits.startswith("000"):
        return 60000

    if digits[:3] == digits[0] * 3 or digits[1:] == digits[1] * 3:
        return 4800 if "666" in digits else 18000

    if digits[0] == digits[1] and digits[2] == digits[3]:
        return 4800 if "66" in digits else 18000

    if digits in ("0123", "1234"):
        return 18000

    if digits.startswith("00"):
        return 12000

    if max(digits.count(digit) for digit in set(digits)) == 3:
        return 4800

    if digits == digits[::-1] or digits[:2] == digits[2:]:
        return 4800

    return None


def evaluate_plate(value: str) -> dict:
    """Рахуємо блатність 0–100 та умовну ціну всього номера."""
    plate = "".join(value.upper().split()).translate(PLATE_LETTERS)

    result = {
        "plate": plate,
        "digits": None,
        "region": None,
        "is_standard": False,
        "score": None,
        "mvs_price_uah": None,
        "estimated_price_uah": None,
        "reasons": [],
    }

    if not PLATE_PATTERN.fullmatch(plate):
        result["reasons"] = ["Нестандартний або порожній номер"]
        return result

    digits = plate[2:6]

    if digits == "0000":
        result["reasons"] = ["Нульова комбінація не оцінюється"]
        return result

    prefix = plate[:2]
    suffix = plate[6:]
    letters = prefix + suffix

    patterns = [(5, "Базова оцінка")]

    if len(set(digits)) == 1:
        patterns.append((65, "Чотири однакові цифри"))

    if digits.startswith("000"):
        patterns.append((60, "Три початкові нулі"))

    if digits[:3] == digits[0] * 3 or digits[1:] == digits[1] * 3:
        patterns.append((45, "Три однакові цифри підряд"))

    if max(digits.count(digit) for digit in set(digits)) == 3:
        patterns.append((35, "Три однакові цифри"))

    if digits[0] == digits[1] and digits[2] == digits[3]:
        patterns.append((40, "Дві пари однакових цифр"))

    if digits == digits[::-1]:
        patterns.append((35, "Дзеркальний номер"))

    if digits[:2] == digits[2:]:
        patterns.append((35, "Повтор двох цифр"))

    differences = [
        int(digits[index + 1]) - int(digits[index])
        for index in range(3)
    ]

    if differences in ([1, 1, 1], [-1, -1, -1]):
        patterns.append((45, "Послідовні цифри"))

    if digits.endswith("00"):
        patterns.append((25, "Кругле число"))

    digit_score, main_reason = max(
        patterns,
        key=lambda item: item[0],
    )

    reasons = [main_reason]
    preference_bonus = 0

    if len(set(digits)) == 1 or digits.startswith("000"):
        preference_bonus = DIGIT_PREFERENCES[digits[-1]]

        if preference_bonus:
            reasons.append(
                f"Бонус за цифру {digits[-1]}: +{preference_bonus}"
            )

    meme_bonus = 0

    for combination, bonus in MEME_PATTERNS.items():
        if combination in digits:
            meme_bonus += bonus
            reasons.append(f"Популярна комбінація {combination}")

    meme_bonus = min(meme_bonus, 25)

    letter_bonus = 0

    if len(set(letters)) == 1:
        letter_bonus = 16
        reasons.append("Усі чотири літери однакові")
    else:
        if prefix == suffix:
            letter_bonus += 8
            reasons.append("Початкова й кінцева серії збігаються")

        if prefix[0] == prefix[1]:
            letter_bonus += 4
            reasons.append("Повтор літер у коді регіону")

        if suffix[0] == suffix[1]:
            letter_bonus += 4
            reasons.append("Повтор літер у кінцевій серії")

    if letters == "AAAA":
        letter_bonus += 4
        reasons.append("Додатковий бонус серії AA…AA")

    score = (
        digit_score
        + preference_bonus
        + meme_bonus
        + letter_bonus
    )

    mvs_price = get_mvs_price(digits)
    base_price = mvs_price if mvs_price is not None else 1000

    estimated_price = round(
        base_price
        * (1 + score / 100)
        * (1 + letter_bonus / 25)
    )

    result.update({
        "digits": digits,
        "region": REGIONS.get(prefix),
        "is_standard": True,
        "score": score,
        "mvs_price_uah": mvs_price,
        "estimated_price_uah": estimated_price,
        "reasons": reasons,
    })

    return result


def parse_registration_date(value: str):
    """Повертаємо ISO-дату, яку зручно порівнювати."""
    for date_format in ("%d.%m.%y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(
                value.strip(),
                date_format,
            ).date().isoformat()
        except ValueError:
            continue

    return None


def update_top(top: list, plate: dict, limit: int):
    top.append(plate)

    top.sort(
        key=lambda item: (
            -item["estimated_price_uah"],
            item["plate"],
        )
    )

    del top[limit:]


def summarize_brands(plates, min_count: int = 20) -> list:
    brands = {}

    for plate in plates:
        if not plate["brand"]:
            continue

        brand = plate["brand"].upper()

        if brand not in brands:
            brands[brand] = {
                "brand": brand,
                "unique_plates": 0,
                "blat_plates": 0,
                "total_score": 0,
                "most_expensive_plate": None,
            }

        stats = brands[brand]
        stats["unique_plates"] += 1
        stats["total_score"] += plate["score"]

        if plate["score"] >= 50:
            stats["blat_plates"] += 1

        best = stats["most_expensive_plate"]

        if (
            best is None
            or plate["estimated_price_uah"] > best["estimated_price_uah"]
            or (
                plate["estimated_price_uah"] == best["estimated_price_uah"]
                and plate["plate"] < best["plate"]
            )
        ):
            stats["most_expensive_plate"] = plate

    result = []

    for stats in brands.values():
        count = stats["unique_plates"]

        if count < min_count:
            continue

        stats["average_score"] = round(
            stats.pop("total_score") / count,
            2,
        )
        stats["blat_share_percent"] = round(
            stats["blat_plates"] / count * 100,
            2,
        )
        result.append(stats)

    return sorted(
        result,
        key=lambda item: (
            -item["blat_share_percent"],
            -item["average_score"],
            item["brand"],
        ),
    )


def analyze_regions(
    file_path: str,
    encoding: str = "utf-8-sig",
    min_brand_count: int = 20,
) -> dict:
    """Області, топ номерів та рейтинг марок."""
    unique_plates = {}

    records_read = 0
    duplicate_records = 0
    nonstandard_records = 0

    for car in parse_data(file_path, encoding=encoding):
        records_read += 1
        plate = evaluate_plate(car["N_REG_NEW"])

        if not plate["is_standard"]:
            nonstandard_records += 1
            continue

        year = car.get("MAKE_YEAR", "")

        plate.update({
            "brand": car.get("BRAND") or None,
            "model": car.get("MODEL") or None,
            "make_year": int(year) if year.isdecimal() else None,
            "registration_date": parse_registration_date(
                car.get("D_REG", "")
            ),
        })

        previous = unique_plates.get(plate["plate"])

        if previous is not None:
            duplicate_records += 1

            previous_date = previous["registration_date"] or ""
            current_date = plate["registration_date"] or ""

            if current_date < previous_date:
                continue

        # За однакової дати залишаємо останній запис у CSV.
        unique_plates[plate["plate"]] = plate

    regions = {}
    top_plates = []
    total_score = 0

    for plate in unique_plates.values():
        total_score += plate["score"]
        update_top(top_plates, plate, limit=10)

        region_name = plate["region"] or "Невідомий регіон"

        if region_name not in regions:
            regions[region_name] = {
                "unique_plates": 0,
                "total_score": 0,
                "capitalization_uah": 0,
                "top_plates": [],
            }

        stats = regions[region_name]
        stats["unique_plates"] += 1
        stats["total_score"] += plate["score"]
        stats["capitalization_uah"] += plate["estimated_price_uah"]

        update_top(stats["top_plates"], plate, limit=3)

    for stats in regions.values():
        count = stats["unique_plates"]

        stats["average_score"] = round(
            stats.pop("total_score") / count,
            2,
        )
        stats["average_price_uah"] = round(
            stats["capitalization_uah"] / count,
            2,
        )
        stats["most_expensive_plate"] = stats["top_plates"][0]

    count = len(unique_plates)

    return {
        "records_read": records_read,
        "duplicate_records": duplicate_records,
        "nonstandard_records": nonstandard_records,
        "unique_plates": count,
        "average_score": round(total_score / count, 2) if count else 0,
        "regions": regions,
        "top_plates": top_plates,
        "brand_ranking": summarize_brands(
            unique_plates.values(),
            min_count=min_brand_count,
        ),
    }
