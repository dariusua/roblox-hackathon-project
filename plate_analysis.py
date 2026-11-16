digit_score, main_reason = max(
        patterns,
        key=lambda item: item[0],
    )
    reasons = [main_reason]

    digit_preferences = {
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

    preference_bonus = 0

    if len(set(digits)) == 1 or digits.startswith("000"):
        preference_bonus = digit_preferences[digits[-1]]
        reasons.append(
            f"Бонус за вибрану цифру: +{preference_bonus}"
        )

    memes = {
        "52": 8,
        "42": 8,
        "228": 15,
        "1337": 25,
        "67": 8,
        "69": 10,
    }

    meme_bonus = 0

    for combination, bonus in memes.items():
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

    score = digit_score + preference_bonus + meme_bonus + letter_bonus

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
