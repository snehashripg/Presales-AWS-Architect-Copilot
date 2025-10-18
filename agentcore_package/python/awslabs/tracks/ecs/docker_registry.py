import boto3
import docker
from urllib.parse import urlparse
from base64 import b64decode


def ecr_credentials(ecr):
    """
    gets an ECR authorization token, and returns the username, password and registry_url of
    the AWS ECR registry
    :param ecr: handle to boto3 ECR client
    :return: username, password and registry_url
    """
    token = ecr.get_authorization_token()['authorizationData'][0]
    registry = token['proxyEndpoint']
    authorization = b64decode(
        token['authorizationToken'].encode('ascii')).decode('ascii')
    username, password = authorization.split(':')
    return username, password, registry


def ecr_docker_login(ecr, docker_client):
    """
    login with docker using the ECR credentials
    :param ecr: boto3 ECR client
    :param docker_client:  docker client
    :return: True if successful, otherwise False
    """
    username, password, registry = ecr_credentials(ecr)
    result = docker_client.login(
        username=username, password=password, registry=registry)
    return result['Status'] == 'Login Succeeded'


def get_docker_registry(ecr):
    """
    returns the ECR registry name
    :param ecr: boto3 ECR client
    """
    _, _, registry = ecr_credentials(ecr)
    return urlparse(registry).netloc
