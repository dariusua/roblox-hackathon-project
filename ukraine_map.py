import json
from pathlib import Path
from urllib.request import urlopen

import folium
import pandas as pd
import streamlit as st
from branca.colormap import linear
from shapely.geometry import Point, shape
from streamlit_folium import st_folium


GEOJSON_URL = (
    "https://media.githubusercontent.com/media/"
    "wmgeolab/geoBoundaries/9469f09/"
    "releaseData/gbOpen/UKR/ADM1/"
    "geoBoundaries-UKR-ADM1_simplified.geojson"
)

REGION_NAMES = {
    "UA-05": "Вінницька область",
    "UA-07": "Волинська область",
    "UA-09": "Луганська область",
    "UA-12": "Дніпропетровська область",
    "UA-14": "Донецька область",
    "UA-18": "Житомирська область",
    "UA-21": "Закарпатська область",
    "UA-23": "Запорізька область",
    "UA-26": "Івано-Франківська область",
    "UA-30": "м. Київ",
    "UA-32": "Київська область",
    "UA-35": "Кіровоградська область",
    "UA-40": "м. Севастополь",
    "UA-43": "АР Крим",
    "UA-46": "Львівська область",
    "UA-48": "Миколаївська область",
    "UA-51": "Одеська область",
    "UA-53": "Полтавська область",
    "UA-56": "Рівненська область",
    "UA-59": "Сумська область",
    "UA-61": "Тернопільська область",
    "UA-63": "Харківська область",
    "UA-65": "Херсонська область",
    "UA-68": "Хмельницька область",
    "UA-71": "Черкаська область",
    "UA-74": "Чернігівська область",
    "UA-77": "Чернівецька область",
}


@st.cache_data
def load_boundaries():
    """Завантажуємо межі один раз і кешуємо їх."""
    path = Path(__file__).with_name("ukraine_regions.geojson")

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        with urlopen(GEOJSON_URL, timeout=30) as response:
            data = json.load(response)

        if len(data.get("features", [])) != 27:
            raise ValueError("Очікували межі 27 регіонів України.")

        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            # Навіть без права запису карта працюватиме з кешу.
            pass

    for feature in data["features"]:
        code = feature["properties"]["shapeISO"]
        feature["properties"]["region"] = REGION_NAMES[code]

    return data


def show_region_statistics(region_name, stats):
    st.subheader(region_name)

    if not stats:
        st.info("У завантаженому CSV немає даних для цього регіону.")
        return

    column1, column2 = st.columns(2)

    column1.metric(
        "Унікальних номерів",
        f"{stats['unique_plates']:,}",
    )
    column2.metric(
        "Середня блатність",
        f"{stats['average_score']:.1f} / 100",
    )

    column3, column4 = st.columns(2)

    column3.metric(
        "Середня умовна ціна",
        f"{stats['average_price_uah']:,.0f} грн",
    )
    column4.metric(
        "Умовна капіталізація",
        f"{stats['capitalization_uah']:,.0f} грн",
    )

    best = stats.get("most_expensive_plate")

    if best:
        st.markdown(f"**Найдорожчий номер: {best['plate']}**")
        st.caption(
            f"{best.get('brand') or 'Марка невідома'} · "
            f"{best.get('model') or 'Модель невідома'} · "
            f"{best['estimated_price_uah']:,.0f} грн"
        )

        with st.expander("Чому цей номер отримав таку оцінку?"):
            for reason in best["reasons"]:
                st.write(f"• {reason}")

            tariff = best.get("mvs_price_uah")

            if tariff is not None:
                st.write(f"Тариф комбінації МВС: {tariff:,.0f} грн")

    st.markdown("**Топ-3 номери регіону**")

    rows = []

    for plate in stats.get("top_plates", []):
        rows.append({
            "Номер": plate["plate"],
            "Марка": plate.get("brand"),
            "Модель": plate.get("model"),
            "Рік": plate.get("make_year"),
            "Бал": plate["score"],
            "Умовна ціна, грн": plate["estimated_price_uah"],
        })
      if rows:
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
        )


def show_ukraine_map(result):
    """Клікабельна карта та статистика вибраної області."""
    st.subheader("Карта блатності України")
    st.caption("Натисни на область, щоб відкрити її статистику.")

    try:
        boundaries = load_boundaries()
    except Exception as error:
        st.error(f"Не вдалося завантажити межі областей: {error}")
        return

    regions = result["regions"]

    metrics = {
        "Середня блатність": "average_score",
        "Середня ціна номера": "average_price_uah",
        "Капіталізація": "capitalization_uah",
        "Кількість номерів": "unique_plates",
    }

    metric_name = st.selectbox(
        "За чим розфарбувати карту?",
        list(metrics),
        key="map_metric",
    )
    metric = metrics[metric_name]

    values = [
        stats[metric]
        for name, stats in regions.items()
        if name in REGION_NAMES.values()
    ]

    minimum = min(values, default=0)
    maximum = max(values, default=1)

    colors = linear.YlGnBu_09.scale(
        minimum,
        max(maximum, minimum + 1),
    )
    colors.caption = metric_name

    for feature in boundaries["features"]:
        properties = feature["properties"]
        stats = regions.get(properties["region"])

        properties["has_data"] = stats is not None
        properties["value"] = stats[metric] if stats else None
        properties["display_value"] = (
            f"{stats[metric]:,.2f}" if stats else "Немає даних"
        )

    def style_region(feature):
        properties = feature["properties"]

        return {
            "fillColor": (
                colors(properties["value"])
                if properties["has_data"]
                else "#cbd5e1"
            ),
            "color": "#ffffff",
            "weight": 1.5,
            "fillOpacity": 0.88,
        }

    map_column, details_column = st.columns([1.4, 1])

    with map_column:
        ukraine_map = folium.Map(
            location=[48.5, 31.2],
            zoom_start=6,
            tiles="OpenStreetMap",
            control_scale=True,
        )

        ukraine_map.fit_bounds([
            [44.2, 22.0],
            [52.5, 40.3],
        ])

        folium.GeoJson(
            boundaries,
            style_function=style_region,
            highlight_function=lambda feature: {
                "weight": 3,
                "color": "#f59e0b",
                "fillOpacity": 1,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["region", "display_value"],
                aliases=["Регіон:", f"{metric_name}:"],
                sticky=True,
            ),
        ).add_to(ukraine_map)

        colors.add_to(ukraine_map)

        event = st_folium(
            ukraine_map,
            height=570,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key="ukraine_regions_map",
        )

        st.caption(
            "Сірий колір — немає даних. "
            "Межі: geoBoundaries / © OpenStreetMap contributors, ODbL."
        )

    clicked = event.get("last_clicked")

    if clicked:
        point = Point(clicked["lng"], clicked["lat"])

        for feature in boundaries["features"]:
            if shape(feature["geometry"]).covers(point):
                st.session_state["selected_map_region"] = (
                    feature["properties"]["region"]
                )
                break

    with details_column:
        region_name = st.session_state.get("selected_map_region")

        if region_name:
            show_region_statistics(
                region_name,
                regions.get(region_name),
            )
        else:
            st.info("Обери область на карті зліва.")

    st.caption(
        "Регіон визначено за початковими літерами номера, "
        "а не за поточним місцем проживання власника. "
        "Ціни й капіталізація — умовні оцінки проєкту."
    )
