import pandas, requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}
webpage = requests.get("https://in.bookmyshow.com/buytickets/hyderabad/movies", headers=headers)
soup = BeautifulSoup(webpage.content, 'html.parser')
