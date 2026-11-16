import argparse
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Блатні номери України",
    page_icon="🚘",
    layout="wide",
)

st.title("🚘 Блатні номери України")
st.caption(
    "Рейтинги областей, номери, автомобілі та потенціал АЗС. "
    "Вартість номерів і капіталізація — умовні оцінки проєкту."
)

from azs import analyze_fleet_for_azs
from main import parse_data
from plate_analysis import analyze_regions, evaluate_plate
from ukraine_map import show_ukraine_map


@st.cache_data(show_spinner=False)
def load_statistics(
    file_path: str,
    modified_time: int,
    file_size: int,
    encoding: str,
    min_count: int,
):
    """Зміна часу або розміру файлу оновлює кеш."""
    return analyze_regions(
        file_path,
        encoding=encoding,
        min_brand_count=min_count,
    )


@st.cache_data(show_spinner=False)
def load_azs_statistics(
    file_path: str,
    modified_time: int,
    file_size: int,
    encoding: str,
):
    return analyze_fleet_for_azs(
        parse_data(file_path, encoding=encoding),
        evaluate_plate,
    )


def show_plates(plates: list):
    if not plates:
        st.info("Немає номерів для відображення.")
        return

    rows = []

    for plate in plates:
        rows.append({
            "Номер": plate["plate"],
            "Область": plate["region"] or "Невідомий регіон",
            "Марка": plate.get("brand"),
            "Модель": plate.get("model"),
            "Рік": plate.get("make_year"),
            "Блатність": plate["score"],
            "Тариф МВС, грн": plate.get("mvs_price_uah"),
            "Умовна ціна, грн": plate["estimated_price_uah"],
            "Причини": ", ".join(plate["reasons"]),
        })

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Рік": st.column_config.NumberColumn(format="%d"),
            "Блатність": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
                format="%d",
            ),
            "Тариф МВС, грн": st.column_config.NumberColumn(
                format="%.0f",
            ),
            "Умовна ціна, грн": st.column_config.NumberColumn(
                format="%.0f",
            ),
        },
    )


def show_region_ranking(regions: dict):
    st.subheader("Рейтинг областей")

    rows = []

    for region, stats in regions.items():
        rows.append({
            "Область": region,
            "Кількість номерів": stats["unique_plates"],
            "Середня блатність": stats["average_score"],
            "Середня ціна, грн": stats["average_price_uah"],
            "Капіталізація, грн": stats["capitalization_uah"],
        })

    regions_df = pd.DataFrame(rows)

    metric = st.selectbox(
        "Показник рейтингу",
        [
            "Капіталізація, грн",
            "Середня ціна, грн",
            "Середня блатність",
            "Кількість номерів",
        ],
    )

    include_unknown = st.checkbox(
        "Показувати невідомий регіон",
        value=False,
    )

    if not include_unknown:
        regions_df = regions_df[
            regions_df["Область"] != "Невідомий регіон"
        ]

    ranked_df = regions_df.sort_values(
        by=[metric, "Область"],
        ascending=[False, True],
    )

    if ranked_df.empty:
        st.info("Немає номерів із відомими регіональними кодами.")
    else:
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

    st.subheader("Топ-3 номери області")

    selected_region = st.selectbox(
        "Обери область",
        sorted(regions),
    )

    show_plates(regions[selected_region]["top_plates"])


def show_brand_ranking(brands: list, min_count: int):
    st.subheader("Марки автомобілів із блатними номерами")
    st.caption(
        "Блатним у цьому рейтингу вважається номер із балом від 50. "
        f"Мінімум номерів марки: {min_count}."
    )

    rows = []

    for brand in brands:
        best = brand["most_expensive_plate"]

        rows.append({
            "Марка": brand["brand"],
            "Кількість номерів": brand["unique_plates"],
            "Блатних номерів": brand["blat_plates"],
            "Частка блатних, %": brand["blat_share_percent"],
            "Середня блатність": brand["average_score"],
            "Найдорожчий номер": best["plate"],
            "Його умовна ціна, грн": best["estimated_price_uah"],
        })

    if not rows:
        st.info(
            "Недостатньо даних. Для маленької вибірки додай "
            "--min-brand-count 1 до команди запуску."
        )
        return

    brands_df = pd.DataFrame(rows)

    st.bar_chart(
        brands_df.head(15),
        x="Марка",
        y="Частка блатних, %",
        horizontal=True,
        sort=False,
    )

    st.dataframe(
        brands_df,
        hide_index=True,
        use_container_width=True,
    )


