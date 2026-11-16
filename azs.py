PREMIUM_BRANDS = [
    "PORSCHE", "MERCEDES-BENZ", "BMW", "LEXUS", "AUDI",
    "LAND ROVER", "RANGE ROVER", "BENTLEY", "MASERATI", "JAGUAR", "INFINITI"
]


def analyze_fleet_for_azs(rows_iterator, evaluate_plate_fn):
    seen_plates = set()
    regions = {}

    for car in rows_iterator:
        kind = car.get("KIND", "ЛЕГКОВИЙ").upper()
        if "ЛЕГКОВИЙ" not in kind:
            continue

        plate_info = evaluate_plate_fn(car["N_REG_NEW"])
        plate = plate_info["plate"]

        if not plate_info["is_standard"] or plate in seen_plates:
            continue

        seen_plates.add(plate)
        region = plate_info["region"] or "Невідомий регіон"

        if region not in regions:
            regions[region] = {
                "total_cars": 0,
                "petrol": 0,
                "diesel": 0,
                "gas": 0,
                "electro": 0,
                "big_engines": 0,
                "pont_cars": 0,
                "real_vip_cars": 0,
                "sum_capacity": 0,
                "count_capacity": 0,
            }

        reg = regions[region]
        reg["total_cars"] += 1

        fuel = car.get("FUEL", "").upper()
        is_electro = False

        if "ЕЛЕКТРО" in fuel and "БЕНЗИН" not in fuel:
            reg["electro"] += 1
            is_electro = True
        elif "ГАЗ" in fuel:
            reg["gas"] += 1
        elif "ДИЗЕЛЬ" in fuel:
            reg["diesel"] += 1
        elif "БЕНЗИН" in fuel:
            reg["petrol"] += 1

        cap_text = car.get("CAPACITY", "")
        if cap_text.isdigit():
            capacity = int(cap_text)
            reg["sum_capacity"] += capacity
            reg["count_capacity"] += 1

            if capacity >= 2500 and not is_electro:
                reg["big_engines"] += 1

        brand = car.get("BRAND", "").upper()
        year_text = car.get("MAKE_YEAR", "")
        year = int(year_text) if year_text.isdigit() else 0

        is_blat = plate_info["score"] >= 30
        is_premium = (brand in PREMIUM_BRANDS) and (year >= 2019)

        if is_blat and not is_premium and 0 < year <= 2012:
            reg["pont_cars"] += 1
        elif is_blat and is_premium:
            reg["real_vip_cars"] += 1


    for region in regions:
        reg = regions[region]
        total = reg["total_cars"]

        if reg["count_capacity"] > 0:
            reg["avg_capacity"] = round(reg["sum_capacity"] / reg["count_capacity"])
        else:
            reg["avg_capacity"] = 0

        reg["big_engines_pct"] = round(reg["big_engines"] / total * 100, 1)
        reg["electro_pct"] = round(reg["electro"] / total * 100, 1)
        reg["gas_pct"] = round(reg["gas"] / total * 100, 1)
        reg["pont_pct"] = round(reg["pont_cars"] / total * 100, 1)
        del reg["sum_capacity"]
        del reg["count_capacity"]
        if reg["big_engines_pct"] >= 18.0 and reg["electro_pct"] >= 5.0:
            reg["azs_format"] = "Флагманський АЗК (А-100 + Fast EV + ресторан)"
        elif reg["gas_pct"] >= 22.0:
            reg["azs_format"] = "Мультипаливна АЗС з газовим модулем (LPG)"
        else:
            reg["azs_format"] = "Класична АЗС (А-95 / Дизель + кав'ярня)"

    return regions