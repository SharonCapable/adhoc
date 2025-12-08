from src.research_tools import ResearchTools
import json

def run():
    try:
        tools = ResearchTools('ollama')
        results = tools.search_web(
            "can we detect the gender of oil palm trees using aerial imagery... maybe by spectral signatures?",
            num_results=3
        )
        print(json.dumps(results, indent=2))
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run()
