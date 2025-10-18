from awslabs.track import Track


class MyTrack(Track):
    
    name = "CloudFormation"
    description = (
        "AWS CloudFormation provides a common language for you to "
        "describe and provision all the infrastructure resources in "
        "your cloud environment. CloudFormation allows you to use a "
        "simple text file to model and provision, in an automated and "
        "secure manner, all the resources needed for your applications "
        "across all regions and accounts. This file serves as the single "
        "source of truth for your cloud environment. "
    )
    level = "basic"
    short_description = "CloudFormation challenges"
