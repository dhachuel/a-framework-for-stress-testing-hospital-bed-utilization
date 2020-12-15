# environment setup
import seaborn as sns; sns.set_theme()
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthEnd
import requests
from tqdm import tqdm
from datetime import datetime


df = pd.read_pickle("./data/main.pkl")
weather_df = pd.read_pickle("./data/weather_df.pkl")
weather_agg_df = pd.read_pickle("./data/weather_agg_df.pkl")
merge_df = pd.read_pickle("./data/merge_df.pkl")


merge_df[merge_df['org_code']=='RJ1'].plot.line(
	x='date',
	y='total_occ_rate'
)
plt.show()

merge_df[merge_df['org_code']=='RYJ'].plot.line(
	x='date',
	y='total_occ_rate'
)


merge_df.plot.scatter(
	x='avgtemp',
	y='total_occ_rate',
	c='date'
)
plt.title('Total Occupancy Rate (%) vs. Average Local Temperature (Celsius)')
# plt.show()
plt.savefig('./assets/total_occ_rate_vs_avgtemp.png', dpi=300)


sns.kdeplot(data=merge_df, x="total_occ_rate", hue='period')
plt.title('Total Occupancy Rate (%) Density vs. Time of Year')
plt.savefig('./assets/total_occ_rate__density_vs_period.png', dpi=300)

corr = merge_df[[
	'total_occ_rate',
	'general_accute_occ_rate',
	'learning_disabilities_occ_rate',
	'mental_illness_occ_rate',
	'maternity_occ_rate',
	'mintemp',
	'maxtemp',
	'avgtemp',
	'totalsnow',
	'sunhour',
	'uv_index'
]].corr()
mask = np.zeros_like(corr)
mask[np.triu_indices_from(mask)] = True
sns.heatmap(corr, annot=True, mask=mask, square=True)
plt.title("Pearson Correlations for Overnight Bed Occupancy Rates and Historical Weather")
plt.show()
plt.savefig('./assets/weather_corr_plot.png', dpi=300)
