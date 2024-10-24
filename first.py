import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import io
import base64
import plotly.graph_objects as go
#import webbrowser
#from time import sleep

# Créer l'application Dash avec un thème Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Définir une fonction pour déterminer la stratégie
def define_strategy(row):
    if row['Δ_CTR'] > 0 and row['Δ_CVR'] < 0:
        return "Improve CVR"
    elif row['Δ_CVR'] > 0 and row['Δ_CTR'] < 0:
        return "Improve CTR"
    elif row['Δ_CTR'] > 0 and row['Δ_CVR'] > 0:
        return "Improve Traffic"
    else:
        return "Reduce Traffic"
    
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

app.layout = dbc.Container([
    dcc.Tabs([
        dcc.Tab(label="Import Data", children=[
            html.H2("Raw data arranged by query score"),
            dcc.Upload(
                id='upload-data',
                children=dbc.Button('Import Data', color='primary'),
                multiple=True
            ),
            html.Div(id='output-data-upload'),
        ]),
        dcc.Tab(label="Focus on a Keyword", children=[
            html.H2("Focus on a Keyword"),
            dcc.Dropdown(id='query-dropdown', options=[], placeholder="Choisissez une Search Query"),
            dcc.Dropdown(id='date-dropdown', options=[], placeholder="Choisissez une Reporting Date", style={'margin-top': '20px', 'margin-bottom': '20px'}),
            html.Div(id='kpi-display', style={'display': 'flex', 'justify-content': 'space-around', 'margin-bottom': '20px'}),
            dcc.Graph(id='funnel-chart'),
            html.Div(id='clicks_kpi', style={'display': 'flex', 'justify-content': 'flex-start', 'margin-bottom': '20px'}),
            html.Div(id='kpi_section'),
            dcc.Graph(id='delta-chart')
        ])
    ]),
    dcc.Store(id='stored-data')
], fluid=True)

# Callback pour traiter les fichiers téléchargés et stocker les données dans dcc.Store
@app.callback(
    [Output('output-data-upload', 'children'),
     Output('stored-data', 'data'),
     Output('query-dropdown', 'options'),
     Output('date-dropdown', 'options')],
    Input('upload-data', 'contents')
)
def update_table(contents):
    if contents is None:
        return None, None, [], []

    dfs = []  # Liste pour stocker les DataFrames lus à partir de chaque fichier

    for content in contents:
        # Lire le contenu de chaque fichier téléchargé
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), skiprows=1)

        # Convertir la colonne "Reporting Date" en datetime
        df['Reporting Date'] = pd.to_datetime(df['Reporting Date'], errors='coerce')

        dfs.append(df)  # Ajouter le DataFrame à la liste

    # Concaténer tous les DataFrames en un seul (hypothèse: même colonnes dans chaque fichier)
    combined_df = pd.concat(dfs, ignore_index=True)

    # Calculer les variables supplémentaires sur le DataFrame combiné
    combined_df['Market_CTR'] = combined_df["Clicks: Total Count"] / combined_df["Impressions: Total Count"] 
    combined_df["Brand_CTR"] = combined_df["Clicks: Brand Count"] / combined_df["Impressions: Brand Count"]  
    combined_df["Δ_CTR"] = combined_df["Brand_CTR"] - combined_df["Market_CTR"]

    combined_df['Market_CVR'] = combined_df["Purchases: Total Count"] / combined_df["Clicks: Total Count"] / 
    combined_df["Brand_CVR"] = combined_df["Purchases: Brand Count"] / combined_df["Clicks: Brand Count"] / 
    combined_df["Δ_CVR"] = combined_df["Brand_CVR"] - combined_df["Market_CVR"]

    combined_df['strategy'] = combined_df.apply(define_strategy, axis=1)
    combined_df = combined_df.round(1)

    # Convertir le dataframe combiné en table HTML stylisée avec Bootstrap
    table = dbc.Table.from_dataframe(combined_df, striped=True, bordered=True, hover=True, dark=True)

    # Mettre à jour les options du dropdown pour la Search Query
    dropdown_options = [{'label': query, 'value': query} for query in combined_df['Search Query'].unique()]

    # Mettre à jour les options du dropdown pour les dates
    date_options = [{'label': date.strftime('%Y-%m-%d'), 'value': date.strftime('%Y-%m-%d')} for date in combined_df['Reporting Date'].unique()]

    # Stocker le dataframe combiné sous forme de dictionnaire
    return table, combined_df.to_dict('records'), dropdown_options, date_options


