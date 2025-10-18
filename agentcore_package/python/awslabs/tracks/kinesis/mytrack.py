from awslabs.track import Track


class MyTrack(Track):

    name = "Kinesis Data Stream"
    description = (
        "Amazon Kinesis Data Streams (KDS) is a massively scalable and durable "
        "real-time data streaming service.\n"
        "\n"
        "In this track you're going to deploy a kinesis stream, learn how to "
        "put records in the stream, and write the messages to S3 using firehose."
    )
    level = "advanced"
    short_description = "Kinesis challenges"
