import requests
import webbrowser
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup





# in terms of efficiency and lookup speed, this is actually incredibly slow.
def open10K(ticker_or_cik, year:int, format_as:str = 'read', launch_browser:bool = True):
    """Opens default browser tab to 10-K filing displayed in desired data format.

    Formats available\n
    `read` 
        Opens 10-K to traditional SEC view
    `inline`
        Opens 10-K as an inline XBRL View, if available. (complete XBRL view tools unavailable for 10-Ks filed before 2019)
    `index`
        Opens to 10-K's filing index display
    `txt`
        Opens 10-K as a plain text version.
    `archive`
        Opens to company's accession directory containing the 10-K.
    `xmldir`
        Opens to company's accession directory, however displays xml data instead. Not particularly useful in getting information on 10-Ks. 
        More for show than for use a tool...
    `jsondir`
        Opens to company's accession directory, however displays json data instead. Also not particularly useful in getting information on 10-Ks. 
    """
    if type(ticker_or_cik) == str:
        with open('tickers_to_cik.json') as file:
            tickers = json.load(file)
        try:
            cik = tickers[ticker_or_cik]
        except KeyError:
            print(f'Ticker {ticker_or_cik} not recognized. Consider using CIK.')
            return
    else:
        cik = ticker_or_cik

    cik, year, format_as = _type_and_data_check(cik, year, format_as)
    basic_url = _url_10K_finder(cik, year)
    if basic_url is None:
        print(f"10-K for {ticker_or_cik} from year {year} could not be found")
        return
    ready_url = _url_presenter(basic_url, format_as)
    if launch_browser:
        webbrowser.open_new_tab(ready_url)
        return ready_url
    else:
        return ready_url





def get_semireadable_raw_10K_text_file(ticker_or_cik, year:int,) -> None:
    if type(ticker_or_cik) == str:
        with open('tickers_to_cik.json') as file:
            tickers = json.load(file)
        try:
            cik = tickers[ticker_or_cik]
        except KeyError:
            print(f'Ticker {ticker_or_cik} not recognized. Consider using CIK.')
            return
        file_name = f'{ticker_or_cik}-{str(year)[-2:]}-raw-10K-readable'
    else:
        cik = ticker_or_cik
        file_name = f'{cik}-{str(year)[-2:]}-raw-10K-readable'

    url_10K = open10K(cik, year, format_as='txt', launch_browser=False)
    response = requests.get(url_10K)
    text = BeautifulSoup(response.text, 'html.parser').prettify()
    lines = text.split('\n')
    with open(file_name, 'w', encoding='utf8') as file:
        for i in range(len(lines)):
            line = lines[i]
            strip_line = line.strip()
            if strip_line.startswith(('<ix', '<html')):
                front_whitespace = len(line) - len(line.lstrip(' '))
                parts = lines[i].split()
                for part in parts:
                    if len(part) > 100:
                        file.write(f'{" "*(front_whitespace+4)}{part[:100]}...\n')
                    else:
                        file.write(f'{" "*(front_whitespace+4)}{part}\n')
            else:
                file.write(f'{line}\n')






























def _type_and_data_check(cik, year, format_as):
    format_types = ['txt', 'read', 'inline', 'index', 'archive', 'xmldir', 'jsondir']
    if format_as not in format_types:
        raise KeyError(f'{format_as} is not recognized as a valid format')
    if type(cik) != int:
        try:
            if type(cik) == float:
                print("Using a float to represent a CIK is dangerous...")
            cik = int(cik)
        except ValueError as not_int_like:
            try:
                cik = int(float(cik))
                print('Using a float-like string to represent a CIK is NOT a good idea!')
            except ValueError:
                raise ValueError('CIK must be an object which can be cast as an int') from not_int_like
    if type(year) != int:
        try: 
            if type(year) == float:
                print('Using a float to represent a year is dangerous...')
            year = int(year)
        except ValueError as not_int_like:
            try:
                year = int(float(year))
                print('Using a float-like string to represent a year is NOT a good idea!')
            except ValueError:
                raise ValueError('Year must be an object which can be cast as an int') from not_int_like
    if cik > 10000000000:
        raise ValueError("CIKs do not have that many digits")
    if year < 1996:
        raise ValueError("This program does not support 10-Ks filed before 1996. Sorry")
    return cik, year, format_as


def _url_10K_finder(cik, year) -> list:
    qtr4 = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR4/form.idx'
    qtr3 = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR3/form.idx'
    qtr2 = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR2/form.idx'
    qtr1 = f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR1/form.idx'
    
    master_file_urls = [qtr4, qtr3, qtr2, qtr1]
    for url in master_file_urls:
        response = requests.get(url)
        text = response.text
        status = response.status_code

        if status != 200:
            if status == 429:
                raise ConnectionRefusedError("""Response 429: You broke the rate limit threshold!
                Are you using this grab_10K to mass gather 10-Ks? If so, stop. This 10-K grabber
                is for getting one off 10-Ks without having to jump over to the SEC.""")
            elif 300 <= status < 400:
                print(f"""Response {status}. Do with that what you will. 
                Page info:
                {text}""")
            elif 400 <= status < 500:
                raise ConnectionError(f"""ClientError: {status}
                Info:
                {text}""")
            elif 500 <= status < 600:
                raise ConnectionError(f'ServerError: {status}')
            else:
                raise ConnectionError(f'Other error: {status}')
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if i < 10:
                continue
            data = line.split()
            try:
                if (data[0]=='10-K') or data[0] == '10-K/A':
                    if int(data[-3]) == cik:
                        return f'https://www.sec.gov/Archives/{data[-1]}'
            except IndexError:
                pass
    return None


def _url_presenter(basic_url, format_as):
    txt = basic_url
    if format_as == 'txt':
        return txt
    og = txt.replace('.txt', '-index.html')
    if format_as == 'index':
        return og
    archive = txt.replace('-','').replace('.txt','')
    if format_as == 'archive':
        return archive
    xmldir = archive + '/index.xml'
    if format_as == 'xmldir':
        return xmldir
    jsondir = archive + '/index.json'
    if format_as == 'jsondir':
        return jsondir

    # means it is either the read version or the linline
    json_item_data = dict(requests.get(jsondir).json())['directory']['item']
    readable_extension = None
    largest_size = 0
    for dictionary in json_item_data:
        try:
            name = dictionary['name']
        except KeyError:
            continue
        try:
            size = dictionary['size'] 
        except KeyError:
            continue
        try:
            size = int(size)
        except ValueError:
            continue
        if (name[-3:] == 'htm') and (size > largest_size):
            readable_extension = name
            largest_size = size
    readable = f'{archive}/{readable_extension}'
    if format_as == 'read':
        return readable
    else:
        url_parts = urlparse(readable)
        inline = f'{url_parts.scheme}://{url_parts.netloc}/ix?doc={url_parts.path}'
        return inline




# examples
#get10K('AAPL', 2020)
#get_semireadable_raw_10K_text_file("AAPL", 2020)