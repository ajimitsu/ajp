import pandas as pd
import time
from typing import Callable, List, Dict

class DataFramePipeline:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.steps: List[Dict] = []
        self.report: List[Dict] = []

    def register(self, name: str, enabled: bool = True):
        def decorator(func: Callable):
            self.steps.append({
                "name": name,
                "func": func,
                "enabled": enabled
            })
            return func
        return decorator

    def run(self, verbose: bool = True, profile: bool = True) -> pd.DataFrame:
        for step in self.steps:
            if not step["enabled"]:
                continue

            start_time = time.time()
            old_shape = self.df.shape

            if verbose:
                print(f"\n🔧 Running step: {step['name']}")

            try:
                self.df = step["func"](self.df)
                duration = time.time() - start_time
                new_shape = self.df.shape

                meta = {
                    "step": step["name"],
                    "rows_before": old_shape[0],
                    "rows_after": new_shape[0],
                    "cols_before": old_shape[1],
                    "cols_after": new_shape[1],
                    "duration_sec": round(duration, 4),
                }

                if profile:
                    meta["summary"] = self.df.describe(include="all").to_dict()

                self.report.append(meta)
                if verbose:
                    print(f"✅ Completed in {duration:.4f}s | shape: {old_shape} → {new_shape}")
            except Exception as e:
                print(f"❌ Error in step {step['name']}: {e}")
                raise

        return self.df

df_result = pipeline.run()
pd.DataFrame(pipeline.report).to_csv("pipeline_report.csv", index=False)