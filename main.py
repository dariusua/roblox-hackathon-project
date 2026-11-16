import csv
from collections.abc import Iterator


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