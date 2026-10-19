import os

import joblib
import numpy as np

from sklearn.metrics import r2_score
from sklearn.tree import DecisionTreeRegressor


MODEL_PATH = os.environ["MODEL_PATH"]

np.random.seed(2)

x = np.random.normal(3, 1, 100)
y = np.random.normal(150, 40, 100) / x

train_x = x[:80].reshape(-1, 1)
train_y = y[:80]

test_x = x[80:].reshape(-1, 1)
test_y = y[80:]


model = DecisionTreeRegressor(
    max_depth=3,
    random_state=2
)

model.fit(train_x, train_y)

print("Custom Decision Tree model trained successfully")

predictions = model.predict(test_x)

r2 = r2_score(test_y, predictions)

print("Custom Model Score:", r2)

joblib.dump(model, MODEL_PATH)

print("Custom model saved to:", MODEL_PATH)

