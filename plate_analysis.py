for car in parse_data(file_path, encoding=encoding):
        records_read += 1
        plate = evaluate_plate(car["N_REG_NEW"])

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