# Callback pour mettre à jour les KPIs, le graphique et les statistiques sur les clics
@app.callback(
    [Output('kpi-display', 'children'),
     Output('funnel-chart', 'figure'),
     Output('kpi_section', 'children'),
     Output('delta-chart', 'figure')],
    [Input('query-dropdown', 'value'),
     Input('date-dropdown', 'value'),
     Input('stored-data', 'data')]
)
def update_kpi_funnel(selected_query, selected_date, data):
    if selected_query is None or selected_date is None or data is None:
        return None, go.Figure(), None, go.Figure()

    df = pd.DataFrame(data)

    # Filtrer les données en fonction de la Search Query sélectionnée et de la date
    df['Reporting Date'] = pd.to_datetime(df['Reporting Date'], errors='coerce')
    filtered_df = df[(df['Search Query'] == selected_query) & (df['Reporting Date'] == pd.to_datetime(selected_date))]
    df_graph = df[(df['Search Query'] == selected_query)]

    # Si le DataFrame filtré est vide, retourner une valeur par défaut
    if filtered_df.empty:
        return None, go.Figure(), None, go.Figure()

    filtered_df = filtered_df.iloc[0]

    # Définir les KPIs avec les icônes et le style modifié
    kpi_layout = [
        html.Div([
            html.H4("Impressions", style={'text-align': 'center'}),
            html.P("📊", style={'font-size': '32px', 'text-align': 'center'}),
            html.Div([
                html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'center'}),
                html.P(f"{filtered_df['Impressions: Total Count']:,}", style={
                    'font-size': '24px', 'color': 'blue', 'text-align': 'center',
                    'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'center'}),
                html.P(f"{filtered_df['Impressions: Brand Count']:,}", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P(f"{filtered_df['Impressions: Brand Share %']:,}"+" %", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ])
        ], style={'display': 'inline-block', 'width': '24%', 'margin': '10px'}),

        html.Div([
            html.H4("Clicks", style={'text-align': 'center'}),
            html.P("👆", style={'font-size': '32px', 'text-align': 'center'}),
            html.Div([
                html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'center'}),
                html.P(f"{filtered_df['Clicks: Total Count']:,}", style={
                    'font-size': '24px', 'color': 'blue', 'text-align': 'center',
                    'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'center'}),
                html.P(f"{filtered_df['Clicks: Brand Count']:,}", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P(f"{filtered_df['Clicks: Brand Share %']:,}"+" %", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ])

        ], style={'display': 'inline-block', 'width': '24%', 'margin': '10px'}),

        html.Div([
            html.H4("Basket Adds", style={'text-align': 'center'}),
            html.P("🛒", style={'font-size': '32px', 'text-align': 'center'}),
            html.Div([
                html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'center'}),
                html.P(f"{filtered_df['Basket Adds: Total Count']:,}", style={
                    'font-size': '24px', 'color': 'blue', 'text-align': 'center',
                    'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'center'}),
                html.P(f"{filtered_df['Basket Adds: Brand Count']:,}", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P(f"{filtered_df['Basket Adds: Brand Share %']:,}"+" %", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ])

        ], style={'display': 'inline-block', 'width': '24%', 'margin': '10px'}),

        html.Div([
            html.H4("Purchases", style={'text-align': 'center'}),
            html.P("💳", style={'font-size': '32px', 'text-align': 'center'}),
            html.Div([
                html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'center'}),
                html.P(f"{filtered_df['Purchases: Total Count']:,}", style={
                    'font-size': '24px', 'color': 'blue', 'text-align': 'center',
                    'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'center'}),
                html.P(f"{filtered_df['Purchases: Brand Count']:,}", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ]),
            html.Div([
                html.P(f"{filtered_df['Purchases: Brand Share %']:,}"+" %", style={
                    'font-size': '24px', 'color': 'green', 'text-align': 'center',
                    'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
            ])

        ], style={'display': 'inline-block', 'width': '24%', 'margin': '10px'}),
    ]

    # Créer le funnel chart
    funnel_chart = go.Figure()
    funnel_chart.add_trace(go.Funnel(
        y=["Impressions Brand", "Clicks", "Basket Adds", "Purchases"],
        x=[
            filtered_df["Impressions: Brand Share %"],
            filtered_df["Clicks: Brand Share %"], 
            filtered_df["Basket Adds: Brand Share %"], 
            filtered_df["Purchases: Brand Share %"]],
        textinfo="value"))

    funnel_chart.update_traces(marker=dict(color=['blue', 'orange', 'green', 'red']))

    # Créer les statistiques sur les clics
    clicks_kpi = [
        html.Div([
            html.Div([
                html.H4("Clicks", style={'text-align': 'left'}),
                html.P("👆", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: Click Rate %']:.2f}%", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: Brand Share %']:.2f}%", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                

            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top', 'margin-right': '10px'}),
            
            html.Div([
                html.H4("Price", style={'text-align': 'left'}),
                html.P("💰", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: Price (Median)']:,}", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: Brand Price (Median)']:,}", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Difference", style={'font-size': '16px', 'color': 'red', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: Price (Median)'] - filtered_df['Clicks: Brand Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'red', 'text-align': 'left',
                        'border': '2px solid red', 'padding': '10px', 'border-radius': '5px'}),
                ]),
            ], style={'display': 'inline-block', 'width': '45%', 'vertical-align': 'top', 'margin-right': '10px'}),

            html.Div([
                html.H4("Shipping", style={'text-align': 'left'}),
                html.P("🚚", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Same-Day", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: Same-Day Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("1D Shipping", style={'font-size': '16px', 'color': 'orange', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: 1D-Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'orange', 'text-align': 'left',
                        'border': '2px solid orange', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("2D Shipping", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Clicks: 2D-Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
            ], style={'display': 'inline-block', 'width': '45%', 'vertical-align': 'top'}),
        ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'stretch', 'margin': '10px'})
    ]

    # Créer les statistiques sur le panier
    basket_kpi = [
        html.Div([
            html.Div([
                html.H4("Add to Basket", style={'text-align': 'left'}),
                html.P("🛒", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: Basket Add Rate %']:.2f}%", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: Brand Share %']:.2f}%", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),

            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top', 'margin-right': '10px'}),

            html.Div([
                html.H4("Price", style={'text-align': 'left'}),
                html.P("💰", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: Brand Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Difference", style={'font-size': '16px', 'color': 'red', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: Price (Median)'] - filtered_df['Basket Adds: Brand Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'red', 'text-align': 'left',
                        'border': '2px solid red', 'padding': '10px', 'border-radius': '5px'}),
                ])
            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top', 'margin-right': '10px'}),

            html.Div([
                html.H4("Shipping", style={'text-align': 'left'}),
                html.P("🚚", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Same-Day", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: Same-Day Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("1D Shipping", style={'font-size': '16px', 'color': 'orange', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: 1D-Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'orange', 'text-align': 'left',
                        'border': '2px solid orange', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("2D Shipping", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Basket Adds: 2D-Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top'}),
        ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'stretch', 'margin': '10px'})
    ]

    # Créer les statistiques sur les achats (Purchases)
    purchases_kpi = [
        html.Div([
            html.Div([
                html.H4("Purchases", style={'text-align': 'left'}),
                html.P("💳", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: Purchase Rate %']:.2f}%", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: Brand Share %']:.2f}%", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top', 'margin-right': '10px'}),

            html.Div([
                html.H4("Price", style={'text-align': 'left'}),
                html.P("💰", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Total", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Brand", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: Brand Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("Difference", style={'font-size': '16px', 'color': 'red', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: Price (Median)'] - filtered_df['Purchases: Brand Price (Median)']:.2f}", style={
                        'font-size': '24px', 'color': 'red', 'text-align': 'left',
                        'border': '2px solid red', 'padding': '10px', 'border-radius': '5px'}),
                ])
            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top', 'margin-right': '10px'}),

            html.Div([
                html.H4("Shipping", style={'text-align': 'left'}),
                html.P("🚚", style={'font-size': '32px', 'text-align': 'left'}),
                html.Div([
                    html.P("Same-Day", style={'font-size': '16px', 'color': 'blue', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: Same-Day Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'blue', 'text-align': 'left',
                        'border': '2px solid blue', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("1D Shipping", style={'font-size': '16px', 'color': 'orange', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: 1D-Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'orange', 'text-align': 'left',
                        'border': '2px solid orange', 'padding': '10px', 'border-radius': '5px'}),
                ]),
                html.Div([
                    html.P("2D Shipping", style={'font-size': '16px', 'color': 'green', 'text-align': 'left'}),
                    html.P(f"{filtered_df['Purchases: 2D-Shipping Speed']:,}", style={
                        'font-size': '24px', 'color': 'green', 'text-align': 'left',
                        'border': '2px solid green', 'padding': '10px', 'border-radius': '5px'}),
                ]),
            ], style={'display': 'inline-block', 'width': '30%', 'vertical-align': 'top'}),
        ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'stretch', 'margin': '10px'})
    ]

    # Conteneur pour afficher les sections clicks_kpi, basket_kpi et purchases_kpi côte à côte
    kpi_section = html.Div([
        html.Div([
            html.H2("1. Statistics on clicks", style={'width': '100%', 'text-align': 'left'}),
            html.Div(clicks_kpi, style={'width': '100%'})  
        ], style={'width': '33%', 'padding': '10px'}),

        html.Div([
            html.H2("2. Statistics on basket", style={'width': '100%', 'text-align': 'left'}),
            html.Div(basket_kpi, style={'width': '100%'})  
        ], style={'width': '33%', 'padding': '10px'}),

        html.Div([
            html.H2("3. Statistics on purchases", style={'width': '100%', 'text-align': 'left'}),
            html.Div(purchases_kpi, style={'width': '100%'})  
        ], style={'width': '33%', 'padding': '10px'}),
    ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'stretch', 'margin': '10px'})
    
    # Créer le graphique pour Δ_CTR et Δ_CVR en fonction de Reporting Date
    delta_chart = go.Figure()

    delta_chart.add_trace(go.Scatter(
       x=df_graph['Reporting Date'],
       y=df_graph['Δ_CTR'],
       mode='lines+markers',
       name='Δ_CTR',
       line=dict(color='blue')
       ))

    delta_chart.add_trace(go.Scatter(
       x=df_graph['Reporting Date'],
       y=df_graph['Δ_CVR'],
       mode='lines+markers',
       name='Δ_CVR',
       line=dict(color='green')
   ))

    delta_chart.update_layout(
       title='Δ_CTR & Δ_CVR evolutions',
       xaxis_title='Date',
       yaxis_title='Δ Value',
       legend=dict(x=0, y=1),
       margin=dict(l=0, r=0, t=30, b=0),
       height=400
   )

    return kpi_layout, funnel_chart, kpi_section, delta_chart


# Lancer l'application
if __name__ == '__main__':
    #sleep(4)
    #open_browser()
    app.run_server(debug=True)
