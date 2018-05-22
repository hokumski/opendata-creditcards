import numpy as np
import pandas as pd
import requests
from datetime import timedelta


# http://sbrfdata.ru/opendata.zip

# https://data.gov.sg/dataset/credit-and-charge-card-statistics?resource_id=abb9c5b4-2d9f-4c97-bc19-b701dbb074d4
# https://data.gov.sg/dataset/37f61fe1-1ad3-4d50-bf43-8d8539cd247b/download

# https://www.cbr.ru/currency_base/dynamics.aspx
# https://www.cbr.ru/currency_base/dynamics.aspx?VAL_NM_RQ=R01625&date_req1=15.01.2014&date_req2=15.08.2015&rt=1&mode=1


sberbank = pd.read_csv('data/amCharts.csv')
sberbank.columns = ['tdate', 'spent_russia_rub', 'region']
sberbank['date'] = pd.to_datetime(sberbank['tdate'])
sberbank.drop(['tdate','region'], inplace=True, axis=1)

singapore = pd.read_csv('data/credit-and-charge-card-statistics-monthly.csv')
singapore['spent_singapore_sdol'] = singapore['total_billings'] / singapore['cards_main'] * 1000000
singapore['tdate'] = singapore['month'] + '-15'
singapore['date'] = pd.to_datetime(singapore['tdate'])

sberbank = sberbank[sberbank['date'] < pd.to_datetime('2015-09-01')]
sberbank.set_index('date', inplace=True)
singapore = singapore[singapore['date'] > pd.to_datetime('2014-01-01')]
singapore.set_index('date', inplace=True)

df = sberbank.join(singapore)
df.drop(
    df.columns[[not x.startswith('spent') for x in df.columns]],
    axis=1, inplace=True
)

# rates = requests.get('https://www.cbr.ru/currency_base/dynamics.aspx?VAL_NM_RQ=R01625&date_req1=15.01.2014&date_req2=15.08.2015&rt=1&mode=1').content
# with open("data/rates.html", "wb") as rates_file:
#     rates_file.write(rates)

with open("data/rates.html", "rb") as rates_file:
    rates = rates_file.read()

rates_html = rates.decode('utf-8')
rates = pd.read_html(rates_html)  # using decimal=True not works here
rates = rates[0]  # first table
rates.drop(0, inplace=True)  # droping wrong header
rates.drop(1, inplace=True, axis=1)  # droping column with multiplier
rates.columns = ['tdate', 'rate']
rates['date'] = pd.to_datetime(rates['tdate'], dayfirst=True)
rates['rate'] = rates['rate'].apply(lambda x: float(x[0:2]+'.'+x[2:]))
rates.set_index('date', inplace=True)
rates.drop('tdate', inplace=True, axis=1)

start_date = rates.iloc[0].name
end_date = rates.iloc[-1].name

missed_dates = {}
for x in range((end_date-start_date).days + 1):
    xdate = start_date + timedelta(days=x)
    if not xdate in rates.index:
        missed_dates[xdate] = None
misseds = df.from_dict(data=missed_dates, orient='index')
misseds.columns = ['rate']

rates = rates.append(misseds)
rates.sort_index(inplace=True)
rates.fillna(method='ffill', inplace=True)

rates15 = rates[
    [x.day == 15 for x in rates.index]
]


df = df.join(rates15)
df['spent_singapore_rub'] = df['spent_singapore_sdol'] * df['rate']
df['spent_singapore_rub'] = df['spent_singapore_rub'].apply(int)
df.drop(['spent_singapore_sdol', 'rate'], axis=1, inplace=True)

coef = np.corrcoef(df['spent_russia_rub'], df['spent_singapore_rub'])[0, 1]

graph = df.plot(
    yticks=range(0, 26000, 2500),
    grid=True
)

graph.set_title(
    'Paid by Cards: Russia vs Singapore',
    pad=20,
    size='large',
    loc='left'
)
graph.set_title(
    'Correlation: {0:.2f}%'.format(coef*100),
    size='small',
    loc='right'
)
graph.set_xlabel('Year - Month', labelpad=15)
graph.set_ylabel('Spent for a month, RUB (Russian Rouble)', labelpad=10)

for l in graph.get_legend().texts:
    if 'russia' in l.get_text():
        l.set_text('Russia')
    if 'singapore' in l.get_text():
        l.set_text('Singapore')

for grid_line in graph.get_xgridlines():
    grid_line.set_color('#cccccc')
    grid_line.set_alpha(0.5)
for grid_line in graph.get_ygridlines():
    grid_line.set_color('#cccccc')
    grid_line.set_alpha(0.5)

graph.get_figure().show()
graph.get_figure().savefig('output.png')