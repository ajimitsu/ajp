import pandas as pd
import numpy as np

class DataFramePipeline:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def filter_adults(self):
        return self._wrap(self.df[self.df["age"] >= 18])

    def add_status(self):
        df = self.df.copy()
        df["status"] = np.where(df["score"] >= 60, "pass", "fail")
        return self._wrap(df)

    def normalize_score(self):
        df = self.df.copy()
        mean = df["score"].mean()
        std = df["score"].std()
        df["score_z"] = (df["score"] - mean) / std
        return self._wrap(df)

    def to_df(self):
        return self.df

    def _wrap(self, df_new: pd.DataFrame):
        return DataFramePipeline(df_new)

def categorize_age(df):
    df["age_group"] = pd.cut(df["age"], [0, 17, 65, 100], labels=["minor", "adult", "senior"])
    return df

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
    .pipe(categorize_age)
)

print(df_processed)