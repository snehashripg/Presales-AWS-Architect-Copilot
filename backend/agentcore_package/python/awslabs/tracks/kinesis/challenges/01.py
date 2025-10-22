from awslabs.challenge import Challenge
import boto3
import yaml
import os
import click
from cfn_tools.yaml_loader import CfnYamlLoader, ODict

class MyChallenge(Challenge):

    title = "Kinesis"
    description = (
        "Create a Kinesis Data Stream using CloudFormation. \n"
        "\n"
        "Tasks:"
        "\n"
        " - Deploy the stack with stack name: awslabs-kinesis\n"
        "\n"
        "Tips & Links:\n"
        "\n"
        "\n"
    )

    def start(self):
        self.instructions()

    def validate(self):
        self.fail("Fail")

        
