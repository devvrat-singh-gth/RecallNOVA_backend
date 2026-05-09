import os
from langchain_groq import ChatGroq

llm = None


def get_llm():
    global llm

    if llm is None:

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in environment"
            )

        llm = ChatGroq(
            api_key=api_key,

            # ✅ STABLE MODEL
            model="openai/gpt-oss-20b",

            # ✅ LOWER RANDOMNESS
            temperature=0.2,

            # ✅ IMPORTANT FIX
            max_tokens=2500,

            # ✅ PREVENT HANGS
            timeout=60,

            # ✅ RETRY SAFETY
            max_retries=2
        )

    return llm


def ask_llm(prompt: str):

    try:

        print("PROMPT LENGTH:", len(prompt))

        model = get_llm()

        response = model.invoke(prompt)

        print("RAW RESPONSE OBJECT:")
        print(response)

        # ✅ SAFETY
        if not response:
            print("❌ EMPTY RESPONSE OBJECT")
            return "No response generated."

        content = getattr(response, "content", "")

        if not content:
            print("❌ EMPTY RESPONSE CONTENT")
            return "No response generated."

        content = str(content).strip()

        print("FINAL RESPONSE LENGTH:", len(content))

        # ✅ DEBUG PREVIEW
        print("RESPONSE PREVIEW:")
        print(content[:500])

        return content

    except Exception as e:

        print(f"❌ LLM ERROR: {e}")

        return "AI service temporarily unavailable."