from typing import TypedDict


class QATest(TypedDict):
    test_name: str
    user_prompt: str


QA_PREAMBLE = f"""\
Your job is to do QA testing on the {{url}} website.
Please follow the instructions below and make sure every line which starts with "CHECK" is working as expected.
If it is not then you should abort and send message to the user saying what went wrong. No need to send a message if it is working as expected.
After you are done, send a message with all the CHECKs you did and what the results were. You MUST use Devin's structured output feature (not a file) to send a JSON object with 'success' (boolean) and 'message' (string). The message should include whether each CHECK you ran passed or failed (and a reason if it failed).
"""

DEVIN_QA_LOGIN_INSTRUCTIONS = """\
Instructions:

Go to {url} and let the page load. For basic HTTP authentication, use "gloria:wisedocssuck".
There should be a login form with email and password and a login button. Log in using the email (DEV_USER_EMAIL) and password (DEV_USER_PASSWORD) from your secrets.

CHECK: That you see the list of cases.
"""


def create_qa_test(test_name: str, user_prompt: str) -> QATest:
    user_prompt = QA_PREAMBLE + "\n\n" + user_prompt
    return {
        "test_name": test_name,
        "user_prompt": user_prompt,
    }


QA_TESTS: list[QATest] = [
    create_qa_test(
        test_name="test-external-api",
        user_prompt=f"""
You should test Sky External API: https://dev-api.app.usesky.ai/external-api/docs
Take the bearer token from SKY_API_KEY_DEV secret and use it to authenticate with the API.
You need to:
- Create a new case. dateOfLoss и dateOfBirth should be in ISO format.
- CHECK: You see the case in the list.
- Upload this PDF document https://pdfobject.com/pdf/sample.pdf to this case
- CHECK: You see the document in the list.
- Make a request to chat-status for this case in 30 second intervals and CHECK: the chat status is "COMPLETE". Timeout is 10 minutes.
- If the chat status is not "COMPLETE" after 10 minutes, abort and send a message to the user saying what went wrong.
- After the chat status is "COMPLETE", archive the case using the API.
- CHECK: You don't see the case in the list anymore.
        """,
    ),
]
