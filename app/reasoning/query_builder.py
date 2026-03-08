from langchain_core.prompts import PromptTemplate

QUERY_BUILDER_PROMPT = """
You convert medical reports, discharge summaries, or claim descriptions
into retrieval queries for health insurance policy documents.

Your goal is to generate a query that helps retrieve relevant policy clauses.

Identify all insurance-relevant concepts in the input.

Examples include (but are not limited to):
- illness or diagnosis
- treatment or medical procedure
- hospitalization details
- accidents or emergencies
- maternity or childbirth
- pre-existing diseases
- waiting periods
- exclusions
- medical expenses or coverage

Do not limit yourself to these examples.

Step 1 — Sentence:
Rewrite the input as ONE clear, neutral natural-language sentence that would
retrieve relevant health insurance policy clauses.

The sentence must remain neutral and should NOT assume whether the treatment
is covered or excluded. It should simply describe the medical situation and
its insurance context based strictly on the input.

Write the sentence as a descriptive statement rather than a question.

Avoid referring to "the patient". Describe the situation in general terms.

Prefer terminology commonly used in insurance policies such as:
"hospitalization expenses", "medical treatment", "inpatient care",
"policy terms", "coverage rules", "medical procedures", or similar terms
that reflect how insurance policies describe medical events.

Avoid excessive clinical abbreviations when possible and prefer general
medical terminology likely to appear in policy documents.

Important rules for the sentence:
- Use ONE natural sentence.
- Do NOT produce keyword lists inside the sentence.
- Do NOT use boolean operators like AND, OR, NOT.
- Do NOT include patient identifiers such as name, age, hospital, or dates.

Step 2 — Keywords:
Provide a short list of 5–10 keywords derived from the input.

The keywords must be directly related to the diagnosis, treatment,
procedure, or insurance concept mentioned in the input.

Do NOT introduce unrelated medical or insurance concepts.
Prefer general terminology likely to appear in policy documents.

Output format:

Sentence:
<one natural sentence>

Keywords:
<comma separated keywords>

Input:
{user_input}
"""


class ClaimLensQueryBuilder:
    """
    Universal Query Builder for ClaimLens RAG system.

    Works with any LangChain-compatible LLM.
    """

    def __init__(self, llm):
        self.llm = llm

        self.prompt = PromptTemplate(
            input_variables=["user_input"],
            template=QUERY_BUILDER_PROMPT
        )

    def build_query(self, user_input: str) -> str:
        formatted_prompt = self.prompt.format(
            user_input=user_input
        )

        response = self.llm.invoke(formatted_prompt)

        return response.content.strip()