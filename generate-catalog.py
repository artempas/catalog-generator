import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def get_video_files(directory):
    """Получает список видеофайлов в директории и обрезает расширения."""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv']
    video_files = []
    for file in os.listdir(directory):
        if os.path.splitext(file)[1].lower() in video_extensions:
            video_files.append(os.path.splitext(file)[0])
    return video_files

def search_movie(api_url, api_token, movie_name):
    """Ищет информацию о фильме через API Kinopoisk Dev."""
    headers = {
        'X-API-KEY': api_token
    }
    params = {
        'query': movie_name,
    }
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get('docs'):
            index=1
            if len(data['docs'])>1:
                index=input('\n'.join([
                        f"{i+1}. {data['docs'][i].get('name')}/{data['docs'][i].get('alternativeName')}"
                        for i in range(len(data['docs']))
                ])+f'\nНайдено больше одного фильма с названием {movie_name}. Выберите фильм: ')
            return data['docs'][int(index)-1]


def download_poster(poster_url, movie_name):
    """Скачивает постер фильма и сохраняет его в папку .posters."""
    if not poster_url:
        return None
    
    # Создаем папку .posters, если она не существует
    if not os.path.exists('.posters'):
        os.makedirs('.posters')

    # Получаем имя файла из URL
    response = requests.get(poster_url)
    filename = os.path.basename(urlparse(poster_url).path)
    file_path = os.path.join('.posters', movie_name+'.'+response.headers['Content-type'].split('/')[1])

    # Скачиваем изображение
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    return None

def save_catalog_html(catalog, output_file):
    """Сохраняет каталог фильмов в формате HTML с фильтрацией и сортировкой."""
    # Собираем уникальные годы и жанры для селекторов
    years = sorted(set(movie['Год'] for movie in catalog if movie['Год'] != 'Неизвестно'))
    genres = set()
    for movie in catalog:
        genres.update(genre.strip() for genre in movie['Жанр'].split(',') if genre.strip())
    genres = sorted(genres)

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Каталог фильмов</title>
        <style>
            body {
                font-family: sans-serif
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                cursor: pointer;
                background-color: #f4f4f4;
            }
            img {
                width: 100px;
                height: auto;
            }
            .filters {
                margin: 20px 0;
                display: flex;
                gap: 20px;
                align-items: center;
            }
            .filter-group {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            select, input {
                padding: 5px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }
            .rating-high {
                color: #28b328;
                font-weight: bold;
            }
            .rating-good {
                font-weight: bold;
                color: #85c151;
            }
            .rating-medium {
                font-weight: bold;
                color: #ffd600;
            }
            .rating-low {
                font-weight: bold;
                color: #FF0000;
            }
        </style>
        <script>
            function sortTable(columnIndex) {
                const table = document.getElementById("movieTable");
                const rows = Array.from(table.rows).slice(1);
                const isAsc = table.getAttribute("data-sort-order") === "asc";
                rows.sort((a, b) => {
                    const aText = a.cells[columnIndex].innerText;
                    const bText = b.cells[columnIndex].innerText;
                    return isAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
                });
                table.tBodies[0].append(...rows);
                table.setAttribute("data-sort-order", isAsc ? "desc" : "asc");
            }

            function filterTable() {
                const genreSelect = document.getElementById("genreFilter").value;
                const yearSelect = document.getElementById("yearFilter").value;
                const nameInput = document.getElementById("nameFilter").value.toLowerCase();
                const rows = document.querySelectorAll("#movieTable tbody tr");

                rows.forEach(row => {
                    const genres = row.cells[3].innerText.split(',').map(g => g.trim());
                    const year = row.cells[1].innerText;
                    const name = row.cells[0].innerText.toLowerCase();

                    const genreMatch = !genreSelect || genres.includes(genreSelect);
                    const yearMatch = !yearSelect || year === yearSelect;
                    const nameMatch = !nameInput || name.includes(nameInput);

                    row.style.display = (genreMatch && yearMatch && nameMatch) ? "" : "none";
                });
            }
        </script>
    </head>
    <body>
        <h1>Каталог фильмов</h1>
        <div class="filters">
            <div class="filter-group">
                <label for="nameFilter">Поиск по названию:</label>
                <input type="text" id="nameFilter" onkeyup="filterTable()">
            </div>
            <div class="filter-group">
                <label for="yearFilter">Год:</label>
                <select id="yearFilter" onchange="filterTable()">
                    <option value="">Все годы</option>
    """

    # Добавляем опции для годов
    for year in years:
        html_content += f'                    <option value="{year}">{year}</option>\n'

    html_content += """
                </select>
            </div>
            <div class="filter-group">
                <label for="genreFilter">Жанр:</label>
                <select id="genreFilter" onchange="filterTable()">
                    <option value="">Все жанры</option>
    """

    # Добавляем опции для жанров
    for genre in genres:
        html_content += f'                    <option value="{genre}">{genre}</option>\n'

    html_content += """
                </select>
            </div>
        </div>
        <table id="movieTable" data-sort-order="asc">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Название</th>
                    <th onclick="sortTable(1)">Год</th>
                    <th onclick="sortTable(2)">Описание</th>
                    <th onclick="sortTable(3)">Жанр</th>
                    <th onclick="sortTable(4)">Оценка</th>
                    <th onclick="sortTable(5)">Продолжительность</th>
                    <th>Постер</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for movie in catalog:
        try:
            rating = float(movie['Оценка'])
            rating_class = 'rating-high' if rating > 8 else 'rating-good' if rating > 7 else 'rating-medium' if rating > 5 else 'rating-low'
        except (ValueError, TypeError):
            rating_class = ''
        html_content += f"""
                <tr>
                    <td>{movie['Название']}</td>
                    <td>{movie['Год']}</td>
                    <td>{movie['Описание']}</td>
                    <td>{movie['Жанр']}</td>
                    <td class="{rating_class}">{movie['Оценка']}</td>
                    <td>{movie['Продолжительность']}</td>
                    <td><img src="{movie['Постер']}" alt="Постер фильма"></td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # directory = input("Введите путь до директории с видеофайлами: ")
    api_url = "https://api.kinopoisk.dev/v1.4/movie/search"
    api_token = os.environ.get('api-token')
    output_file = "movie_catalog.html"

    video_files = get_video_files(directory)
    
    print(f"Найдено {len(video_files)} видеофайлов.")

    catalog = []
    for movie_name in video_files:
        print(f"Ищем информацию о фильме: {movie_name}")
        movie_info = search_movie(api_url, api_token, movie_name)
        if movie_info:
            poster_url = movie_info.get('poster', {}).get('url', '')
            local_poster = download_poster(poster_url, movie_name) if poster_url else None
            duration = movie_info.get('movieLength', 0)
            duration = f'{duration // 60}ч {duration%60}м' if duration > 60 else f'{duration}м' if duration else 'Нет данных'
            catalog.append({
                'Название': movie_info.get('name', 'Неизвестно'),
                'Год': movie_info.get('year', 'Неизвестно'),
                'Описание': movie_info.get('description', 'Описание отсутствует'),
                'Жанр': ', '.join(genre.get('name') for genre in movie_info.get('genres', [])),
                'Оценка': round(float(movie_info.get('rating', {}).get('kp')),2) if movie_info.get('rating', {}).get('kp') else 'Нет данных',
                'Продолжительность': duration,
                'Постер': local_poster if local_poster else ''
            })
        else:
            print(f"Информация о фильме {movie_name} не найдена.")

    save_catalog_html(catalog, output_file)
    print(f"Каталог фильмов сохранён в файл {output_file}")

if __name__ == "__main__":
    main()