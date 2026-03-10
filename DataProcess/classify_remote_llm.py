import pandas as pd
import os
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class PlaceStats(BaseModel):
    romance: int = Field(description="How romantic is this place? 1 (not at all) to 5 (perfect for couples)")
    family: int = Field(
        description="How family-friendly is it? 1 (not recommended for kids) to 5 (perfect for families)")
    cost: int = Field(description="Price level: 1 (very cheap/backpacking) to 5 (luxury/expensive)")
    nature: int = Field(description="Connection to nature: 1 (purely urban) to 5 (wild nature/scenic)")
    adventure: int = Field(description="Adventure level: 1 (chill/easy) to 5 (extreme/challenging)")
    culture: int = Field(description="Cultural/Historical significance: 1 (modern) to 5 (rich history/tradition)")
    relaxation: int = Field(description="Relaxation level: 1 (busy/hectic) to 5 (peaceful/calm)")
    service: int = Field(description="Quality of services/facilities: 1 (none/basic) to 5 (excellent)")
    accessibility: int = Field(
        description="How accessible is it? 1 (hard to reach/stairs) to 5 (wheelchair/stroller friendly)")
    crowded: int = Field(description="How crowded is it typically? 1 (empty/hidden gem) to 5 (very touristy/packed)")

    short_summary: str = Field(description="A 1-sentence summary of the place based on these stats")

llm = Ollama(model="llama3.2:3b", format="json", temperature=0)
parser = JsonOutputParser(pydantic_object=PlaceStats)

prompt = ChatPromptTemplate.from_template(
    "Analyze the following travel description and return ONLY a JSON object.\n"
    "Description: {description}\n"
    "{format_instructions}"
)

chain = prompt | llm | parser


def process_all_csvs(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")

                df = pd.read_csv(file_path)
                enriched_data = []

                for index, row in df.iterrows():
                    try:
                        print(f"  Classifying: {row['place']}...")
                        response = chain.invoke({
                            "description": row['combined_description'],
                            "format_instructions": parser.get_format_instructions()
                        })

                        full_row = {**row.to_dict(), **response}
                        enriched_data.append(full_row)
                    except Exception as e:
                        print(f"  Error on {row['place']}: {e}")
                        continue

                new_df = pd.DataFrame(enriched_data)
                new_df.to_csv(file_path.replace(".csv", "_enriched.csv"), index=False)

process_all_csvs("../Unified_Countries")
