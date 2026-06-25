import asyncio
from typing import List, Dict


class WebSearchService:
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        try:
            from duckduckgo_search import DDGS
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=max_results))
            )
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ]
        except Exception as e:
            print(f"Erro na busca web: {e}")
            return []
