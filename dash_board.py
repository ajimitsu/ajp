from dash import Dash, dcc, html, callback, Output, Input
import plotly.express as px
import pandas as pd

# サンプルデータを作成
data = {
    'category': ['tops', 'tops', 'tops', 'bottoms', 'bottoms', 'bottoms'],
    'sub_category': ['t-shirt', 'polo', 'knit', 'denim', 'cargo', 'chino'],
    'value': [10, 20, 15, 25, 20, 30]
}
df = pd.DataFrame(data)

# Dashアプリを作成
app = Dash(__name__)

# レイアウトを定義
app.layout = html.Div([
    html.H1('Sample Dash App'),
    dcc.Dropdown(df.category.unique(), 'tops', id='dropdown'),
    dcc.Graph(
        id='bar-chart',
        figure=px.bar(df, x='sub_category', y='value', title='Sample Bar Chart')
    )
])

# コールバックを定義
@callback(
    Output('bar-chart', 'figure'),
    Input('dropdown', 'value')
)
def update_bar_chart(value):
    dff = df[df.category == value]
    return px.bar(dff, x='sub_category', y='value', title='Sample Bar Chart')

if __name__ == '__main__':
    app.run(debug=True)