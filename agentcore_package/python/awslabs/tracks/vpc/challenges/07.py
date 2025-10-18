from awslabs.challenge import Challenge
import boto3
import yaml
import os
import click
from cfn_tools.yaml_loader import CfnYamlLoader, ODict

class MyChallenge(Challenge):
    """
    Now delete the stacks to avoid further costs.

    If you followed the tips, you'll only have to delete one CloudFormation stack.
    """
    title = "Delete your stacks"

    description = __doc__


    def validate(self):

        vpc_id = self.get("vpc_id")

        self.fail("Fail")


