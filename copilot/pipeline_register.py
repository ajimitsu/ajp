import pandas as pd
from functools import wraps
from typing import Callable

class DataFramePipeline:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.steps = []

    def register(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(df: pd.DataFrame):
            return func(df)
        self.steps.append(wrapper)
        return wrapper

    def run(self) -> pd.DataFrame:
        for step in self.steps:
            self.df = step(self.df)
        return self.df

df = pd.DataFrame({
    "name": ["Ren", "Yuki", "Mitsu"],
    "age": [22, 35, 29],
    "score": [88, 77, 92]
})

pipeline = DataFramePipeline(df)

@pipeline.register
def add_status(df):
    df["status"] = df["score"].apply(lambda x: "pass" if x >= 60 else "fail")
    return df

@pipeline.register
def categorize_age(df):
    df["age_group"] = pd.cut(df["age"], [0, 25, 65], labels=["young", "adult"])
    return df

@pipeline.register
def normalize_score(df):
    df["score_z"] = (df["score"] - df["score"].mean()) / df["score"].std()
    return df

df_result = pipeline.run()
print(df_result)