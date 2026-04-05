import os
from dotenv import load_dotenv
load_dotenv()

from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
import pandas as pd

# load data
df = pd.read_json('data/jobs.json')

# create agent 
agent = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0, model="gpt-4o-mini"),  # model 
    df,  # dataframe 
    verbose=True,  # print the agent's thought process 
    agent_type="openai-tools",  # agent type 
    allow_dangerous_code=True,  # allow dangerous code 
)

question = input("Ask a question about the data: ")
response = agent.invoke(question)
print(response['output'])