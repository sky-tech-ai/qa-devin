from typing import TypedDict


class QATest(TypedDict):
    test_name: str
    user_prompt: str


QA_PREAMBLE = f"""\
Your job is to do QA testing on the {{url}} website.
Please follow the instructions below and make sure every line which starts with "CHECK" is working as expected.
If it is not then you should abort and send message to the user saying what went wrong. No need to send a message if it is working as expected.
After you are done, send a message with all the CHECKs you did and what the results were. Your structured output should be a json object with 'success' (boolean) and 'message' (string). The message should include whether each CHECK you ran passed or failed (and a reason if it failed).
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
        test_name="check-the-case-page-load",
        user_prompt=f"""{DEVIN_QA_LOGIN_INSTRUCTIONS}
Find the last case in the case table and click on it.
CHECK: That you are on the case page and see its name on top, date of birth, date of loss, claim or case #, total number of pages and created by.
CHECK: You see a list of documents associated with the case.""",
    ),
]
