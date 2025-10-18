from typing import List
from awslabs.challenge import Challenge
import boto3

class MyChallenge(Challenge):
    """The first challenge in this track is to create an API Gateway RestAPI
Tasks:
    - Start a new template.yaml,
    - Create an API Gateway RestApi resource with an endpoint of REGIONAL,
    - The name of the RestApi should be exactly: `myApi`,
    - The CloudFormation stack name should be: `awslabs`, deploy in `eu-west-1`,
Tips & Links:
    - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-restapi.html
    """
    title = "Create an API Gateway"
    description = __doc__

    def start(self) -> None:
        self.instructions()

    def validate(self) -> None:
        errors = validate_apigw() + validate_cf()
        if len(errors) != 0:
            self.fail(errors)
        else:
            self.success('You deployed the RestApi!!')


def validate_apigw() -> List[str]:
    client = boto3.client('apigateway')
    xs = [item for item in list(client.get_rest_apis()['items']) if item['name'] == 'myApi']
    if len(xs) == 0:
        return ['No RestApi with the name `myApi` found']
    else:
        return []


def validate_cf() -> List[str]:
    client = boto3.client('cloudformation')
    xs = [item for item in list(client.list_stacks()['StackSummaries']) if item['StackName'] == 'awslabs' and item['StackStatus'] == 'CREATE_COMPLETE']
    if len(xs) == 0:
        return ['No CloudFormation stack with the name `awslabs` found']
    else:
        return []
