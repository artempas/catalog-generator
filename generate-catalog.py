import json
import os
import re
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

BASE_PATH = ''
DUMP_JSON = {}

def get_video_files():
    """Получает список видеофайлов в директории и обрезает расширения."""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.stub', ".m4v"]
    video_files = []
    for file in os.listdir(BASE_PATH):
        if os.path.splitext(file)[1].lower() in video_extensions:
            video_files.append(file)
    return video_files

def search_movie(api_url, api_token, file_name: str, query=None):
    """Ищет информацию о фильме через API Kinopoisk Dev."""
    global DUMP_JSON
    headers = {
        'X-API-KEY': api_token
    }
    if file_name in DUMP_JSON:
        print('Cached')
        return DUMP_JSON[file_name]
    movie_name = (os.path.splitext(file_name)[0].replace('.fixed','') if not query else query).replace('.',' ')
    extension = os.path.splitext(file_name)[1]
    params = {
        'query': movie_name,
        'limit': 5
    }
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get('docs'):
            index = 0
            if re.match(r'.* \([0-9]{4}\)\.[a-z]{3}', file_name) is None and not file_name.split('.')[-2] == 'fixed':
                index = input('\n'.join([
                    f"{i + 1}. {data['docs'][i].get('name')} ({data['docs'][i].get('year')}) / {data['docs'][i].get('alternativeName')}"
                    for i in range(len(data['docs']))
                ]) + f'\nНайдено больше одного фильма с названием {movie_name}. Выберите фильм или введите другое название (0 для пропуска): ')
                if index.isnumeric():
                    index = int(index) - 1
                    if index == -1:
                        return None
                else:
                    return search_movie(api_url, api_token, file_name, index)
            if file_name.split('.')[-2] == 'fixed':
                new_filename = file_name
            else:
                new_filename = f"{data['docs'][int(index)]['name']} ({data['docs'][index]['year']}){extension}"
                new_filename = re.sub(r'[\\/*?:"<>|]', "", new_filename)
                os.rename(os.path.join(BASE_PATH, file_name), os.path.join(BASE_PATH, new_filename))
            DUMP_JSON[new_filename]=data['docs'][index]
            return data['docs'][index]
        else:
            new_query = input(f'Не нашлось данных о фильме {movie_name}. Введите название (0 чтобы пропустить)')
            if new_query == '0':
                return None
            return search_movie(api_url, api_token, file_name, new_query)


def download_poster(poster_url, movie_name):
    """Скачивает постер фильма и сохраняет его в папку .posters."""
    directory = os.path.join(BASE_PATH, '.posters')
    if not poster_url:
        return None
    
    # Создаем папку .posters, если она не существует
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Получаем имя файла из URL
    response = requests.get(poster_url)
    file_path = os.path.join(directory, movie_name + '.' + response.headers['Content-type'].split('/')[1])
    if os.path.exists(file_path):
        print('Img cached')
        return file_path

    # Скачиваем изображение
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path
    return None


