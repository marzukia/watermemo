"""
watermemo Open WebUI Filter
=========================
Paste the contents of this file into Open WebUI:
  Workspace → Functions → + New Function → type: Filter

Inlet  — recalls relevant memories and injects them into the system
         prompt before the LLM sees the user's message.
Outlet — stores the user+assistant exchange as a new memory after
         every response.
"""

import requests
from pydantic import BaseModel
from typing import Optional


class Filter:
    class Valves(BaseModel):
        base_url: str = "http://web:8000/api"
        recall_limit: int = 5
        recall_threshold: float = 0.5
        update_threshold: float = 0.15  # cosine distance; lower = must be very similar to update
        store_exchanges: bool = True
        enabled: bool = True

    def __init__(self):
        self.valves = self.Valves()

    # ------------------------------------------------------------------
    # Inlet — runs before the LLM answers
    # ------------------------------------------------------------------
    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.enabled:
            return body

        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m["role"] == "user"]
        if not user_msgs:
            return body

        query = user_msgs[-1]["content"]

        # Skip expensive recall if the message doesn't warrant it
        try:
            cls_res = requests.post(
                f"{self.valves.base_url}/classify",
                json={"text": query},
                timeout=15,
            )
            cls_res.raise_for_status()
            if not cls_res.json().get("recall", True):
                return body
        except Exception:
            pass  # on classify failure, proceed with recall anyway

        try:
            res = requests.post(
                f"{self.valves.base_url}/recall",
                json={
                    "query": query,
                    "limit": self.valves.recall_limit,
                    "threshold": self.valves.recall_threshold,
                },
                timeout=10,
            )
            res.raise_for_status()
            data = res.json()
        except Exception:
            return body

        context = data.get("context", [])
        if not context:
            return body

        lines = ["## Memories relevant to this conversation"]
        for m in context:
            prefix = "⭐ [core]" if m.get("is_core") else "-"
            lines.append(f"{prefix} {m['distillation']}")
        lines.append("")
        memory_block = "\n".join(lines)

        system_msgs = [m for m in messages if m["role"] == "system"]
        if system_msgs:
            system_msgs[0]["content"] = memory_block + "\n\n" + system_msgs[0]["content"]
        else:
            body["messages"] = [{"role": "system", "content": memory_block}] + messages

        return body

    # ------------------------------------------------------------------
    # Outlet — runs after the LLM responds
    # ------------------------------------------------------------------
    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        if not self.valves.enabled or not self.valves.store_exchanges:
            return body

        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m["role"] == "user"]
        asst_msgs = [m for m in messages if m["role"] == "assistant"]

        if not user_msgs or not asst_msgs:
            return body

        user_text = user_msgs[-1]["content"]
        content = (
            f"User: {user_text}\n"
            f"Assistant: {asst_msgs[-1]['content']}"
        )

        # --- Classify intent via LLM ---
        intent = "store"
        scope = "specific"
        try:
            cls_res = requests.post(
                f"{self.valves.base_url}/classify",
                json={"text": user_text},
                timeout=15,
            )
            cls_res.raise_for_status()
            cls = cls_res.json()
            if cls.get("intent") == "delete" and cls.get("confidence") == "high":
                intent = "delete"
                scope = cls.get("scope", "specific")
            elif cls.get("intent") == "ignore":
                intent = "ignore"
        except Exception:
            pass

        if intent == "ignore":
            return body

        if intent == "delete":
            try:
                if scope == "all":
                    requests.delete(
                        f"{self.valves.base_url}/memories/",
                        timeout=10,
                    )
                else:
                    search_res = requests.post(
                        f"{self.valves.base_url}/distillations/search",
                        json={
                            "query": user_text,
                            "limit": 1,
                            "threshold": self.valves.recall_threshold,
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

        # --- Store / update ---
        try:
            search_res = requests.post(
                f"{self.valves.base_url}/distillations/search",
                json={
                    "query": content,
                    "limit": 1,
                    "threshold": self.valves.update_threshold,
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
                    timeout=10,
                )
            else:
                requests.post(
                    f"{self.valves.base_url}/memories/",
                    json={"content": content},
                    timeout=10,
                )
        except Exception:
            pass

        return body
