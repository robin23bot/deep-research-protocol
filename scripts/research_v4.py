#!/usr/bin/env python3
import os
import json
import argparse
import asyncio
import aiohttp
from typing import List, Dict

# Keys are pulled from environment
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

class DeepResearchCLI:
    def __init__(self, model="o4-mini"):
        self.model = model
        self.openai_url = "https://api.openai.com/v1/responses"
        self.tavily_url = "https://api.tavily.com/search"
        self.serper_url = "https://google.serper.dev/search"

    async def generate_outline(self, topic: str, session: aiohttp.ClientSession) -> List[Dict]:
        """Deconstruct topic into a 5-10 section research plan."""
        payload = {
            "model": self.model,
            "input": f"You are a Research Director. Deconstruct '{topic}' into a detailed 6-10 section report outline. Each section should have a title and a specific research objective. Return ONLY a JSON list of objects with 'title' and 'objective' keys."
        }
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        async with session.post(self.openai_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            text = data['output'][1]['content'][0]['text']
            clean_json = text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)

    async def research_section(self, section: Dict, session: aiohttp.ClientSession) -> str:
        """Perform targeted research and synthesis for a specific section."""
        print(f"📖 Researching: {section['title']}")
        # Fan-out search for this specific objective
        t_task = self.search_tavily(section['objective'], session)
        s_task = self.search_serper(section['objective'], session)
        results = await asyncio.gather(t_task, s_task)
        sources = [item for sublist in results for item in sublist]
        
        # Synthesize just this chapter
        context_str = "\n".join([f"Source: {s.get('url') or s.get('link')}\nContent: {s.get('content') or s.get('snippet')}" for s in sources[:15]])
        payload = {
            "model": self.model,
            "input": f"You are a Specialist Researcher. Write a detailed, multi-page depth chapter for the section: '{section['title']}'. \n\nObjective: {section['objective']}\n\nSources:\n{context_str}\n\nRequirements: Use professional, high-density language. Cite every claim. Include tables if data is present."
        }
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        async with session.post(self.openai_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            return f"\n\n# {section['title']}\n\n" + data['output'][1]['content'][0]['text']

    async def search_tavily(self, query: str, session: aiohttp.ClientSession) -> List[Dict]:
        if not TAVILY_KEY: return []
        payload = {"api_key": TAVILY_KEY, "query": query, "search_depth": "advanced", "max_results": 10}
        async with session.post(self.tavily_url, json=payload) as resp:
            data = await resp.json()
            return data.get("results", [])

    async def search_serper(self, query: str, session: aiohttp.ClientSession) -> List[Dict]:
        if not SERPER_KEY: return []
        headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": 20}
        async with session.post(self.serper_url, headers=headers, json=payload) as resp:
            data = await resp.json()
            return data.get("organic", [])

    async def run(self, topic: str):
        async with aiohttp.ClientSession() as session:
            print(f"🚀 Starting HIGH-FIDELITY Deep Research: {topic}")
            outline = await self.generate_outline(topic, session)
            print(f"📋 Generated {len(outline)}-section research plan.")
            
            # PARALLEL CHAPTER RESEARCH
            tasks = [self.research_section(section, session) for section in outline]
            chapters = await asyncio.gather(*tasks)
            
            full_report = f"# Master Report: {topic}\n\n" + "\n\n".join(chapters)
            filename = topic.lower().replace(" ", "_") + "_full_v4.md"
            with open(filename, "w") as f:
                f.write(full_report)
            
            print(f"✅ Master Synthesis complete! Saved to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("topic")
    args = parser.parse_args()
    asyncio.run(DeepResearchCLI().run(args.topic))
