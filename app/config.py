import os
import json
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def load_config():
    '''
        Config path from env, could be local or on s3
    '''
    config_path = os.getenv("CONFIG_PATH", "config/config.json")
    if config_path.startswith("s3://"):
        # s3://bucket/key
        parts = config_path[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError("Invalid S3 config path. Expected s3://bucket/key")
        bucket, key = parts
        s3_client = boto3.client("s3")
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            config = json.loads(content)
        except (NoCredentialsError, ClientError) as e:
            raise Exception("Failed to load config from S3") from e
    else:
        with open(config_path, "r") as f:
            config = json.load(f)
    return config

