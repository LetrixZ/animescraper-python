import requests
import re
import json
import time
import os.path
import os
from datetime import datetime
from bs4 import BeautifulSoup

months = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def get_items(soup):
    item_cards = soup.find('div', {'class': 'anime__page__content'}).findAll(
        'div', {'class': 'custom_item2'})
    item_list = []
    for card in item_cards:
        slug = card.select_one('.card-title a')['href'].split('/')[3]
        title = card.select_one('h5 a').text
        episodes = re.findall(
            r'\d+', card.select_one('.ep').text.split(',')[0])
        if not episodes:
            episodes = None
        else:
            episodes = int(episodes[0])
        status = card.select_one('.card-status').text.strip()
        show_type = card.select_one('.card-info > .card-txt').text.strip()
        synopsis = card.select_one('.synopsis').text.strip()
        date_text = card.select_one('.ep > small').text
        start_date = {
            "day": int(date_text.split(' ')[2]),
            "month": int(months.get(date_text.split(' ')[1])),
            "year": int(date_text.split(' ')[4])
        }
        item = {
            'slug': slug,
            'title': title,
            'total_episodes': episodes,
            'status': status,
            'type': show_type,
            'synopsis': synopsis,
            'start_date': start_date
        }
        item_list.append(item)
    return item_list


def get_pages(items, page=1):
    print(f'Page {page}')
    url = f"https://jkanime.net/directorio/{page}/"
    res = requests.get(url)
    with open(f'jk/html/{page}.html', 'w', encoding='utf8') as f:
        f.write(res.text)
        f.close()
    soup = BeautifulSoup(res.text, 'html.parser')
    if len(soup.find('div', {'class': 'anime__page__content'}).findAll('div', {'class': 'custom_item2'})) > 0:
        parsed = get_items(soup)
        items.append(parsed)
        file = open(f'jk/json/{page}.json', 'w', encoding='utf8')
        file.write(json.dumps(parsed, ensure_ascii=False))
        file.close()
        time.sleep(3)
        get_pages(items, page=page+1)
    return items


def get_thumbnails(id, pages, slug):
    def map_thumb(it):
        return {
            'episode': it['number'],
            'image': 'https://cdn.jkanime.net/assets/images/animes/video/image_thumb/' + it['image']
        }
    thumb_list = []
    for i in range(1, pages + 1):
        if os.path.isfile(f'jk/items/thumbnails/{slug}/{i}.json'):
            with open(f'jk/items/thumbnails/{slug}/{i}.json', 'r', encoding='utf8') as f:
                thumb_list.append(json.loads(f.read()))
        else:
            time.sleep(1)
            url = f'https://jkanime.net/ajax/pagination_episodes/{id}/{i}/'
            res = requests.get(url)
            data = json.loads(res.text)
            data = list(map(map_thumb, data))
            with open(f'jk/items/thumbnails/{slug}/{i}.json', 'w', encoding='utf8') as f:
                f.write(json.dumps(data, ensure_ascii=False))
                f.close()
            thumb_list.append(data)
    flat_list = [item for sublist in thumb_list for item in sublist]
    return flat_list


def parse_item(soup, slug):
    title = soup.select_one('.anime__details__title h3').text
    synopsis = soup.select_one('.anime__details__text p').text
    info_tab = soup.select_one('.anime__details__widget').select('li')
    show_type = info_tab[0].text.replace('Tipo:', '').strip()
    genres = list(map(lambda x: x.text, info_tab[1].select('a')))
    total_episodes = re.findall(r'\d+', info_tab[3].text)
    if not total_episodes:
        total_episodes = None
    else:
        total_episodes = int(total_episodes[0])
    duration = re.findall(r'\d+', info_tab[4].text)
    if not duration:
        duration = None
    else:
        duration = int(duration[0])
    date = info_tab[5].text
    start_text = date
    if 'de' in start_text:
        start_date = {
            "day": int(start_text.split(' ')[2]),
            "month": int(months.get(start_text.split(' ')[1])),
            "year": int(start_text.split(' ')[4]),
        }
    else:
        start_date = {
            "day": int(re.findall(r'\d+', start_text.split(' ')[2])[0]),
            "month": int(months.get(start_text.split(' ')[1])),
            "year": int(start_text.split(' ')[3]),
        }
    end_date = None
    if len(date.split(' a ')) > 1:
        end_text = date.split(' a ')[1]
        end_date = {
            "day": int(end_text.split(' ')[1]),
            "month": int(months.get(end_text.split(' ')[0])),
            "year": int(end_text.split(' ')[3]),
        }
    status = info_tab[-1].select('span')[1].text.strip()
    if soup.select('.anime__pagination a.numbers'):
        uploaded_episodes = int(soup.select(
            '.anime__pagination a.numbers')[-1].text.split(' - ')[1])
    else:
        uploaded_episodes = None
    poster = soup.select_one('.anime__details__pic')['data-setbg']
    anime_id = soup.select_one('#guardar-anime')['data-anime']
    total_pages = len(soup.select('.anime__pagination a'))
    thumbs = get_thumbnails(anime_id, total_pages, slug)
    item = {
        'slug': slug,
        'title': title,
        'total_episodes': total_episodes,
        'uploaded_episodes': uploaded_episodes,
        'status': status,
        'type': show_type,
        'synopsis': synopsis,
        'start_date': start_date,
        'end_date': end_date,
        'genres': genres,
        'duration': duration,
        'poster': poster,
        'thumbnails': thumbs
    }
    return item


def get_info_page(slug):
    print(f'{slug}')
    try:
        if not os.path.exists(f'jk/items/thumbnails/{slug}'):
            os.makedirs(f'jk/items/thumbnails/{slug}')
        if os.path.isfile(f'jk/items/html/{slug}.html'):
            file = open(f'jk/items/html/{slug}.html',
                        'r', encoding='utf8').read()
            soup = BeautifulSoup(file, 'html.parser')
        else:
            time.sleep(1)
            url = f"https://jkanime.net/{slug}/"
            res = requests.get(url)
            with open(f'jk/items/html/{slug}.html', 'w', encoding='utf8') as f:
                f.write(res.text)
                f.close()
            soup = BeautifulSoup(res.text, 'html.parser')
        item = parse_item(soup, slug)
        with open(f'jk/items/json/{slug}.json', 'w', encoding='utf8') as f:
            f.write(json.dumps(item, ensure_ascii=False))
            f.close()
        return item
    except Exception as e:
        print(f'{slug}')
        raise e


def loop_library(skip=True):
    file = open('jk/list.json', 'r', encoding='utf8').read()
    data = json.loads(file)
    item_list = []
    for it in data:
        if skip:
            if os.path.isfile(f'jk/items/json/{it["slug"]}.json'):
                item = json.loads(open(f'jk/items/json/{it["slug"]}.json', 'r', encoding='utf8').read())
                item_list.append(item)
                continue
        item = get_info_page(it['slug'])
        item_list.append(item)
    with open('jk/list_info.json', 'w', encoding='utf8') as f:
        f.write(json.dumps(item_list, ensure_ascii=False))
        f.close()
