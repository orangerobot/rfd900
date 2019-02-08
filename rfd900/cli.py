# -*- coding: utf-8 -*-

"""Console script for rfd900."""
import sys
import click


@click.command()
@click.option('--count', default=1, help='Number of greetings.')
@click.option('--name', prompt='Your name',
              help='The person to greet.')
def main(args=None):
    """Console script for rfd900."""
    click.echo("Replace this message by putting your code into "
               "rfd900.cli.main")
    click.echo("See click documentation at http://click.pocoo.org/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
