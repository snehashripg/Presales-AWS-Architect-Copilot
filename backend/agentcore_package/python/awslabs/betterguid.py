from datetime import datetime
from random import Random


class BetterGuid(object):
    """
    A readable and userfriendly globally unique identifier based on https://github.com/kjk/betterguid:

    - 20 character strings, safe for inclusion in urls (don't require escaping)
    - based on timestamp; they sort after any existing ids
    - 72-bits of random data after the timestamp so that IDs won't collide with other IDs
    - they sort lexicographically (the timestamp is converted to a string that will sort correctly)
    - monotonically increasing. Even if you generate more than one in the same timestamp, the latter ones will sort
      after the former ones. We do this by using the previous random bits but "incrementing" them by 1
      (only in the case of a timestamp collision).
    """

    def __init__(self):
        self.random = Random()
        self.push_characters = b"-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
        self.last_random_characters = bytearray(12)
        self.last_push_time = 0
        self.generate_random_part()
        assert len(self.push_characters) == 64

    def generate_random_part(self):
        for i in range(0, 12):
            self.last_random_characters[i] = self.random.randint(0, 63)

    def new_guid(self):
        result = bytearray(8 + 12)
        time_in_ms = time_in_millis()
        if time_in_ms == self.last_push_time:
            for i in range(0, 12):
                self.last_random_characters[i] = self.last_random_characters[i] + 1
                if self.last_random_characters[i] < 64:
                    break
                self.last_random_characters[i] = 0
        else:
            self.last_push_time = time_in_ms
            self.generate_random_part()

        for i in range(0, 12):
            result[19 - i] = self.push_characters[self.last_random_characters[i]]

        for i in range(7, -1, -1):
            n = int(time_in_ms % 64)
            result[i] = self.push_characters[n]
            time_in_ms = int(time_in_ms / 64)
        return result.decode('ascii')


def time_in_millis():
    """
    returns the current time in milliseconds
    """
    return int(round(datetime.utcnow().timestamp() * 1000))
