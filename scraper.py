import requests
import bs4
import sys
import re
import geocoder
import json
import argparse
import pprint


INSPECTION_DOMAIN = 'http://info.kingcounty.gov'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
INSPECTION_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}

def get_inspection_page(**kwargs):
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in kwargs.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    resp = requests.get(url, params=params)
    resp.raise_for_status() # <- This is a no-op if there is no HTTP error
    # remember, in requests `content` is bytes and `text` is unicode
    return resp.content, resp.encoding


def load_inspection_page(html):
    open_file = open(html)
    html = open_file.read()
    return html, 'utf-8'


def parse_source(response, encoding='utf-8'):
    soup = bs4.BeautifulSoup(response, 'html5lib', from_encoding=encoding)
    return soup


def extract_data_listings(html):
    id_finder = re.compile(r'PR[\d]+~')
    return html.find_all('div', id=id_finder)


def has_two_tds(element):
    is_tr = element.name == 'tr'
    td_children = element.find_all('td', recursive=False)
    has_two = len(td_children) == 2
    return is_tr and has_two


def clean_data(td):
    data = td.string
    try:
        return data.strip(" \n:-")
    except AttributeError:
        return u""


def extract_restaurant_metadata(element):
    metadata_rows = element.find('tbody').find_all(
        has_two_tds, recursive=False
    )
    rdata = {}
    current_label = ''
    for row in metadata_rows:
        key_cell, val_cell = row.find_all('td', recursive=False)
        new_label = clean_data(key_cell)
        current_label = new_label if new_label else current_label
        rdata.setdefault(current_label, []).append(clean_data(val_cell))
    return rdata


def is_inspection_row(elem):
    is_tr = elem.name == 'tr'
    if not is_tr:
        return False
    td_children = elem.find_all('td', recursive=False)
    has_four = len(td_children) == 4
    this_text = clean_data(td_children[0]).lower()
    contains_word = 'inspection' in this_text
    does_not_start = not this_text.startswith('inspection')
    return is_tr and has_four and contains_word and does_not_start


def extract_score_data(listing):
    rows = listing.find_all(is_inspection_row)
    samples = len(rows)
    total, high_score, average = 0, 0, 0
    for row in rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except (ValueError, TypeError):
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score
    if samples:
        average = total/float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data


def generate_results(test=False, count=10):
    kwargs = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98109'
    }
    if test:
        html, encoding = load_inspection_page('inspection_page.html')
    else:
        html, encoding = get_inspection_page(**kwargs)
    doc = parse_source(html, encoding)
    listings = extract_data_listings(doc)
    for listing in listings[:count]:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        metadata.update(score_data)
        yield metadata


def get_geojson(result):
    address = " ".join(result.get('Address', ''))
    if not address:
        return None
    geocoded = geocoder.google(address)
    geojson = geocoded.geojson
    inspection_data = {}
    use_keys = (
        'Business Name', 'Average Score', 'Total Inspections',
        'High Score', 'Address',
    )
    for key, val in result.items():
        if key not in use_keys:
            continue
        if isinstance(val, list):
            val = " ".join(val)
        inspection_data[key] = val
    new_address = geojson['properties'].get('address')
    if new_address:
        inspection_data['Address'] = new_address
    geojson['properties'] = inspection_data
    return geojson


if __name__ == '__main__':
    test = len(sys.argv) > 1 and sys.argv[1] == 'test'
    total_result = {'type': 'FeatureCollection', 'features': []}
    for result in generate_results(test):
        geo_result = get_geojson(result)
        pprint.pprint(geo_result)
        total_result['features'].append(geo_result)
    with open('my_map.json', 'w') as fh:
        json.dump(total_result, fh)
