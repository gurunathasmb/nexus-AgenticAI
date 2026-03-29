import asyncio

from Intent_Agent3.base import BaseAgent, Message

from table_agent.ranker import rank_tables


class TableAgent(BaseAgent):

    def __init__(self):
        super().__init__("table_agent")

    async def handle_message(self, message: Message) -> Message:
        query = message.text.strip()
        top_k = 5
        tables, err = await asyncio.to_thread(rank_tables, query, top_k)
        if err:
            return Message(
                sender="table_agent",
                text=f"Could not rank tables: {err}",
                metadata={**(message.metadata or {}), "table_rank_error": err},
            )

        if not tables:
            return Message(
                sender="table_agent",
                text="No matching result sources found. Try mentioning semester (e.g. 3rd sem) or year.",
                metadata=message.metadata or {},
            )

        lines = ["Here are the most relevant result sources for your query:\n"]
        for i, t in enumerate(tables, 1):
            lines.append(
                f"{i}. {t['table']} (score {t['score']:.2f})\n"
                f"   - {t['source_file']}\n"
                f"   - id: {t['table_id']}"
            )
        lines.append(
            "\nOpen the Table Agent page (/table-agent) for the full JSON API response."
        )

        return Message(
            sender="table_agent",
            text="\n".join(lines),
            metadata={
                **(message.metadata or {}),
                "ranked_tables": tables,
            },
        )
