from stravalib.client import Client
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash  # (version 1.12.0) pip install dash
import plotly.graph_objects as go
import plotly.express as px  # (version 4.7.0)
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

payload = {
    'client_id': "52298",
    'client_secret': '975598825de77cdd6351013db2e8e86feb4ea889',
    'refresh_token': '5651cdc054b620d8f6614b94e721f8e85ed6a0bf',
    'grant_type': "refresh_token",
    'f': 'json'
}

# ----------------- Get new access token ----------------- #

print("Requesting Token...\n")
res = requests.post(auth_url, data=payload, verify=False)
accesstoken = res.json()['access_token']

# ----------------- Use access token to get data and convert to .csv ----------------- #

client = Client(access_token=accesstoken)  # updating every 6 hours
activities = client.get_activities()
sample = list(activities)[0]
sample.to_dict()

my_cols = ['average_speed',
           'max_speed',
           'average_heartrate',
           'max_heartrate',
           'distance',
           'elapsed_time',
           'moving_time',
           'total_elevation_gain',
           'elev_high',
           'type',
           'start_date_local',
           'start_latitude',
           'start_longitude',
           'kudos_count']
data = []
for activity in activities:
    my_dict = activity.to_dict()
    data.append([my_dict.get(x) for x in my_cols])

df = pd.DataFrame(data, columns=my_cols)
df.to_csv('strava_full_data.csv')
print("File Saved (.csv)")

# ----------------- Start up the app ----------------- #

app = dash.Dash(__name__, external_stylesheets=[
    'https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP
])

# ----------------- Import and clean the data ----------------- #

df = pd.read_csv("strava_full_data.csv")

# Convert to datetime
df['start_date_local'] = pd.to_datetime(df['start_date_local'])
df['elapsed_time'] = pd.to_datetime(df['elapsed_time'])  # .dt.time
df['elapsed_time'] = df['elapsed_time'].dt.hour * \
    60 + df['elapsed_time'].dt.minute
df['moving_time'] = pd.to_datetime(df['moving_time'])  # .dt.time
df['moving_time'] = df['moving_time'].dt.hour * \
    60 + df['moving_time'].dt.minute

# Unit conversions
df['distance'] = df['distance']/1609.344  # Convert m to miles
df[['average_speed', 'max_speed']] = 26.8224 / \
    df[['average_speed', 'max_speed']]  # Convert m/s to min/mile

# Group by weeks with start new week from monday
df_week = df.groupby(
    ['type', pd.Grouper(key='start_date_local', freq='W-SUN', label='left')])['distance'].sum().reset_index().sort_values('start_date_local')

# Create column to bucket distances run
df['Run Length'] = np.nan
df['Run Length'] = np.where(
    df['distance'] < 2, 'Less than 2 miles', df['Run Length'])
df['Run Length'] = np.where((df['distance'] >= 2) & (
    df['distance'] < 4), '2 to 4 miles', df['Run Length'])
df['Run Length'] = np.where((df['distance'] >= 4) & (
    df['distance'] < 7), '4 to 7 miles', df['Run Length'])
df['Run Length'] = np.where(
    df['distance'] >= 7, 'More than 7 miles', df['Run Length'])
df_lengthfreq = df.groupby('Run Length').count()
df_lengthfreq.rename(columns={'Unnamed: 0': 'Frequency'}, inplace=True)
df_lengthfreq = df_lengthfreq['Frequency'].reset_index()

# Create column to bucket run times
df['Run Time'] = np.nan
df['Run Time'] = np.where(df['moving_time'] < 20,
                          'Less than 20 minutes', df['Run Time'])
df['Run Time'] = np.where((df['moving_time'] >= 20) & (
    df['moving_time'] < 40), '20 to 40 minutes', df['Run Time'])
df['Run Time'] = np.where((df['moving_time'] >= 40) & (
    df['moving_time'] < 60), '40 to 60 minutes', df['Run Time'])
