import pandas as pd

# Крок 1: Завантаження даних
def load_data(file_path):
    data = pd.read_csv(file_path, sep=';', encoding='utf-8')
    return data

# Крок 2: Основні функції для обробки даних
def filter_by_region(data, region_koatuu):
    filtered_data = data[data['REG_ADDR_KOATUU'] == region_koatuu]
    return filtered_data

def analyze_vehicle_data(data):
    summary = data.groupby(['MAKE_YEAR', 'BRAND']).agg({
        'VIN': 'count',
        'COLOR': pd.Series.nunique,
        'KIND': pd.Series.nunique,
    }).reset_index()
    return summary

# Крок 3: Головна функція
def main():
    # Завантаження даних
    file_path = 'path/to/your/data.csv'  # Заміна на фактичний шлях до файлу
    data = load_data(file_path)
    
    # Приклад фільтрації по регіону
    region_koatuu = '6310138200'  # Заміна на бажаний код області
    region_data = filter_by_region(data, region_koatuu)
    
    # Аналіз даних по автомобілям
    vehicle_summary = analyze_vehicle_data(region_data)
    
    # Вивід результатів
    print(vehicle_summary)

if __name__ == "__main__":
    main()
