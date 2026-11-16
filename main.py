import csv
from collections.abc import Iterator

def load_azs_statistics(
    file_path: str,
    modified_time: int,
    file_size: int,
    encoding: str,
):
    """Окремо кешуємо аналіз автомобілів для АЗС."""
    return analyze_fleet_for_azs(
        parse_data(file_path, encoding=encoding),
        evaluate_plate,
    )


def show_azs_page(regions: dict):
    st.subheader("⛽ Потенціал регіонів для АЗС")
    st.caption(
        "Рекомендації за складом автомобілів у CSV. "
        "Регіон визначено за кодом номера. Це попередня гіпотеза, "
        "а не оцінка реального попиту чи готовий бізнес-план."
    )

    if not regions:
        st.info("Немає даних про легкові автомобілі для аналізу.")
        return

    total_cars = sum(reg["total_cars"] for reg in regions.values())
    total_electro = sum(reg["electro"] for reg in regions.values())
    total_big_engines = sum(
        reg["big_engines"] for reg in regions.values()
    )
    total_vip = sum(reg["real_vip_cars"] for reg in regions.values())

    column1, column2, column3, column4 = st.columns(4)

    column1.metric("Автомобілів у вибірці", f"{total_cars:,}")
    column2.metric("Електромобілів", f"{total_electro:,}")
    column3.metric("ДВЗ від 2,5 л", f"{total_big_engines:,}")
    column4.metric("Нових преміальних із блатними номерами", f"{total_vip:,}")

    st.divider()

    selected_region = st.selectbox(
        "Регіон для аналізу АЗС",
        sorted(regions),
        key="azs_region",
    )

    reg = regions[selected_region]

    st.markdown(f"### {selected_region}")
    st.info(f"**Рекомендований формат:** {reg['azs_format']}")

    column1, column2, column3 = st.columns(3)

    column1.metric("Автомобілів", f"{reg['total_cars']:,}")
    column2.metric(
        "Середній об’єм двигуна",
        (
            f"{reg['avg_capacity']:,} см³"
            if reg["avg_capacity"] > 0
            else "Немає даних"
        ),
    )
    column3.metric(
        "Великі двигуни",
        f"{reg['big_engines_pct']:.1f}%",
    )

    column1, column2, column3 = st.columns(3)

    column1.metric("Електромобілі", f"{reg['electro_pct']:.1f}%")
    column2.metric("Газ", f"{reg['gas_pct']:.1f}%")
    column3.metric(
        "Старі авто з блатними номерами",
        f"{reg['pont_pct']:.1f}%",
    )

    st.markdown("#### Паливний склад")

    # Класифікатор azs.py відносить автомобіль максимум до однієї групи.
    classified = (
        reg["petrol"]
        + reg["diesel"]
        + reg["gas"]
        + reg["electro"]
    )
    other_fuel = max(0, reg["total_cars"] - classified)

    fuel_df = pd.DataFrame([
        {"Паливо": "Бензин / бензиновий гібрид", "Автомобілів": reg["petrol"]},
        {"Паливо": "Дизель", "Автомобілів": reg["diesel"]},
        {"Паливо": "Газ / змішане з газом", "Автомобілів": reg["gas"]},
        {"Паливо": "Електро за класифікацією azs.py", "Автомобілів": reg["electro"]},
        {"Паливо": "Інше / невідоме", "Автомобілів": other_fuel},
    ])

    fuel_df["Частка, %"] = (
        fuel_df["Автомобілів"] / reg["total_cars"] * 100
    ).round(1)

    st.bar_chart(
        fuel_df,
        x="Паливо",
        y="Автомобілів",
        horizontal=True,
        sort=False,
    )

    st.dataframe(
        fuel_df,
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### Автомобілі та номери")

    segments_df = pd.DataFrame([
        {
            "Категорія": "Двигун від 2500 см³, не електро",
            "Автомобілів": reg["big_engines"],
        },
        {
            "Категорія": "Авто до 2012 року з блатним номером",
            "Автомобілів": reg["pont_cars"],
        },
        {
            "Категорія": "Преміальна марка від 2019 року з блатним номером",
            "Автомобілів": reg["real_vip_cars"],
        },
    ])

    st.dataframe(
        segments_df,
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Категорії можуть перетинатися — їх не потрібно сумувати.")

    st.divider()
    st.markdown("### Порівняння регіонів")

    rows = []
for name, data in regions.items():
        rows.append({
            "Область": name,
            "Автомобілів": data["total_cars"],
            "Бензин": data["petrol"],
            "Дизель": data["diesel"],
            "Газ": data["gas"],
            "Електро": data["electro"],
            "Середній об’єм, см³": data["avg_capacity"],
            "Великі двигуни": data["big_engines"],
            "Великі двигуни, %": data["big_engines_pct"],
            "Електро, %": data["electro_pct"],
            "Газ, %": data["gas_pct"],
            "Старі авто з блатними номерами": data["pont_cars"],
            "Старі авто з блатними номерами, %": data["pont_pct"],
            "Нові преміальні з блатними номерами": data["real_vip_cars"],
            "Рекомендований формат": data["azs_format"],
        })

    comparison_df = pd.DataFrame(rows)

    metric = st.selectbox(
        "Показник для порівняння",
        [
            "Автомобілів",
            "Великі двигуни, %",
            "Електро, %",
            "Газ, %",
            "Середній об’єм, см³",
            "Старі авто з блатними номерами, %",
            "Нові преміальні з блатними номерами",
        ],
        key="azs_metric",
    )

    ranked_df = comparison_df.sort_values(
        by=[metric, "Область"],
        ascending=[False, True],
    )

    st.bar_chart(
        ranked_df,
        x="Область",
        y=metric,
        horizontal=True,
        sort=False,
    )

    st.dataframe(
        ranked_df,
        hide_index=True,
        use_container_width=True,
    )

    st.download_button(
        "Завантажити статистику АЗС у CSV",
        data=ranked_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="azs_statistics.csv",
        mime="text/csv",
    )

    with st.expander("Як визначається рекомендований формат?"):
        st.markdown(
            """
- Флагманський АЗК: великі двигуни ≥ 18% та електромобілі ≥ 5%.
- АЗС із LPG: газових автомобілів ≥ 22%, якщо не спрацювала перша умова.
- Класична АЗС: решта випадків.

У azs.py блатним вважається номер із балом від 30.
«Новий преміальний» — марка з PREMIUM_BRANDS і рік від 2019.
Категорія старих автомобілів із блатними номерами — рік до 2012 включно.
            """
        )

    st.caption(
        "АЗС фізично не розміщуються на карті: у наборі немає координат "
        "заправок. Показуємо рекомендовані формати для регіонів."
    )


def parse_data(file_path, encoding = "utf-8-sig"):
    with open(file_path, encoding=encoding, newline="") as file:
        reader = csv.DictReader(file, delimiter=";", strict=True)

        if not reader.fieldnames or "N_REG_NEW" not in reader.fieldnames:
            raise ValueError("У CSV немає колонки N_REG_NEW.")

        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(
                    f"Неправильна кількість полів біля рядка {reader.line_num}."
                )

            yield {
                column: value.strip()
                for column, value in row.items()
            }
