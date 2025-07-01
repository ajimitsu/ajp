import numpy as np
df["status"] = np.where(df["score"] >= 60, "pass", "fail")

df = (
    df.assign(ratio=lambda x: x["math"] / x["english"])
      .assign(score_label=lambda x: np.where(x["ratio"] > 1, "mathy", "wordy"))
)

def categorize(row):
    if row["age"] < 18:
        return "minor"
    elif row["age"] <= 65:
        return "adult"
    else:
        return "senior"

df["age_group"] = df.apply(categorize, axis=1)


df["abbrev_gender"] = df["gender"].map({"male": "M", "female": "F"})

for row in df.itertuples(index=False):
    print(f"{row.name} - Age: {row.age}")


import pandas as pd
import numpy as np

class DataFramePipeline:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def filter_adults(self):
        self.df = self.df[self.df["age"] >= 18]
        return self

    def add_status(self):
        self.df["status"] = np.where(self.df["score"] >= 60, "pass", "fail")
        return self

    def normalize_score(self):
        mean = self.df["score"].mean()
        std = self.df["score"].std()
        self.df["score_z"] = (self.df["score"] - mean) / std
        return self

    def to_df(self):
        return self.df

df = pd.DataFrame({
    "name": ["Aoi", "Ren", "Yuki", "Mitsu"],
    "age": [15, 22, 35, 29],
    "score": [58, 88, 77, 92]
})

df_processed = (
    DataFramePipeline(df)
    .filter_adults()
    .add_status()
    .normalize_score()
    .to_df()
)

print(df_processed)