df['Run Time'] = np.where(df['moving_time'] > 60,
                          'More than 60 minutes', df['Run Time'])
df_timefreq = df.groupby('Run Time').count()
df_timefreq.rename(columns={'Unnamed: 0': 'Frequency'}, inplace=True)
df_timefreq = df_timefreq['Frequency'].reset_index()

# ----------------- Figs/ Widgets To Be Used In App ----------------- #

# Bar
fig1 = px.bar(df_week, x='start_date_local', y='distance', labels={
    'start_date_local': 'Date', 'distance': 'Miles'}, title='Weekly Miles')

# Scatter
fig2 = px.scatter(x=df['distance'], y=df['average_speed'], labels={
    'x': 'Pace (min/mi)', 'y': 'Distance (mi)'}, title='Intensity (Distance vs. Pace)')
fig2.update_layout(yaxis=dict(autorange="reversed"))

# Pie
fig3 = make_subplots(rows=1, cols=2, specs=[
                     [{'type': 'domain'}, {'type': 'domain'}]])
fig3.add_trace(go.Pie(labels=df_lengthfreq['Run Length'], values=df_lengthfreq['Frequency'], name="Run Lengths"),
               1, 1)
fig3.add_trace(go.Pie(labels=df_timefreq['Run Time'], values=df_timefreq['Frequency'], name="Run Times"),
               1, 2)

# Use `hole` to create a donut-like pie chart
fig3.update_traces(hole=.4, hoverinfo="label+percent+name")

fig3.update_layout(
    title_text="Run Lengths & Times",
    annotations=[dict(text='Lengths', x=0.16, y=0.5, font_size=20, showarrow=False),  # Add annotations in the center of the donut pies.
                 dict(text='Times', x=0.82, y=0.5, font_size=20, showarrow=False)])

# Nav-Bar
# navbar = dbc.Navbar(
#     dbc.Container(
#         [
#             html.A(
#                 # Use row and col to control vertical alignment of logo / brand
#                 dbc.Row(
#                     [
#                         # dbc.Col(html.Img(src=PLOTLY_LOGO, height="30px")),
#                         dbc.Col(dbc.NavbarBrand(
#                             "Running Dashboard", className="ml-2"), height="30px"),
#                     ],
#                     align="center",
#                     no_gutters=True,
#                 ),
#                 href="https://plot.ly",
#             ),
#             dbc.NavbarToggler(id="navbar-toggler2"),
#             dbc.Collapse(
#                 # dbc.Nav(
#                 #     [nav_item,
#                 #      dropdown,
#                 #      ], className="ml-auto", navbar=True
#                 # ),
#                 id="navbar-collapse2",
#                 navbar=True,
#             ),
#         ]
#     ),
#     color="dark",
#     dark=True,
#     className="mb-5",

# )

# ----------------- App Layout ----------------- #

app.layout = html.Div([
    html.Div([
        html.H1("Running Dashboard")
    ], className="banner", style={'text-align': 'center'}),
    html.Div([
        html.Br(),

        dcc.Graph(id='weeklyrunning', figure=fig1),

        dcc.Graph(id='intensity', figure=fig2),

        html.Br(),

        dcc.Graph(id='lengthtime', figure=fig3),
        # html.Div([
        #     html.Div([
        #         dcc.Graph(id='rundistance', figure=fig3, )
        #     ], className="five columns", style={"height": "25%", "width": "30%"}),

        #     html.Div([
        #         dcc.Graph(id='runtime', figure=fig4)
        #     ], className="four columns", style={"height": "25%", "width": "30%"}),

        # ], className="row", style={'textAlign': 'center'})
    ], className='ten columns offset-by-one')
])

# # Boostrap CSS.
# app.css.append_css(
#     {'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})

# ----------------- Connect Plotly Graphs w/ Dash Components ----------------- #

# ----------------- Run App ----------------- #

if __name__ == '__main__':
    app.run_server(debug=True)
