import boto3

from awslabs.challenge import Challenge, UnfinishedChallengeException


class MyChallenge(Challenge):
    """
    create an ECR repository with the name paas-monitor in your account.

    Tips & Links:
     -  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecr-repository.html
     -  https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html

    """
    title = "Create an ECR repository named 'paas-monitor'"
    description = __doc__

    def validate(self):
        ecr = boto3.client('ecr')
        try:
            ecr.describe_repositories(repositoryNames=["paas-monitor"])
            self.success('ECR repository "paas-monitor found.')
        except ecr.exceptions.RepositoryNotFoundException as e:
            self.fail('No ECR repository "paas-monitor" found.')