def save_catalog_html(catalog, output_file, total_duration):
    """Сохраняет каталог фильмов в формате HTML с фильтрацией и сортировкой."""
    # Собираем уникальные годы, жанры и страны для селекторов
    years = sorted(set(movie['Год'] for movie in catalog if movie['Год'] != 'Неизвестно'))
    genres = set()
    countries = set()
    for movie in catalog:
        genres.update(genre.strip() for genre in movie['Жанр'].split(',') if genre.strip())
        countries.update(movie['Страна'].split(','))
    genres = sorted(genres)
    countries = sorted(countries)

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Каталог фильмов</title>
        <style>
            .modal {
                display: none; 
                position: fixed; 
                z-index: 1000; 
                left: 0;
                top: 0;
                width: 100%; 
                height: 100%; 
                overflow: auto; 
                background-color: rgb(0,0,0); 
                background-color: rgba(0,0,0,0.9); 
            }

            .modal-content {
                margin: auto;
                display: block;
                width: auto;
                height: 100%;
            }

            .close {
                position: absolute;
                top: 15px;
                right: 35px;
                color: #fff;
                font-size: 40px;
                font-weight: bold;
                transition: 0.3s;
            }

            .close:hover,
            .close:focus {
                color: #bbb;
                text-decoration: none;
                cursor: pointer;
            }
            body {
                font-family: sans-serif;
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
                color: #180101;
                font-weight: bold;
                background: #0099298f;
            }
            .rating-good {
                font-weight: bold;
                background: #60e90c82;
            }
            .rating-medium {
                font-weight: bold;
                color: #585858;
            }
            .rating-low {
                font-weight: bold;
                color: #000000;
            }
            .asc::after {
                content: "▲";
            }
            .desc::after {
                content: "▼";
            }
        </style>
        <script>
            let currentSortColumn = -1;
            let currentSortOrder = 'asc';

            function sortTable(columnIndex) {
                const table = document.getElementById("movieTable");
                const rows = Array.from(table.rows).slice(1);

                if (currentSortColumn === columnIndex) {
                    currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSortColumn = columnIndex;
                    currentSortOrder = 'asc';
                }

                rows.sort((a, b) => {
                    let aint = parseInt(a.cells[columnIndex].innerText);
                    let bint = parseInt(b.cells[columnIndex].innerText);
                    if (isNaN(aint) || isNaN(bint)) {
                        const aText = a.cells[columnIndex].innerText;
                        const bText = b.cells[columnIndex].innerText;
                        return currentSortOrder === 'asc' ? aText.localeCompare(bText) : bText.localeCompare(aText);
                    } else {
                        return currentSortOrder === 'asc' ? aint - bint : bint - aint;
                    }
                });
                
                table.tBodies[0].append(...rows);
                updateSortArrows(columnIndex);
            }

            function updateSortArrows(columnIndex) {
                const headers = document.querySelectorAll('th');
                headers.forEach((header, index) => {
                    header.classList.remove('asc', 'desc');
                    if (index === columnIndex) {
                        header.classList.add(currentSortOrder);
                    }
                });
            }

            function filterTable() {
                const genreSelect = document.getElementById("genreFilter").value;
                const countrySelect = document.getElementById("countryFilter").value;
                const yearAfter = document.getElementById("yearAfter").value;
                const yearBefore = document.getElementById("yearBefore").value;
                const nameInput = document.getElementById("nameFilter").value.toLowerCase();
                const rows = document.querySelectorAll("#movieTable tbody tr");

                rows.forEach(row => {
                    const genres = row.cells[3].innerText.split(',').map(g => g.trim());
                    const countries = row.cells[6].innerText.split(',').map(c => c.trim());
                    const year = row.cells[1].innerText;
                    const name = row.cells[0].innerText.toLowerCase();

                    const genreMatch = !genreSelect || genres.includes(genreSelect.trim());
                    const countryMatch = !countrySelect || countries.includes(countrySelect.trim());
                    const yearMatch = (!yearAfter || year >= yearAfter) && (!yearBefore || year <= yearBefore);
                    const nameMatch = !nameInput || name.includes(nameInput);

                    row.style.display = (genreMatch && countryMatch && yearMatch && nameMatch) ? "" : "none";
                });
            }
        </script>
    </head>
    <body>
        <h1>Каталог фильмов</h1>""" + f"<h3>Всего фильмов: {len(catalog)}, Суммарная продолжительность: {total_duration // 60}ч  {total_duration % 60}мин</h3>"+ """
        <div class="filters">
            <div class="filter-group">
                <label for="nameFilter">Поиск по названию:</label>
                <input type="text" id="nameFilter" onkeyup="filterTable()">
            </div>
            <div class="filter-group">
                <label for="yearAfter">Год:</label>
                <input style="width: 75px" type="number" id="yearAfter" onchange="filterTable()">

                <label for="yearBefore">-</label>
                <input style="width: 75px" type="number" id="yearBefore" onchange="filterTable()">
            </div>
            <div class="filter-group">
                <label for="genreFilter">Жанр:</label>
                <select id="genreFilter" onchange="filterTable()">
                    <option value="">Все жанры</option>
    """

    # Добавляем опции для жанров
    for genre in genres:
        html_content += f'<option value="{genre}">{genre}</option>\n'

    html_content += """
                </select>
            </div>
            <div class="filter-group">
                <label for="countryFilter">Страна:</label>
                <select id="countryFilter" onchange="filterTable()">
                    <option value="">Все страны</option>
    """

    # Добавляем опции для стран
    for country in countries:
        html_content += f'<option value="{country}">{country}</option>\n'

    html_content += """
                </select>
            </div>
        </div>
        <table id="movieTable" data-sort-order="asc">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Название</th>
                    <th onclick="sortTable(1)">Год</th>
                    <th>Описание</th>
                    <th>Жанр</th>
                    <th onclick="sortTable(4)">Оценка</th>
                    <th onclick="sortTable(5)">Продолжительность, мин</th>
                    <th>Страна</th>
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
        poster_arg = movie['Постер'].replace('\\','\\\\')
        html_content += f"""
                <tr>
                    <td><a href="{movie['Ссылка']}">{movie['Название']}</td>
                    <td>{movie['Год']}</td>
                    <td>{movie['Описание']}</td>
                    <td>{movie['Жанр']}</td>
                    <td class="{rating_class}">{movie['Оценка']}</td>
                    <td>{movie['Продолжительность']}</td>
                    <td>{movie['Страна']}</td>
                    <td><img src="{movie['Постер']}" alt="Постер фильма" onclick="openModal('{poster_arg}')" style="cursor: pointer;"></td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
        <div id="myModal" class="modal">
            <span class="close" onclick="closeModal()">&times;</span>
            <img class="modal-content" id="img01">
        </div>

        <script>
            function openModal(imgSrc) {
                const modal = document.getElementById("myModal");
                const modalImg = document.getElementById("img01");
                modal.style.display = "block";
                modalImg.src = imgSrc;
            }

            function closeModal() {
                const modal = document.getElementById("myModal");
                modal.style.display = "none";
            }
        </script>
    </body>
    </html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    global BASE_PATH
    global DUMP_JSON
    BASE_PATH = input("Введите путь до директории с видеофайлами: ")
    if os.path.exists('./dump.json'):
        with open('dump.json') as dump:
            DUMP_JSON=json.load(dump)
    api_url = "https://api.kinopoisk.dev/v1.4/movie/search"
    api_token = os.environ.get('api-token')
    output_file = "1. Каталог.html"

    video_files = get_video_files()
    
    print(f"Найдено {len(video_files)} видеофайлов.")

    catalog = []
    total_duration = 0
    for movie_name in video_files:
        print(f"Ищем информацию о фильме: {movie_name}")
        movie_info = search_movie(api_url, api_token, movie_name)
        if type(movie_info) == dict:
            poster_url = movie_info.get('poster', {}).get('url', '')
            local_poster = download_poster(poster_url, movie_name) if poster_url else None
            duration = movie_info.get('movieLength', 0)
            total_duration += duration
            duration = duration if duration else 'Нет данных'
            countries = ', '.join(i['name'] for i in movie_info.get('countries', []))
            url = f'https://www.kinopoisk.ru/film/{movie_info.get("id")}/'
            catalog.append({
                'Название': movie_info.get('name', 'Неизвестно'),
                'Год': movie_info.get('year', 'Неизвестно'),
                'Описание': movie_info.get('description', 'Описание отсутствует'),
                'Жанр': ', '.join(genre.get('name') for genre in movie_info.get('genres', [])),
                'Оценка': round(float(movie_info.get('rating', {}).get('kp')), 2) if movie_info.get('rating', {}).get('kp') else 'Нет данных',
                'Продолжительность': duration,
                'Страна': countries,
                'Постер': local_poster if local_poster else '',
                'Ссылка': url
            })
        else:
            print(f"Информация о фильме {movie_name} не найдена.")

    save_catalog_html(catalog, os.path.join(BASE_PATH, output_file), total_duration)
    with open('dump.json', 'w') as dump:
        json.dump(DUMP_JSON, dump)
    
    print(f"Каталог фильмов сохранён в файл {output_file}")

if __name__ == "__main__":
    main()
