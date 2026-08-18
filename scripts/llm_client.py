
"""
LLM Client
----------

OpenAI GPT-4o-mini inference for portfolio chatbot.

The model answers ONLY from the supplied portfolio context.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# =============================================================================
# ENVIRONMENT
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


# =============================================================================
# CONFIG
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MAX_TOKENS = 600

TEMPERATURE = 0.0


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT = """You are Victor Von Doom, the intelligent, eloquent, and formidable AI Portfolio Assistant for Md. Asaduzzaman Shuvo.
Answer the user's question accurately using ONLY the exact facts provided in the Context below.

CRITICAL ANTI-HALLUCINATION RULES:
- ONLY state paper titles, project names, datasets, URLs, dates, or statistics that are EXPLICITLY written in the Context below.
- NEVER invent, speculate, or cite any fictional paper titles (e.g. YOLO-DengueVector or Cross-Modal Attention). If a paper or detail is NOT in the context, explicitly state that it is not available.
- Do NOT repeat any list items or sentences.
- Maintain your persona as Victor Von Doom: confident, articulate, dignified, and precise.
- If the user asks about activity today or recently, summarize the recent work updates, paper acceptances, or projects provided in the context.
"""

CONVERSATION_SYSTEM_PROMPT = """You are Victor Von Doom, the refined and powerful AI Portfolio Assistant representing Md. Asaduzzaman Shuvo.
Respond to greetings, small talk, and casual conversation in your signature persona: dignified, confident, eloquent, and commanding yet polite.
Introduce yourself proudly as Victor Von Doom, AI Assistant to Md. Asaduzzaman Shuvo.
Invite the user to inquire about Shuvo's research papers, AI projects, technical skills, education, LeetCode stats, or recent work updates.
Keep your response brief and articulate (2-3 sentences max).
"""


# =============================================================================
# CLIENT
# =============================================================================

class LLMClient:

    def __init__(self):

        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Add it to your .env file."
            )

        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
        )

        self.model = OPENAI_MODEL

        print(f"[OK] OpenAI client ready (model: {self.model})")

    # =========================================================================
    # GENERATE
    # =========================================================================

    def generate(
        self,
        question: str,
        context: str,
    ) -> str:

        is_conversation = (
            "Casual conversation" in context
            or "Casual conversational query" in context
            or question.strip().lower() in [
                "hi", "hello", "hey", "how are you",
                "good morning", "good evening", "thanks",
                "thank you", "bye", "goodbye", "who are you",
                "what can you do"
            ]
        )

        sys_prompt = CONVERSATION_SYSTEM_PROMPT if is_conversation else SYSTEM_PROMPT

        user_message = (
            f"Context:\n{context}\n\n"
            f"Question: {question}"
        )

        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": sys_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.5 if is_conversation else TEMPERATURE,
            )

            answer = response.choices[0].message.content

        except Exception as error:

            print(f"[ERROR] OpenAI API: {error}")

            return (
                "Sorry, I could not generate a response. "
                "Please try again."
            )

        if not answer:
            return (
                "The available portfolio data does not "
                "contain that information."
            )

        answer = answer.strip()

        # Remove leading colon or "Answer:" prefix
        while answer.startswith(":") or answer.startswith("-"):
            answer = answer[1:].strip()

        if answer.startswith("Answer:"):
            answer = answer[7:].strip()

        # Strip hallucinated URL placeholders
        answer = re.sub(
            r'\s*\(Link[^)]*\)',
            '',
            answer,
        )

        if not answer:
            return (
                "The available portfolio data does not "
                "contain that information."
            )

        return answer


# =============================================================================
# SINGLETON
# =============================================================================

_client = None


def get_llm_client():

    global _client

    if _client is None:

        _client = LLMClient()

    return _client


# =============================================================================
# PUBLIC FUNCTION
# =============================================================================

def generate_answer(
    question: str,
    context: str,
) -> str:

    client = get_llm_client()

    return client.generate(
        question=question,
        context=context,
    )


# =============================================================================
# TEST
# =============================================================================

def main():

    print("=" * 70)
    print("LLM CLIENT TEST (GPT-4o-mini)")
    print("=" * 70)

    question = "Tell me about Shuvo"

    context = """
The following is Shuvo's portfolio information:

Source 1 (from AI_resume_shuvo.pdf):
Md. Asaduzzaman Shuvo
AI Engineer - Machine Learning

AI researcher and engineer specializing in LLMs,
low-resource NLP, multimodal AI, and computer vision.

Author of 2 published papers and 3 papers under review.

Skills include PyTorch, Hugging Face, QLoRA/LoRA,
LangChain, YOLO, and FastAPI.

Solved 260+ problems across LeetCode,
Codeforces, and other competitive programming platforms.

B.Sc. in Computer Science & Engineering at
United International University. CGPA: 3.60/4.00.
"""

    print()
    print(f"Question:\n{question}")

    print()
    print("-> Generating answer with GPT-4o-mini...")

    answer = generate_answer(
        question=question,
        context=context,
    )

    print()
    print("-" * 70)
    print("ANSWER")
    print("-" * 70)
    print(answer)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
