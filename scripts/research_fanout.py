#!/usr/bin/env python3
import os
import json
import argparse
import requests
import asyncio
import aiohttp
from typing import List, Dict

# Keys are pulled from .env or environment
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

async def search_tavily(query: str, session: aiohttp.ClientSession) -> List[Dict]:
    if not TAVILY_KEY: return []
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": 20,
        "include_raw_content": True
    }
    try:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            return data.get("results", [])
    except:
        return []

async def search_serper(query: str, session: aiohttp.ClientSession) -> List[Dict]:
    if not SERPER_KEY: return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 50}
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()
            return data.get("organic", [])
    except:
        return []

async def run_parallel_research(topic: str, sub_queries: List[str]):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for q in sub_queries:
            tasks.append(search_tavily(q, session))
            tasks.append(search_serper(q, session))
        
        results = await asyncio.gather(*tasks)
        # Flatten and deduplicate
        flat_results = [item for sublist in results for item in sublist]
        unique_results = {res.get("url") or res.get("link"): res for res in flat_results if res.get("url") or res.get("link")}
        
        print(json.dumps(list(unique_results.values()), indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("topic")
    parser.add_argument("--queries", nargs="+", help="Sub-queries for fan-out")
    args = parser.parse_args()
    
    queries = args.queries if args.queries else [args.topic]
    asyncio.run(run_parallel_research(args.topic, queries))
