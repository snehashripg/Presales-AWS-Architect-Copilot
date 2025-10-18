import boto3

from awslabs.challenge import Challenge
from awslabs.tracks.ecs.docker_registry import get_docker_registry

DOCKER_IMAGE = 'mvanholsteijn/paas-monitor:latest'


class MyChallenge(Challenge):
    """
    Create a ECS Task Definition for the family `paas-monitor` using the docker image mvanholsteijn/paas-monitor:latest
    exposing port 1337 to the host with `awsvpc` networking.

    Tips & Tricks:
      - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html
      - https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-task-definition.html
    """
    title = "Create an ECS Task Definition"
    description = __doc__

    def validate(self):
        ecs = boto3.client('ecs')
        ecr = boto3.client('ecr')
        response = ecs.list_task_definitions(
            familyPrefix='paas-monitor', sort='DESC')
        task_definitions = map(
            lambda arn: ecs.describe_task_definition(taskDefinition=arn)['taskDefinition'],
            response['taskDefinitionArns'])
        definition = next(
            filter(lambda d: d['family'] == 'paas-monitor', task_definitions),
            None)

        if not definition:
            self.fail(
                'no task definition with family name "paas-monitor" was found')

        if definition['networkMode'] != 'awsvpc':
            self.fail(
                'latest task definition "{taskDefinitionArn}" has network mode "{networkMode}", expected "awsvpc"'
                    .format(**definition))

        valid_images = [
            DOCKER_IMAGE, '{}/paas-monitor:latest'.format(
                get_docker_registry(ecr))
        ]

        app_container = list(
            filter(lambda c: c['image'] in valid_images,
                   definition['containerDefinitions']))
        if not app_container:
            self.fail(
                'ltest task definition "{}" does not define a container with either image "{}"'
                    .format(definition['taskDefinitionArn'], valid_images))

        self.success(
            'task definition for family "paas-monitor" with container image "{}" was found'.format(
                app_container[0]['image']))

        return True
