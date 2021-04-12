import click

from indico.cli.core import cli_group
from indico.util.console import cformat
from indico_citadel.backend import LiveSyncCitadelBackend
from indico_livesync.models.agents import LiveSyncAgent


@cli_group(name='citadel')
def cli():
    """Manage the Citadel plugin."""


@cli.command()
@click.argument('agent_id', type=int)
@click.option('--force', is_flag=True, help="Upload even if it has already been done once.")
def upload(agent_id, force):
    agent = LiveSyncAgent.get(agent_id)
    if agent is None:
        print('No such agent')
        return
    if agent.backend is None or agent.backend is not LiveSyncCitadelBackend:
        print(cformat('Cannot run agent %{red!}{}%{reset} (backend invalid or not found)').format(agent.name))
        return
    backend = agent.create_backend()
    backend.run_export_files()
