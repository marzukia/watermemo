"""
watermemo filter for Open WebUI.

Install: Workspace > Functions > + New Function > type: Filter,
then paste this file's contents.
"""

import requests
from pydantic import BaseModel
from typing import Optional


class Filter:
    class Valves(BaseModel):
        base_url: str = "http://web:8000/api"
        recall_limit: int = 5
        recall_threshold: float = 0.7
        update_threshold: float = 0.15
        store_exchanges: bool = True
        enabled: bool = True
        context_messages: int = 6

    def __init__(self):
        self.valves = self.Valves()

    def _build_recall_query(self, messages: list[dict]) -> str:
        """Concatenate recent non-system messages into a single recall query."""
        recent = [
            m for m in messages if m.get("role") in ("user", "assistant")
        ][-self.valves.context_messages :]

        if not recent:
            return ""

        if len(recent) == 1:
            return recent[0].get("content", "")

        parts = []
        for m in recent[:-1]:
            text = m.get("content", "")
            if len(text) > 500:
                text = text[:500]
            parts.append(text)

        parts.append(recent[-1].get("content", ""))
        return "\n".join(parts)

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.enabled:
            return body

        user_id = (__user__ or {}).get("id", "")
        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m["role"] == "user"]
        if not user_msgs:
            return body

        query = self._build_recall_query(messages)
        if not query:
            return body

        memory_block = ""
        try:
            res = requests.post(
                f"{self.valves.base_url}/distillations/search",
                json={
                    "query": query,
                    "limit": self.valves.recall_limit,
                    "threshold": self.valves.recall_threshold,
                    "user_id": user_id,
                },
                timeout=15,
            )
            res.raise_for_status()
            results = res.json()
            if results:
                lines = [
                    "## Long-term memories",
                    "The following are facts recalled from past conversations.",
                    "Use them to inform your answer when relevant. Do not mention",
                    "that you are reading from memories unless asked.",
                    "",
                ]
                for r in results:
                    prefix = "⭐" if r.get("is_core") else "-"
                    lines.append(f"{prefix} {r['content']}")
                lines.append("")
                memory_block = "\n".join(lines)
        except Exception:
            pass

        if memory_block:
            system_msgs = [m for m in messages if m["role"] == "system"]
            if system_msgs:
                system_msgs[0]["content"] = (
                    memory_block + "\n\n" + system_msgs[0]["content"]
                )
            else:
                body["messages"] = [
                    {"role": "system", "content": memory_block}
                ] + messages

        body["think"] = False

        return body

    _DELETE_PHRASES = (
        "forget",
        "delete",
        "remove memory",
        "erase memory",
        "clear memory",
        "wipe memory",
        "forget everything",
        "delete all memories",
        "clear all memories",
    )

    def _looks_like_delete(self, text: str) -> tuple[bool, str]:
        """Keyword-based delete intent detection. Returns (is_delete, scope)."""
        lower = text.lower().strip()
        for phrase in ("forget everything", "delete all memories", "clear all memories", "wipe memory"):
            if phrase in lower:
                return True, "all"
        for phrase in self._DELETE_PHRASES:
            if phrase in lower:
                return True, "specific"
        return False, "specific"

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.enabled or not self.valves.store_exchanges:
            return body

        user_id = (__user__ or {}).get("id", "")
        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m["role"] == "user"]
        asst_msgs = [m for m in messages if m["role"] == "assistant"]

        if not user_msgs or not asst_msgs:
            return body

        user_text = user_msgs[-1]["content"]
        asst_text = asst_msgs[-1]["content"]
        if len(asst_text) > 2000:
            asst_text = asst_text[:2000] + "…"
        content = f"User: {user_text}\nAssistant: {asst_text}"

        is_delete, scope = self._looks_like_delete(user_text)

        if is_delete:
            try:
                if scope == "all":
                    requests.delete(
                        f"{self.valves.base_url}/memories/",
                        params={"user_id": user_id},
                        timeout=10,
                    )
                else:
                    search_res = requests.post(
                        f"{self.valves.base_url}/distillations/search",
                        json={
                            "query": user_text,
                            "limit": 1,
                            "threshold": self.valves.recall_threshold,
                            "user_id": user_id,
                        },
                        timeout=10,
                    )
                    search_res.raise_for_status()
                    matches = search_res.json()
                    if matches:
                        memory_id = matches[0]["memory_id"]
                        requests.delete(
                            f"{self.valves.base_url}/memories/{memory_id}",
                            timeout=10,
                        )
            except Exception:
                pass
            return body

        try:
            search_res = requests.post(
                f"{self.valves.base_url}/distillations/search",
                json={
                    "query": content,
                    "limit": 1,
                    "threshold": self.valves.update_threshold,
                    "user_id": user_id,
                },
                timeout=10,
            )
            search_res.raise_for_status()
            matches = search_res.json()
        except Exception:
            matches = []

        try:
            if matches:
                memory_id = matches[0]["memory_id"]
                requests.patch(
                    f"{self.valves.base_url}/memories/{memory_id}",
                    json={"content": content},
                    timeout=30,
                )
            else:
                requests.post(
                    f"{self.valves.base_url}/memories/",
                    json={"content": content, "user_id": user_id},
                    timeout=30,
                )
        except Exception:
            pass

        return body
