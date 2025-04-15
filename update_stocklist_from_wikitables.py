import requests
from bs4 import BeautifulSoup
import pandas as pd

# Get the web page
urls = [("https://en.wikipedia.org/wiki/Russell_1000_Index", "Russell_1000_Index"),
        ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "SP500_Index")]


for url in urls:
    response = requests.get(url[0])
    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table", {"class": "wikitable"})
    len(tables)
    # turn each table into a dataframe and print the header rows of each table
    for table in tables:
        df = pd.read_html(str(table))[0]
        if "Symbol"  in set(df.columns):
            datatable = df
            break

    datatable.to_csv(r"static/"+url[1] + ".csv", index=False)