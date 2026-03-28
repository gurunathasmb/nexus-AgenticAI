import os
from Intent_Agent3.base import BaseAgent, Message
from Intent_Agent3.registry import dispatcher


class RouterAgent(BaseAgent):

    def __init__(self):
        super().__init__("router_agent")

    def _has_llm_key(self):
        return bool(os.getenv("NVIDIA_API_KEY", ""))

    async def _llm_or_fallback(self, message: Message, domain: str, meta: dict):
        """Try LLM agent if API key is set, otherwise return a structured fallback."""
        if self._has_llm_key():
            response = await dispatcher.dispatch(message, "llm_agent")
            return Message(
                sender="router_agent",
                text=response.text,
                metadata=meta,
            )
        # No API key — return a useful response with the classification info
        conf = meta.get("confidence", "?")
        action = meta.get("action", "")
        return Message(
            sender="router_agent",
            text=f"[Domain: {domain} | Confidence: {conf}]\n\n{action}\n\n"
                 f"(LLM unavailable — set NVIDIA_API_KEY in .env to enable full responses)",
            metadata=meta,
        )

    async def handle_message(self, message: Message):
        # Step 1: classify intent
        intent_result = await dispatcher.dispatch(message, "intent_agent")
        domain = intent_result.text
        meta = intent_result.metadata

        downstream_meta = {**(message.metadata or {}), **meta}

        # Step 2: handle based on classification outcome
        if domain == "CLARIFICATION_REQUIRED":
            return Message(
                sender="router_agent",
                text="I'm not sure what you're looking for. Could you rephrase or add more details? "
                     "For example, mention a subject, semester, company, or faculty name.",
                metadata=meta,
            )

        # Multi-candidate (e.g. "results,syllabus")
        domains = [d.strip() for d in domain.split(",")]

        if len(domains) > 1:
            domain_list = " and ".join(domains)
            return await self._llm_or_fallback(message, domain_list, meta)

        # Single resolved domain — route to domain handler or LLM
        single = domains[0]

        if single == "results":
            enriched = Message(
                sender=message.sender,
                text=message.text,
                metadata=downstream_meta,
            )
            result = await dispatcher.dispatch(enriched, "table_agent")
            return Message(
                sender=result.sender,
                text=result.text,
                metadata=meta,
            )

        if single in ("syllabus", "faculty"):
            enriched = Message(
                sender=message.sender,
                text=message.text,
                metadata=downstream_meta,
            )
            result = await dispatcher.dispatch(enriched, "student_agent")
            return Message(
                sender=result.sender,
                text=result.text,
                metadata=meta,
            )

        # For other domains, use LLM with domain context
        return await self._llm_or_fallback(message, single, meta)
