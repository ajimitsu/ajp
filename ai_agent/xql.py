import os
# 【変更点1】ライブラリをOpenAIからGoogleに変更
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# APIキーの設定（Google AI Studioで取得したもの）
# 環境変数にセットするのが鉄則だが、ここではわかりやすく直接書く場所も示しておく
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyDb9-An1ffE-9XhySD0CqzwZMyJGUqAAag"

# 【変更点2】脳みそをGeminiに換装
# model="gemini-1.5-pro" (賢い) または "gemini-1.5-flash" (爆速)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# --- ここから下はOpenAIの時と 1文字も 変える必要はない ---
# これがLangChainというフレームワークの「科学的勝利」だ。

# 1. 独自の言語ルールと、数パターンの「正解データ」を定義する
sdl_spec = """
[SDL Specification]
1. Need to define JOB block(s) and SCENARIO block(s)
2. To define a job name in a JOB block, use JOB = <job name>
3. To define a scenario name in a SCENARIO block, use SCENARIO = <scenario name>
4. Each job and scenario block should be enclosed by {{}}
5. To define a scenario, provide 3 items by ":". First item is WHICH, and second item is WHAT, and third item is WHEN.
6. WHAT should include operation and the value on the operation. The available operation types are RISE, RISES, FALL, FALLS, SET, KEEP. The value can % or BP.

[Examples]
User: Bump all curves by 1 % parallel shift as of today 
AI: ALL : RISES 1% : TODAY

User: Bump IR curves only with -1% parallel shift as of today
AI: AssetClass = IR : FALL 1% : TODAY

User: Bump IR curves by grid with 1BP shift as of today
AI: AssetClass = IR : RISE 1BP BY tenor : TODAY

User: Bump IR and FX curves with -1% shift as of today with the scenario name as IRFX_bump
AI: SCENARIO = IRFX_bump
    {{
        AssetClass = IR : RISES 1% : TODAY  
        AssetClass = FX : RISE 1% : TODAY
    }} 
"""

# 2. プロンプトに埋め込む
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a SDL expertise. Please generate a SDL scenario according to these rules: \n\n" + sdl_spec),
    ("human", "{input}"),
])

# 3.
chain = prompt | llm

# Teet
print("--- Gemini Response ---")
try:
    # Let's try your FX query
    query = "Bump IR and CR curves with 1bp by grid as of -3D with the scenario name as IRCRBump and the job name as SDLExample1"
    print(f"Input: {query}")

    response = chain.invoke({"input": query})
    print(f"Output: {response.content}")

except Exception as e:
    print(f"Training Injury (Error): {e}")