def show_azs_page(regions: dict):
    st.subheader("⛽ Потенціал регіонів для АЗС")
    st.caption(
        "Рекомендації за складом автомобілів у CSV. "
        "Це попередня гіпотеза, а не готовий бізнес-план."
    )

    if not regions:
        st.info("Немає даних про легкові автомобілі.")
        return

    total_cars = sum(reg["total_cars"] for reg in regions.values())
    total_electro = sum(reg["electro"] for reg in regions.values())
    total_big_engines = sum(
        reg["big_engines"] for reg in regions.values()
    )
    total_vip = sum(
        reg["real_vip_cars"] for reg in regions.values()
    )

    column1, column2, column3, column4 = st.columns(4)

    column1.metric("Автомобілів у вибірці", f"{total_cars:,}")
    column2.metric("Електро за класифікатором", f"{total_electro:,}")
    column3.metric("ДВЗ від 2,5 л", f"{total_big_engines:,}")
    column4.metric(
        "Нових преміальних із блатними номерами",
        f"{total_vip:,}",
    )

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

    column1.metric("Електро", f"{reg['electro_pct']:.1f}%")
    column2.metric("Газ", f"{reg['gas_pct']:.1f}%")
    column3.metric(
        "Старі авто з блатними номерами",
        f"{reg['pont_pct']:.1f}%",
    )

    st.markdown("#### Паливний склад")

    classified = (
        reg["petrol"]
        + reg["diesel"]
        + reg["gas"]
        + reg["electro"]
    )
    other_fuel = max(0, reg["total_cars"] - classified)

    fuel_df = pd.DataFrame([
        {
            "Паливо": "Бензин / бензиновий гібрид",
            "Автомобілів": reg["petrol"],
        },
        {
            "Паливо": "Дизель",
            "Автомобілів": reg["diesel"],
        },
        {
            "Паливо": "Газ / змішане з газом",
            "Автомобілів": reg["gas"],
        },
        {
            "Паливо": "Електро за класифікацією azs.py",
            "Автомобілів": reg["electro"],
        },
        {
            "Паливо": "Інше / невідоме",
            "Автомобілів": other_fuel,
        },
    ])

    if reg["total_cars"] > 0:
        fuel_df["Частка, %"] = (
            fuel_df["Автомобілів"] / reg["total_cars"] * 100
        ).round(1)
    else:
        fuel_df["Частка, %"] = 0.0

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
            "Категорія": (
                "Преміальна марка від 2019 року з блатним номером"
            ),
            "Автомобілів": reg["real_vip_cars"],
        },
    ])

    st.dataframe(
        segments_df,
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Категорії можуть перетинатися — їх не потрібно сумувати."
    )

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
- **Флагманський АЗК:** великі двигуни ≥ 18% та електро ≥ 5%.
- **АЗС із LPG:** газових автомобілів ≥ 22%, якщо не спрацювала перша умова.
- **Класична АЗС:** решта випадків.

