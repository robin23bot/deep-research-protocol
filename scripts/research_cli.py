#!/usr/bin/env python3
import os
import json
import argparse
import asyncio
import aiohttp
from typing import List, Dict

# Keys are pulled from environment (set from .env in main agent)
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

class DeepResearchCLI:
    def __init__(self, model="o4-mini"):
        self.model = model
        self.openai_url = "https://api.openai.com/v1/responses"
        self.tavily_url = "https://api.tavily.com/search"
        self.serper_url = "https://google.serper.dev/search"

    async def generate_queries(self, topic: str, session: aiohttp.ClientSession) -> List[str]:
        """Use OpenAI to generate 4 specialized sub-queries for fan-out."""
        payload = {
            "model": self.model,
            "input": f"Act as a Research Planner. Decompose this topic into 4 distinct, high-signal search queries for a deep research task: '{topic}'. Return ONLY a JSON list of strings."
        }
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        try:
            async with session.post(self.openai_url, json=payload, headers=headers) as resp:
                data = await resp.json()
                text = data['output'][0]['content'][0]['text']
                # Clean markdown if present
                clean_json = text.replace('```json', '').replace('```', '').strip()
                return json.loads(clean_json)
        except Exception as e:
            print(f"Query generation failed: {e}. Using fallback.")
            return [topic]

    async def search_tavily(self, query: str, session: aiohttp.ClientSession) -> List[Dict]:
        if not TAVILY_KEY: return []
        payload = {
            "api_key": TAVILY_KEY,
            "query": query,
            "search_depth": "advanced",
            "max_results": 20,
            "include_raw_content": True
        }
        try:
            async with session.post(self.tavily_url, json=payload) as resp:
                data = await resp.json()
                return data.get("results", [])
        except: return []

    async def search_serper(self, query: str, session: aiohttp.ClientSession) -> List[Dict]:
        if not SERPER_KEY: return []
        headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": 50}
        try:
            async with session.post(self.serper_url, headers=headers, json=payload) as resp:
                data = await resp.json()
                return data.get("organic", [])
        except: return []

    async def synthesize_report(self, topic: str, sources: List[Dict], session: aiohttp.ClientSession) -> str:
        """Map-Reduce: Send all filtered source snippets to OpenAI for final synthesis."""
        # Simple Map-Reduce: Just send the high-signal snippets for now
        context_str = ""
        for s in sources[:40]: # Limit to top 40 for context window safety
            title = s.get('title', 'No Title')
            content = s.get('content') or s.get('snippet', '')
            url = s.get('url') or s.get('link', '')
            context_str += f"SOURCE: {title}\nURL: {url}\nCONTENT: {content}\n\n---\n"

        payload = {
            "model": self.model,
            "input": f"You are a Senior Researcher. Synthesize a professional, comprehensive report on '{topic}' based on these sources. Use high-density information, clear sections (Executive Summary, Findings, Outlook), and markdown formatting. Cite every claim with the URL provided. \n\nSOURCES:\n{context_str}"
        }
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        try:
            async with session.post(self.openai_url, json=payload, headers=headers) as resp:
                data = await resp.json()
                return data['output'][0]['content'][0]['text']
        except Exception as e:
            return f"Synthesis failed: {e}"

    async def run(self, topic: str):
        async with aiohttp.ClientSession() as session:
            print(f"🚀 Starting Deep Research: {topic}")
            
            print("🧠 Generating sub-queries...")
            queries = await self.generate_queries(topic, session)
            
            print(f"📡 Fanning out across {len(queries)} parallel search tasks...")
            search_tasks = []
            for q in queries:
                search_tasks.append(self.search_tavily(q, session))
                search_tasks.append(self.search_serper(q, session))
            
            search_results = await asyncio.gather(*search_tasks)
            
            print("🧹 Deduplicating and filtering sources...")
            flat_results = [item for sublist in search_results for item in sublist]
            unique_sources = {}
            for res in flat_results:
                url = res.get("url") or res.get("link")
                if url and url not in unique_sources:
                    unique_sources[url] = res
            
            # Filter for relevance score if available (Tavily)
            final_sources = list(unique_sources.values())
            
            print(f"📝 Synthesizing report from {len(final_sources)} sources...")
            report = await self.synthesize_report(topic, final_sources, session)
            
            output_file = topic.lower().replace(" ", "_") + "_report.md"
            with open(output_file, "w") as f:
                f.write(report)
            
            print(f"✅ Research complete! Report saved to {output_file}")
            print("\nREPORT PREVIEW:\n")
            print(report[:500] + "...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", help="The topic to research")
    args = parser.parse_args()
    
    cli = DeepResearchCLI()
    asyncio.run(cli.run(args.topic))
