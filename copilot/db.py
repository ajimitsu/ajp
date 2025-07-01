import pandas as pd

df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
df.to_feather("data.feather")

df2 = pd.read_feather("data.feather")

import pickle

data = {"x": [1, 2, 3], "y": (4, 5)}
with open("data.pkl", "wb") as f:
    pickle.dump(data, f)

with open("data.pkl", "rb") as f:
    loaded = pickle.load(f)

import pandas as pd

df = pd.DataFrame({"temp": [20.1, 19.8], "time": [1, 2]})
df.to_hdf("data.h5", key="experiment", mode="w")

df2 = pd.read_hdf("data.h5", key="experiment")