# Project Files Processing Lambda

This AWS Lambda function is triggered by SQS messages and processes files associated with a project.

## Description

The Lambda function processes SQS messages containing project IDs and user IDs, retrieves the corresponding files from MongoDB, and processes those files based on their categories.

## Dependencies

- Python 3.9+
- boto3 - AWS SDK for Python
- pymongo - MongoDB driver for Python

## Environment Variables

The following environment variables need to be set:

- `MONGODB_URI` - MongoDB connection string
- `SQS_QUEUE_URL` - URL of the SQS queue to read messages from
- `MONGODB_DB_NAME` - (Optional) Name of the MongoDB database (defaults to "cpmai")

## Deployment

1. Install dependencies:
   ```
   pip install -r requirements.txt -t .
   ```

2. Create a deployment package:
   ```
   zip -r deployment_package.zip .
   ```

3. Deploy to AWS Lambda:
   ```
   aws lambda create-function \
     --function-name process-project-files-lambda \
     --runtime python3.9 \
     --handler lambda_function.lambda_handler \
     --role arn:aws:iam::ACCOUNT_ID:role/lambda-role \
     --zip-file fileb://deployment_package.zip \
     --environment Variables={MONGODB_URI=your-mongodb-uri,SQS_QUEUE_URL=your-sqs-queue-url}
   ```

## Usage

The lambda function can be triggered by:

1. SQS events
2. Direct invocation

The expected input message format from SQS:
```json
{
  "project_id": "your-project-id",
  "user_id": "user-id",
  "action": "process",
  "timestamp": "2023-01-01T00:00:00+00:00"
}
```

## Response Format

Successful response:
```json
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "message": "Successfully processed 3 files for project your-project-id",
    "project_id": "your-project-id",
    "user_id": "user-id",
    "file_count": 3
  }
}
```

Error responses:

Missing required fields:
```json
{
  "statusCode": 400,
  "body": {
    "error": "Missing project_id in the message"
  }
}
```

Project not found:
```json
{
  "statusCode": 404,
  "body": {
    "error": "Project with ID your-project-id not found"
  }
}
```

No files found:
```json
{
  "statusCode": 404,
  "body": {
    "error": "No files found for project ID your-project-id and user ID user-id"
  }
}
```

Processing failed:
```json
{
  "statusCode": 500,
  "body": {
    "status": "error",
    "message": "Failed to process files for project your-project-id",
    "project_id": "your-project-id",
    "user_id": "user-id"
  }
}
```