У модулі АЗС блатний номер має бал **від 30**.
Преміальний автомобіль — марка зі списку та рік **від 2019**.
Старий автомобіль — рік **до 2012 включно**.
            """
        )

    st.caption(
        "Це рекомендації форматів за регіонами, а не розташування "
        "реальних заправок. Модуль АЗС зберігає перший запис номера. "
        "Його класифікатор також може віднести дизельний гібрид "
        "до категорії електро."
    )

def show_plate_checker():
    st.subheader("🔎 Оціни свій номер")
    st.caption(
        "Введи номер у форматі АА1111АА. "
        "Підтримуються українські та латинські літери."
    )

    with st.form("plate_checker_form"):
        entered_plate = st.text_input(
            "Автомобільний номер",
            placeholder="АА1111АА",
        )
        submitted = st.form_submit_button("Оцінити номер")

    if submitted:
        if not entered_plate.strip():
            st.warning("Введи номер для оцінки.")
            return

        result = evaluate_plate(entered_plate)
        st.session_state["checked_plate"] = result

    result = st.session_state.get("checked_plate")

    if result is None:
        return

    if not result["is_standard"]:
        st.error(
            "Не вдалося оцінити номер. Потрібні дві літери, "
            "чотири цифри та дві літери, наприклад АА1111АА. "
            "Комбінація 0000 не оцінюється."
        )
        return

    st.markdown(f"### {result['plate']}")
    st.write(
        f"**Регіон:** {result['region'] or 'Невідомий регіон'}"
    )

    column1, column2, column3 = st.columns(3)

    column1.metric(
        "Блатність",
        f"{result['score']} / 100",
    )
    column2.metric(
        "Умовна ціна номера",
        f"{result['estimated_price_uah']:,.0f} грн",
    )

    tariff = result["mvs_price_uah"]

    column3.metric(
        "Тариф комбінації МВС",
        f"{tariff:,.0f} грн" if tariff is not None else "Не наведений",
    )

    st.progress(result["score"] / 100)

    st.markdown("**Чому така оцінка?**")

    for reason in result["reasons"]:
        st.write(f"• {reason}")

    st.caption(
        "Оцінка розраховується за комбінацією символів. "
        "Вона не підтверджує існування номера, його доступність "
        "або ринкову вартість. Тариф МВС не включає всі витрати "
        "на реєстрацію."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Візуалізація даних МВС",
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        help="Шлях до оригінального CSV",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Кодування CSV",
    )
    parser.add_argument(
        "--min-brand-count",
        type=int,
        default=20,
        help="Мінімальна кількість номерів марки",
    )

    args = parser.parse_args()

    if not args.csv_file:
        st.error("Вкажи CSV у команді запуску.")
        st.code(
            "python -m streamlit run visualization.py "
            "-- reestrtz2025.csv",
            language="bash",
        )
        st.stop()

    if args.min_brand_count < 1:
        st.error("--min-brand-count має бути не менше 1.")
        st.stop()

    file_path = Path(args.csv_file).expanduser().resolve()

    if not file_path.is_file():
        st.error(f"CSV не знайдено: {file_path}")
        st.stop()

    try:
        file_info = file_path.stat()

        with st.spinner("Аналізуємо номери…"):
            result = load_statistics(
                file_path=str(file_path),
                modified_time=file_info.st_mtime_ns,
                file_size=file_info.st_size,
                encoding=args.encoding,
                min_count=args.min_brand_count,
            )
    except Exception as error:
        st.error(f"Не вдалося обробити CSV: {error}")
        st.stop()

    st.caption(f"Джерело: {file_path.name}")

    regions = result["regions"]
    unique_count = result["unique_plates"]

    if not regions or unique_count == 0:
        st.warning("Немає номерів, придатних для оцінювання.")
        st.stop()

    capitalization = sum(
        stats["capitalization_uah"]
        for stats in regions.values()
    )

    column1, column2, column3 = st.columns(3)

    column1.metric("Унікальних номерів", f"{unique_count:,}")
    column2.metric(
        "Середня блатність",
        f"{result['average_score']:.1f} / 100",
    )
    column3.metric(
        "Умовна капіталізація",
        f"{capitalization:,.0f} грн",
    )

    st.caption(
        f"Прочитано: {result['records_read']:,} · "
        f"Повторних записів: {result['duplicate_records']:,} · "
        f"Неоцінених записів: {result['nonstandard_records']:,}"
    )

    st.divider()
    show_ukraine_map(result)
    st.divider()

    tab_regions, tab_plates, tab_brands, tab_azs, tab_checker = st.tabs([
        "Рейтинг областей",
        "Топ номерів та автомобілі",
        "Марки автомобілів",
        "⛽ АЗС",
        "🔎 Перевірити номер",
    ])

    with tab_regions:
        show_region_ranking(regions)

    with tab_checker:
        show_plate_checker()

    with tab_plates:
        st.subheader("Топ-10 найдорожчих номерів")
        st.caption(
            "Автомобілі з найблатнішими номерами. "
            "Марка й модель — з останнього запису номера за датою "
            "у CSV. Це не рейтинг вартості автомобілів."
        )
        show_plates(result["top_plates"])

    with tab_brands:
        show_brand_ranking(
            result["brand_ranking"],
            args.min_brand_count,
        )

    with tab_azs:
        try:
            with st.spinner("Аналізуємо автомобілі для АЗС…"):
                azs_regions = load_azs_statistics(
                    file_path=str(file_path),
                    modified_time=file_info.st_mtime_ns,
                    file_size=file_info.st_size,
                    encoding=args.encoding,
                )
        except Exception as error:
            st.error(f"Помилка аналізу АЗС: {error}")
        else:
            show_azs_page(azs_regions)

    st.divider()
    st.caption(
        "Номери нормалізуються та враховуються без повторів. "
        "Код номера визначає регіональну прив’язку, "
        "а не місце проживання власника. "
        "Тариф МВС і умовна ціна всього номера — окремі показники."
    )


if __name__ == "__main__":
    main()
