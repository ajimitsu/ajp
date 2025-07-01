import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error

# Sample dataset
data = {
    'Bedrooms': [2, 3, 4, 3, 5],
    'Bathrooms': [1, 2, 2, 1, 3],
    'Size_sqft': [1000, 1500, 1800, 1200, 2500],
    'Price': [200000, 300000, 400000, 250000, 500000]
}

df = pd.DataFrame(data)

# Features and target
X = df[['Bedrooms', 'Bathrooms', 'Size_sqft']]
y = df['Price']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = LinearRegression()
model.fit(X_train, y_train)

# Predict
y_pred = model.predict(X_test)

# Results
print("Coefficients:", model.coef_)
print("Intercept:", model.intercept_)
print("R² score:", r2_score(y_test, y_pred))
print("MSE:", mean_squared_error(y_test, y_pred))