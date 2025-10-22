import importlib
import importlib.util
import os
from typing import Any, Dict

import click

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
DEBUG = False


def get_track_class(path: str) -> Any:
    """
    Returns a class dynamically loaded from the path
    """
    spec = importlib.util.spec_from_file_location("MyTrack", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clazz = getattr(module, 'MyTrack')
    return clazz


def get_tracks(track_dir: str) -> Dict[str,  Any]:
    """
    Return an index of tracks with classes
    """
    index = { f: get_track_class(track_dir + '/tracks/' + str(f) + '/' + 'mytrack.py') for f in os.listdir(track_dir + '/tracks/') if f not in ['__init__.py', '__pycache__']}
    return index


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('track', default='list')
@click.argument('action', default='validate', type=click.Choice(['start', 'validate', 'help', 'stop', 'restart']))
@click.option('--verbose/-v', is_flag=True)
def main(track = '', action = '', verbose = False):

    script_directory = os.path.dirname(os.path.realpath(__file__))

    if verbose:
        os.environ["AWSLABS_VERBOSE"] = "1"
    else:
        os.environ["AWSLABS_VERBOSE"] = "0"

    if track == "list":
        awslabs = click.style('awslabs', fg='red')
        click.echo("\nWelcome to "+awslabs)
        click.echo("\nThe following tracks are available:\n")
        for (k, v) in sorted(get_tracks(script_directory).items()):
           click.echo(f'{k}: {v.short_description}')
        click.echo("\nUse the following commands to play:\n")
        click.echo(" awslabs trackname start")
        click.echo(" awslabs trackname help")
        click.echo(" awslabs trackname validate   or   awslabs trackname")
        click.echo(" awslabs trackname stop")
        click.echo(" awslabs trackname restart")
        click.echo("\n")
        exit()

    try:
        track_class = get_tracks(script_directory).get(track)
        if track_class:
            cl = track_class(track)
            getattr(cl, action)()
        else:
            print(f'Track {track} not found')
    except Exception as e:
        print(f'Track {track} not found, {e}')
        exit()


if __name__ == '__main__':
    main()
