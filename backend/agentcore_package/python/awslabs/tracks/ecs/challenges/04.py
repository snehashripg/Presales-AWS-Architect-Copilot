import boto3

from awslabs.challenge import Challenge, UnfinishedChallengeException


class MyChallenge(Challenge):
    """
    create an ECS cluster named 'awslabs-cluster'.

    Tips & Tricks:
      - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-cluster.html
      - https://docs.aws.amazon.com/cli/latest/reference/ecs/create-cluster.html
    """
    title = "Create an ECS Cluster"
    description = __doc__

    def validate(self):
        ecs = boto3.client('ecs')
        for response in ecs.get_paginator('list_clusters').paginate():
            response = ecs.list_clusters()
            cluster = next(
                filter(
                    lambda c: c['clusterName'] == 'awslabs-cluster',
                    ecs.describe_clusters(
                        clusters=response['clusterArns'])['clusters']), None)
            if cluster:
                self.success('ECS cluster "awslabs-cluster" was found')
                return True

        self.fail('no ECS cluster named "awslabs-cluster" was found.')
