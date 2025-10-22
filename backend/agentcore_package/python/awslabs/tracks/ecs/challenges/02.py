import boto3
import docker

from awslabs.challenge import Challenge
from awslabs.tracks.ecs.docker_registry import get_docker_registry

IMAGE_NAME = 'mvanholsteijn/paas-monitor:latest'

ecr = boto3.client('ecr')


class MyChallenge(Challenge):
    """
    push the image from the Docker repository "mvanholsteijn/paas-monitor:latest" to your newly
    created ECR repository "paas-monitor".

    Tasks:
      - pull docker image "mvanholsteijn/paas-monitor:latest"  locally.
      - tag the image with your new repository name.
      - push it to your newly created repository

    Tips & Tricks:
      - https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-basics.html
      - https://docs.docker.com/engine/reference/commandline/tag/
      - to do a docker registry login use `aws ecr get-login --no-include-email | sh`

    """
    title = "Create an ECR repository"
    description = __doc__

    def validate(self):
        try:
            dckr = docker.from_env()
            image = dckr.images.get(IMAGE_NAME)
        except Exception as e:
            image = None

        if not image:
            self.fail(
                'the image "{}" was not found in your local docker installation'
                .format(IMAGE_NAME))

        if IMAGE_NAME not in image.tags:
            self.fail(
                'the image "{}" was not found in your local docker installation'
                .format(IMAGE_NAME))

        hostname = get_docker_registry(ecr)
        ecr_image_name = '{}/paas-monitor:latest'.format(hostname)
        try:
            response = ecr.describe_images(
                repositoryName="paas-monitor",
                imageIds=[{
                    "imageTag": "latest"
                }])
            image_details = response['imageDetails'][0]
        except (ecr.exceptions.RepositoryNotFoundException,
                ecr.exceptions.ImageNotFoundException) as e:
            image_details = None

        if not image_details:
            self.fail(
                'No image tagged "latest" found in the repository "{}/paas-monitor".'
                .format(hostname))

        if ecr_image_name not in image.tags:
            self.fail(
                'the image "{}" is not the same as the image "{}"'.format(
                    ecr_image_name, IMAGE_NAME))

        self.success('you have pushed to image {} to {}.'.format(
            IMAGE_NAME, ecr_image_name))
        return True
