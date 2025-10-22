import boto3

from awslabs.challenge import Challenge
from awslabs.tracks.ecs.docker_registry import get_docker_registry

ecs = boto3.client('ecs')
ecr = boto3.client('ecr')

DOCKER_IMAGE = 'mvanholsteijn/paas-monitor:latest'


class MyChallenge(Challenge):
    """
    create a service named 'paas-monitor' which runs the Docker image mvanholsteijn/paas-monitor:latest
    using Fargate in your default VPC, exposing port 1337 to the public internet.

    Tips & Tricks:
      - https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_GetStarted.html
    """
    title = "Deploy a service using FarGate"
    description = __doc__

    def validate(self):
        response = ecs.describe_services(
            cluster='awslabs-cluster', services=['paas-monitor'])
        service = response['services'][0] if response['services'] else None
        if not service:
            self.fail(
                'no service "paas-monitor" was found in the cluster "awslabs-cluster"'
            )

        if service['status'] == 'INACTIVE':
            self.fail(
                'the service "paas-monitor" was found in the cluster "awslabs-cluster", but it is still INACTIVE'
            )

        task_definition = ecs.describe_task_definition(
            taskDefinition=service['taskDefinition'])['taskDefinition']

        if task_definition['networkMode'] != 'awsvpc':
            self.fail(
                'task definition {} of service "paas-monitor" does not have network mode "awsvpc"'
                .format(task_definition['taskDefinitionArn']))

        valid_images = [
            DOCKER_IMAGE, '{}/paas-monitor:latest'.format(
                get_docker_registry(ecr))
        ]
        container_definition = next(
            filter(lambda c: c['image'] in valid_images,
                   task_definition['containerDefinitions']), None)
        if not container_definition:
            self.fail(
                'the task definition of "paas-monitor" does not have a container with image "{}" nor "{}"'
                .format(valid_images[0], valid_images[1]))
