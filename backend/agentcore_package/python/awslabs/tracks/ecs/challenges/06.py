import boto3
import requests
from botocore.exceptions import ClientError

from awslabs.tracks.ecs.challenges.create_service import MyChallenge as CreateServiceChallenge


class MyChallenge(CreateServiceChallenge):
    """
    Create an Application Load Balancer (ELBv2) named 'awslabs-ecs-lb' which listens on port 80 on the public
    internet and forwards to ECS service 'paas-monitor' with 2 instances running in the default VPC.

    Tasks:
      - create an Application Load Balancer, with a listener and a default target group.
      - associate the service with the default target group.
      - grant access to the service from the load balancer only.
      - increase the number of service instances to 2

    Tips & Tricks:
      - https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-service.html
      - When using CloudFormation add a DependsOn in your Service on the Load Balancer Listener
    """
    title = "Running the service behind a load balancer"
    description = __doc__

    def validate(self):
        elbv2 = boto3.client('elbv2')
        ecs = boto3.client('ecs')
        try:
            response = elbv2.describe_load_balancers(
                Names=['awslabs-cluster-lb'])
        except ClientError as e:
            self.fail(
                'no application load balancer named "awslabs-cluster-lb" found.'
            )

        lb = response['LoadBalancers'][0]
        lb_arn = lb['LoadBalancerArn']

        try:
            listeners = elbv2.describe_listeners(
                LoadBalancerArn=lb_arn)['Listeners']
        except ClientError as e:
            self.fail(
                'no listeners found for application load balancer named "awslabs-cluster-lb".'
            )

        listener = next(filter(lambda l: l['Port'] == 80, listeners), None)
        if not listener:
            self.fail(
                'no listeners for port 80 found on the application load balancer named "awslabs-cluster-lb".'
            )

        try:
            rules = elbv2.describe_rules(
                ListenerArn=listener['ListenerArn'])['Rules']
        except ClientError as e:
            self.fail(
                'no rules found for port 80 listener on the application load balancer named "awslabs-cluster-lb".'
            )

        try:
            services = ecs.describe_services(
                cluster='awslabs-cluster',
                services=['paas-monitor'])['services']
        except ClientError as e:
            self.fail(
                'service "paas-monitor" not found on cluster "awslabs-cluster".'
            )

        if not services:
            self.fail(
                'service "paas-monitor" not found on cluster "awslabs-cluster".'
            )

        service = services[0]
        target_group_arns = set(
            map(lambda lb: lb['targetGroupArn'], service['loadBalancers']))
        if not target_group_arns:
            self.fail(
                'service "paas-monitor" is not associated with any TargetGroups'
            )

        rule_matches = filter(lambda rule: filter(
            lambda action: 'TargetGroupArn' in action and action['TargetGroupArn'] in target_group_arns,
            rule['Actions']), rules)
        if not rule_matches:
            self.fail(
                'no rules on the port 80 listener forward to the target group target {} of the service "paas-monitor"'
                .format(target_group_arns))

        if service['desiredCount'] <= 1:
            self.fail(
                'expected at least two instances of the service "paas-monitor" are running, found {}'
                .format(service['desiredCount']))

        url = 'http://{}'.format(lb['DNSName'])
        try:
            response = requests.get(url + '/status', timeout=3)
        except Exception as e:
            self.fail('Failed to connect to {}\n\t{}'.format(url, e))

        if response.status_code != 200:
            self.fail('{} does not return 200 OK, but {}\n\t {}'.format(
                url, response.status_code, response.text))

        self.success(
            'The load balancer is forwarding to the paas-monitor service. goto {}'
            .format(url))
