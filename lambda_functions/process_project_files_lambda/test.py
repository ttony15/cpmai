# test_lambda_function.py

import json
from lambda_function import lambda_handler


def main():
    # Define a mock event
    mock_event = {
        "project_id": "test",
        "user_id": "test_user_id",
        "action": "process",
    }

    # Define a mock context (this can be an empty object)
    mock_context = {}

    # Call the lambda_handler function
    response = lambda_handler(mock_event, mock_context)

    # Print the response
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    main()
