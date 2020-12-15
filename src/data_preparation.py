# environment setup
import seaborn as sns; sns.set_theme()
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthEnd
import requests
from tqdm import tqdm
from datetime import datetime


# helpers
def get_organisation_post_code(org_code: str) -> (str, str):
	try:
		r: requests.models.Response = requests.get('https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/{}'.format(org_code))
		data: dict = r.json()
		return data['Organisation']['GeoLoc']['Location']['PostCode'], data['Organisation']['GeoLoc']['Location']['Town']
	except Exception as e:
		print(e)
	else:
		return None, None


def get_post_code_geo_data(post_code: str) -> str:
	try:
		r: requests.models.Response = requests.get(
			'http://api.getthedata.com/postcode/{}'.format(post_code.replace(' ', '+')))
		data: dict = r.json()
		if data['status'] == 'match':
			return {
				'latitude': float(data['data']['latitude']),
				'longitude': float(data['data']['longitude']),
				'postcode_area': data['data']['postcode_area'],
				'postcode_district': data['data']['postcode_district']
			}
		else:
			return None
	except Exception as e:
		print(e)
	else:
		return None



# import data
df: pd.core.frame.DataFrame = pd.read_csv(
	'./data/nhs_england_overnight_beds_raw.csv'
)

# ensure correct types
df['date']: pd.core.series.Series = pd.to_datetime(df['date']) + MonthEnd(1)

# get postal code and geolocation data
org_code_post_code_town: dict = {}
unique_org_codes: list = df['org_code'].unique().tolist()
for org_code in tqdm(unique_org_codes):
	post_code, town = get_organisation_post_code(org_code)
	if post_code is None:
		print(org_code)
	org_code_post_code_town[org_code] = {
		'postal_code': post_code,
		'town': town
	}
	additional_post_code_data = get_post_code_geo_data(post_code=post_code)
	for key in additional_post_code_data:
		org_code_post_code_town[org_code][key] = additional_post_code_data[key]
df['postal_code'] = df['org_code'].apply(lambda x: org_code_post_code_town[x]['postal_code'])
df['town'] = df['org_code'].apply(lambda x: org_code_post_code_town[x]['town'])
df['latitude'] = df['org_code'].apply(lambda x: org_code_post_code_town[x]['latitude'])
df['longitude'] = df['org_code'].apply(lambda x: org_code_post_code_town[x]['longitude'])
df['postcode_area'] = df['org_code'].apply(lambda x: org_code_post_code_town[x]['postcode_area'])
df['postcode_district'] = df['org_code'].apply(lambda x: org_code_post_code_town[x]['postcode_district'])
df['total_occ_rate'] = df['total_occupied'] / df['total_available']
df['general_accute_occ_rate'] = df['general_acute_occupied'] / df['general_acute_available']
df['learning_disabilities_occ_rate'] = df['learning_disabilities_occupied'] / df['learning_disabilities_available']
df['mental_illness_occ_rate'] = df['mental_illness_occupied'] / df['mental_illness_available']
df['maternity_occ_rate'] = df['maternity_occupied'] / df['maternity_available']
df.to_pickle("./data/main.pkl")  # checkpoint

# TODO: get demographic / population data

# get historical weather data
historical_weather_data: dict = []
weather_date_range: list = pd.date_range(
	start=datetime.strptime("2010-06-01", "%Y-%m-%d"),
	end=datetime.strptime("2020-11-01", "%Y-%m-%d"),
	freq='10D'
).tolist()
for org_code in tqdm(org_code_post_code_town):
	print(">>> Processing :", org_code_post_code_town[org_code]['postal_code'])
	payload: dict = {
		"access_key": "f32cccf5ef40b8dda0ab29ed7961d38d",
		"query": "{},{}".format(
			org_code_post_code_town[org_code]['latitude'],
			org_code_post_code_town[org_code]['longitude']
		),
		"historical_date": ';'.join([datetime.strftime(date, "%Y-%m-%d") for date in weather_date_range]),
		"interval": 24
	}
	r = requests.get('https://api.weatherstack.com/historical', params=payload)
	weather_data: dict = r.json()
	# temp => Celsius
	# totalsnow => Centimeters
	# sunhour => hours
	# uv_index => uv index associated with the current weather conditions
	for date_key in weather_data['historical']:
		historical_weather_data.append({
			'date': date_key,
			'postal_code': org_code_post_code_town[org_code]['postal_code'],
			'latitude': org_code_post_code_town[org_code]['latitude'],
			'longitude': org_code_post_code_town[org_code]['longitude'],
			'mintemp': weather_data['historical'][date_key]['mintemp'],
			'maxtemp': weather_data['historical'][date_key]['maxtemp'],
			'avgtemp': weather_data['historical'][date_key]['avgtemp'],
			'totalsnow': weather_data['historical'][date_key]['totalsnow'],
			'sunhour': weather_data['historical'][date_key]['sunhour'],
			'uv_index': weather_data['historical'][date_key]['uv_index']
		})

	weather_df: pd.core.frame.DataFrame = pd.DataFrame.from_dict(historical_weather_data)
	weather_df.to_pickle("./data/weather_df.pkl")  # checkpoint
weather_df = weather_df.drop_duplicates(subset=['date', 'postal_code'])
weather_df['date'] = pd.to_datetime(weather_df['date'])
weather_df['quarter_end'] = weather_df['date'].apply(
	lambda x: datetime.strptime("{}-{}-01".format(x.year, 3*(((x.month-1) // 3)+1)), "%Y-%m-%d")
) + MonthEnd(1)
weather_df.to_pickle("./data/weather_df.pkl")
weather_agg_df: pd.core.frame.DataFrame = weather_df[
	['postal_code', 'quarter_end', 'mintemp', 'maxtemp', 'avgtemp', 'totalsnow', 'sunhour', 'uv_index']
].groupby(
	['postal_code', 'quarter_end']
).mean().reset_index()
weather_agg_df.to_pickle("./data/weather_agg_df.pkl")


# df = pd.read_pickle("./data/main.pkl")
# weather_agg_df = pd.read_pickle("./data/weather_agg_df.pkl")
merge_df = df.merge(
	right=weather_agg_df,
	how='left',
	left_on=['postal_code', 'date'],
	right_on=['postal_code', 'quarter_end'],
	validate='many_to_one'
)
merge_df.to_pickle("./data/merge_df.pkl")

# get macroeconomic data
unemployment_df = pd.read_csv('./data/uk_unemployment_rate.csv')