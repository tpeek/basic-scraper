import requests
import bs4
import sys


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
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response


def parse_source(response, encoding='utf-8'):
    soup = bs4.BeautifulSoup(response, 'html5lib', from_encoding=encoding)
    return soup

if __name__ == '__main__':
    kwargs = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98109'
    }
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # you will likely have something different here, depending on how
        # you implemented the load_inspection_page function.
        response = get('inspection_page.html')
        html =response.content
        encoding = response.encoding
    else:
        response = get_inspection_page(**kwargs)
        html =response.content
        encoding = response.encoding
    doc = parse_source(html, encoding)
    print doc.prettify(encoding=encoding)