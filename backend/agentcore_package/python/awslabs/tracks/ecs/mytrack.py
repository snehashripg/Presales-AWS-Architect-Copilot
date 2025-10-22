from awslabs.track import Track


class MyTrack(Track):

    name = "ECS"
    level = "basic"
    short_description = "labs to learn Elastic Container Service"
    description = """
    ECS challenges
    ==============
    In this track you will experience the basics of setting up
    the AWS Elastic Container Service.

    The track uses Fargate, so you do not have to setup 
    your own cluster.
    """
