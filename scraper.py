from bs4 import BeautifulSoup
from time import sleep
import requests
import json
import re
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

user_agent = (
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/106.0.0.0 Safari/537.36'
)

default_headers = {'User-Agent':user_agent}

def get_max_page() -> int:
    """ Maximum number of pages """
    session = requests.Session()
    response = session.get('https://pergikuliner.com/restaurants')
    page = BeautifulSoup(response.text, 'html.parser')
    text = page.find('h2', {'id':'top-total-search-view'})
    text = text.find('strong').text.split('dari')
    page_num = [int(t.strip()) for t in text]
    return int(page_num[1]/page_num[0])

def scrape_page(response):
    page = BeautifulSoup(response.text, 'html.parser')
    cards = page.find_all('div', class_='restaurant-result-wrapper')
    data = []
    for item in cards:
        # title and link
        title = item.find('h3').text.strip()
        link = 'https://pergikuliner.com' + item.find('a')['href']
        # food style and location
        description = item.find('div', class_='item-group').find('div').text.strip()
        description = description.split('|')
        if len(description) > 1:
            location = description[0].strip()
            cuisine = [i.strip() for i in description[1].split(',')]
        else:
            location = description
            cuisine = None
        # rating
        full_rate = item.find('div', class_='item-rating-result').find('small').text.strip()
        rate = item.find('div', class_='item-rating-result').text.replace(full_rate,'').strip()
        full_rate = full_rate.replace('/','')
        # location and price
        for p in item.find_all('p', class_='clearfix'):
            if 'icon-map' in p.find('i')['class']:
                place = p.find_all('span', class_='truncate')
                address = place[0].text.strip()
                street = place[1].text.strip()
            elif 'icon-price' in p.find('i')['class']:
                price_text = p.find('span').text.strip()
                if re.findall(r'-', price_text):
                    price_from = price_text.split('-')[0].strip()
                    price_till = price_text.split('-')[1].replace('/orang','').strip()
                elif re.findall(r'Di atas', price_text):
                    price_from = price_text.replace('Di atas','').replace('/orang','').strip()
                    price_till = None
                elif re.findall(r'Di bawah', price_text):
                    price_from = 'Rp. 0'
                    price_till = price_text.replace('Di bawah','').replace('/orang','').strip()
                else:
                    logging.info(f"Another condition in price")
                    price_from = price_text
                    price_till = price_text
            else:
                logging.info(f"Something else in location and price section")
        item_data = {
            'title': title,
            'rate': rate,
            'cuisine': cuisine,
            'location': location,
            'address': address,
            'street': street,
            'price_from': price_from,
            'price_till': price_till,
            'url': link,
        }
        data.append(item_data)
    return data

def crawl(npage=None):
    """ Crawl pages """
    session = requests.Session()
    session.headers.update(default_headers)

    if npage is None:
        npage = get_max_page() + 1
    
    data = []
    
    for n in range(1, npage):
        params = {'page': n}
        """ params = {
            'advance': '1',
            'average_price': '',
            'average_rate': '',
            'default_search': '',
            'latitude': '',
            'longitude': '',
            'meals': '',
            'open_at': '',
            'page': '2',
            'rate_rasa': 'true',
            'search_name_cuisine': '',
            'search_place': '',
            'sort_by': 'pergikuliner',
        }
        """
        try:
            response = session.get('https://pergikuliner.com/restaurants', params=params)
            logging.info(f"({response.status_code}) GET page {n}")
            data += scrape_page(response)
            sleep(1)
        except Exception as e:
            logging.error(f"Error in {n}: {e}")
            pass
    return data

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)

if __name__ == '__main__':
    data = crawl()
    save_data(data, "data.json")
