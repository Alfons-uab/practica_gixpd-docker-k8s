import os
import numpy as np

from sklearn.metrics import r2_score

MODEL_PATH = os.environ["MODEL_PATH"]

np.random.seed(2)

x = np.random.normal(3, 1, 100)
y = np.random.normal(150, 40, 100) / x

train_x = x[:80]
train_y = y[:80]

test_x = x[80:]
test_y = y[80:]

# V2: canviem el grau del polinomi de 4 a 2
mymodel = np.poly1d(np.polyfit(train_x, train_y, 2))

print("Model V2 trained successfully")

r2 = r2_score(test_y, mymodel(test_x))
print("Model V2 Score:", r2)

np.save(MODEL_PATH, mymodel)

