import json

import boto3


class LambdaClient:
    def __init__(self):
        self.client = boto3.client('lambda')

    def invoke(self, name, data):
        kwargs = {
            'FunctionName': name,
            'Payload': json.dumps(data).encode,
        }
        print(f'Invoking lambda function: {json.dumps(kwargs)}')
        response = self.client.invoke(**kwargs)
        print(f'Received Response: {json.dumps(response)}')
        return response

    def update_function_configuration(self, name, **changes):
        kwargs = dict(FunctionName=name, **changes)
        print('Invoking lambda.update_function_configuration with kwargs: '
              f'{json.dumps(kwargs)}')
        response = self.client.update_function_configuration(**kwargs)
        print(f"Received response: {json.dumps(response, default=str)}")


class S3Client:
    def __init__(self):
        self.client = boto3.client('s3')

    def get_object(self, bucket, key):
        kwargs = {
            'Bucket': bucket,
            'Key': key,
        }
        print(f"Calling s3.get_object with kwargs: {json.dumps(kwargs)}")
        response = self.client.get_object(**kwargs)
        print(f"Received response: {json.dumps(response, default=str)}")
        return response['Body']

    def put_object(self, bucket, key, body):
        kwargs = {
            'Bucket': bucket,
            'Key': key,
            'Body': self.truncate_body(body),
        }
        print(f"Calling s3.put_item with kwargs: {json.dumps(kwargs)}")
        kwargs['Body'] = body
        s3_response = self.client.put_object(**kwargs)
        print(f"Received response {json.dumps(s3_response, default=str)}")

    @staticmethod
    def truncate_body(body, head=100, tail=100):
        if len(body) > head + tail + 16:
            return (body[:head].decode()
                    + f'...<{len(body) - head - tail} bytes>...'
                    + body[-tail:].decode())
        else:
            return body.decode()


class SnsClient:
    def __init__(self):
        self.client = boto3.client('sns')

    def publish(self, topic, message, sms_sender=None, subject=None):
        kwargs = {
            'TopicArn': topic,
            'Message': message,
            'MessageAttributes': {
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional',
                }
            },
        }
        if sms_sender:
            kwargs['MessageAttributes']['AWS.SNS.SMS.SenderID'] = {
                'DataType': 'String',
                'StringValue': sms_sender,
            }
        if subject:
            kwargs['Subject'] = subject
        print(f'Publishing to SNS: {json.dumps(kwargs)}')
        response = self.client.publish(**kwargs)
        print(f'Received Response: {json.dumps(response)}')
