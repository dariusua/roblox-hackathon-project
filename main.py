import csv
from collections.abc import Iterator


def parse_data(
    file_path: str,
    encoding: str = "utf-8-sig",
) -> Iterator[dict[str, str]]:
    """Читаємо CSV МВС поступово та повертаємо очищені записи."""
    with open(file_path, encoding=encoding, newline="") as file:
        reader = csv.DictReader(
            file,
            delimiter=";",
            strict=True,
        )

        columns = reader.fieldnames

        if not columns or "N_REG_NEW" not in columns:
            raise ValueError("У CSV немає колонки N_REG_NEW.")

        if len(columns) != len(set(columns)):
            raise ValueError("У CSV є однакові назви колонок.")

        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(
                    f"Неправильна кількість полів біля рядка "
                    f"{reader.line_num}."
                )

            yield {
                column: value.strip()
                for column, value in row.items()
            }
