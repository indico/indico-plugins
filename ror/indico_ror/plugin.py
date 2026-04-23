# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2026 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import csv
import io
import pathlib
import time
import zipfile
from collections import defaultdict

import click
import requests
import sqlalchemy

import indico
from indico.cli.core import cli_group
from indico.core import signals
from indico.core.db import db
from indico.core.plugins import IndicoPlugin
from indico.modules.events.abstracts.models.persons import AbstractPersonLink
from indico.modules.events.contributions.models.persons import ContributionPersonLink, SubContributionPersonLink
from indico.modules.events.models.persons import EventPerson, EventPersonLink
from indico.modules.events.sessions.models.persons import SessionBlockPersonLink
from indico.modules.users.models.affiliations import Affiliation
from indico.modules.users.models.users import User
from indico.util.console import verbose_iterator

from indico_ror.matching import PGVectorStoreBackedSearch
from indico_ror.models.affiliation_vs_document import AffiliationVectorStoreDocument


AFFILIATION_BACKREF_CLASSES = [
    AbstractPersonLink,
    ContributionPersonLink,
    EventPersonLink,
    EventPerson,
    SessionBlockPersonLink,
    SubContributionPersonLink,
    User,
]

CSV_MATCHES_HEADER = ('Affiliation Text', 'Match Text', 'Match ID', 'Confidence')


def fetch_ror():
    headers = {
        'User-Agent': f'Indico/{indico.__version__}'
    }

    base_url = 'https://zenodo.org/api/records/6347574'
    click.echo(f"fetching records from '{base_url}'...")

    versions = requests.get(
        base_url,
        headers=headers,
        allow_redirects=True
    )

    if versions.status_code != 200:
        return None

    json = versions.json()

    filename = json['files'][0]['key']
    file_url = json['files'][0]['links']['self']

    click.echo(f"fetching '{filename}' from '{file_url}'...")

    return requests.get(
        file_url,
        headers=headers,
        allow_redirects=True
    )


def parse_csv(contents: str):
    csv_dict = defaultdict(list)
    header, *rows = list(csv.reader(contents.splitlines()))
    for row in rows:
        for key, value in zip(header, row, strict=True):
            csv_dict[key].append(value)
    return csv_dict


def extract_csv_rows(csv_dict, names):
    return {
        key: value
        for key, value in csv_dict.items() if key in names
    }


def iterate_csv_rows(csv_dict):
    header = csv_dict.keys()
    size = len(next(iter(csv_dict.values())))
    for row_n in range(size):
        yield {
            key: csv_dict[key][row_n]
            for key in header
        }


def get_ror_csv() -> str:
    ror_zip = fetch_ror()
    click.echo('extracting contents from zip...')
    in_memory_zip = io.BytesIO()
    in_memory_zip.write(ror_zip.content)
    try:
        with zipfile.ZipFile(in_memory_zip, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.csv'):
                    click.echo('done')
                    return zf.read(name).decode()
    finally:
        in_memory_zip.close()

    click.echo('failed to extract contents from zip (no CSV file included)')
    return


def sanitize_csv_name(name: str) -> str:
    name = name.strip()
    split = name.split(':')
    if len(split) == 1:
        return name
    return split[-1].strip()


def parse_csv_names(names: str) -> set[str]:
    names_list = names.split(';')
    return {
        sanitize_csv_name(name) for name in names_list
    }


def parse_csv_name_column(csv_dict, column):
    for row, names in enumerate(csv_dict[column]):
        csv_dict[column][row] = parse_csv_names(names)


def parse_csv_id_column(csv_dict, column):
    for row, ror_id in enumerate(csv_dict[column]):
        csv_dict[column][row] = ror_id.split('/')[-1]


def update_ror_affiliations(ror_affiliations) -> tuple:
    start = time.perf_counter()

    click.echo('updating affiliations...')
    affiliations_by_ror_id = {
        aff.meta['ror_id']: aff
        for aff in Affiliation.query.filter(Affiliation.meta['ror_id'].isnot(None), Affiliation.is_deleted.is_(False))
    }

    updated = {}
    # For each affiliation in the ROR records, try to match it with an existing one in the database.
    # If a match is found, updated the old entry as needed; otherwise, add a new entry.
    for ror_id, aff_data in verbose_iterator(ror_affiliations.items(), len(ror_affiliations), print_total_time=True):
        if (aff := affiliations_by_ror_id.get(ror_id)) is not None:
            assert aff.meta['ror_id'] == ror_id
            del affiliations_by_ror_id[ror_id]

            changed = False
            for field, data in aff_data.items():
                if field == 'alt_names':
                    old = set(aff.alt_names)
                    new = set(data)
                    if old != new:
                        aff.alt_names = sorted(new)
                        changed = True
                elif getattr(aff, field) != data:
                    setattr(aff, field, data)
                    changed = True
            if changed:
                updated[aff.id] = aff
        else:
            db.session.add(Affiliation(**aff_data, meta={'ror_id': ror_id}))

    # The remaining affilitations in the database that were not matched are not
    # present in the new ROR records, so they must be deleted
    for remaining_affiliation in affiliations_by_ror_id.values():
        db.session.delete(remaining_affiliation)

    new = list(db.session.new)
    deleted = {aff.id: aff for aff in db.session.deleted if isinstance(aff, Affiliation)}

    click.echo('flushing database session...')
    db.session.flush()

    # Create the dict here since before flush() we don't have IDs
    added = {aff.id: aff for aff in new if isinstance(aff, Affiliation)}

    elapsed = time.perf_counter() - start
    click.echo(
        f'updated {len(updated)}, added {len(added)}, and deleted {len(deleted)} affiliations in {elapsed:.2f} seconds'
    )

    return added, updated, deleted


def make_vectorstore_data(affiliations: dict[int, Affiliation]) -> tuple[list[str], list[int]]:
    names, metadatas = [], []
    for affiliation_id, affiliation in affiliations.items():
        names.append(affiliation.name)
        metadatas.append(affiliation_id)
        for name in affiliation.alt_names:
            names.append(name)
            metadatas.append(affiliation_id)
    return names, metadatas


def do_ror_sync(csv_dict: dict, reset: bool, dry_run: bool, batch_size: int) -> None:
    filtered = extract_csv_rows(
        csv_dict,
        {
            'id',  # id
            'names.types.ror_display',  # name
            'locations.geonames_details.country_code',  # country code
            'locations.geonames_details.name',  # city
            'names.types.acronym',  # alt name
            'names.types.alias',  # alt name
            'names.types.label',  # alt name
        }
    )

    parse_csv_id_column(csv_dict, 'id')
    parse_csv_name_column(csv_dict, 'names.types.acronym')
    parse_csv_name_column(csv_dict, 'names.types.alias')
    parse_csv_name_column(csv_dict, 'names.types.label')

    rows = len(next(iter(csv_dict.values())))

    affiliations = {}
    for row in verbose_iterator(iterate_csv_rows(filtered), rows, print_total_time=True):
        alts = (row['names.types.acronym'] | row['names.types.alias'] | row['names.types.label']) - {''}
        affiliations[row['id']] = {
            'name': row['names.types.ror_display'],
            'city': row['locations.geonames_details.name'],
            'country_code': row['locations.geonames_details.country_code'],
            'alt_names': alts
        }

    if reset:
        click.echo('deleting previous ROR affiliations from the database...')
        db.session.execute(
            sqlalchemy.delete(Affiliation)
                .where(Affiliation.meta['ror_id'].isnot(None), Affiliation.is_deleted.is_(False))
                .execution_options(synchronize_session='fetch')
        )

    click.echo('updating vector store...')
    added, updated, deleted = update_ror_affiliations(affiliations)
    added_texts, added_ids = make_vectorstore_data(added)
    updated_texts, updated_ids = make_vectorstore_data(updated)
    __, deleted_ids = make_vectorstore_data(deleted)

    search_engine = PGVectorStoreBackedSearch(batch_size=batch_size)
    search_engine.delete(deleted_ids)
    search_engine.update(updated_texts, updated_ids, updated_ids)
    search_engine.add(added_texts, added_ids)

    if not dry_run:
        click.echo('committing database changes...')
        db.session.commit()


class RORPlugin(IndicoPlugin):
    """ROR affiliations.

    Provides access to ROR affiliation information.
    """

    configurable = False

    def init(self):
        super().init()
        self.connect(signals.plugin.cli, self._extend_indico_cli)

    def _extend_indico_cli(self, sender, **kwargs):
        @cli_group()
        def ror():
            """Manage ROR storage."""

        @ror.command()
        @click.option(
            '--output', type=click.Path(dir_okay=False, path_type=pathlib.Path),
            default='ror.csv', help='The output file name.'
        )
        def download(output: str) -> None:
            """Download affiliation metadata from ROR registry."""
            csv_contents = get_ror_csv()
            pathlib.Path(output).write_text(csv_contents)

        @ror.command()
        @click.option(
            '--csv', type=click.Path(dir_okay=False, path_type=pathlib.Path), help='Path to a pre-downloaded CSV.'
        )
        @click.option(
            '--reset', is_flag=True, help='Delete all previously existing affiliations from ROR before starting.'
        )
        @click.option('--dry-run', is_flag=True, help="Don't persist any changes to the database.")
        @click.option(
            '--batch-size', default=512, type=click.INT, help='Change the batch size when calculating embeddings.'
        )
        def sync(csv: pathlib.Path | None, reset: bool, dry_run: bool, batch_size: int) -> None:
            """Update the affiliations in the database from ROR registry."""
            if csv is None:
                csv_contents = get_ror_csv()
            else:
                csv_contents = csv.read_text()

            click.echo('parsing ROR affiliations CSV...')
            csv_dict = parse_csv(csv_contents)
            do_ror_sync(csv_dict, reset, dry_run, batch_size)
            click.echo('done')

        @ror.command()
        @click.argument(
            'output', type=click.Path(dir_okay=False, path_type=pathlib.Path),
        )
        def match(output: pathlib.Path) -> None:
            """Match "free-text" affiliations with affiliations stored in the database."""
            search_engine = PGVectorStoreBackedSearch()

            click.echo('loading affiliations...')
            affiliations: set[str] = {}
            for cls in AFFILIATION_BACKREF_CLASSES:
                affiliations = affiliations.union(
                    str(cwa.affiliation)
                    for cwa in cls.query.filter(cls.affiliation.is_not(None), cls.affiliation != '').all()  # noqa: PLC1901
                )

            def process_affiliation(
                affiliation: str
            ) -> tuple[str, tuple[AffiliationVectorStoreDocument, float]] | None:
                results = search_engine.match(affiliation, 1)
                if len(results) == 0:
                    return None
                return (affiliation, results[0])

            click.echo('matching...')
            results = [process_affiliation(affiliation) for affiliation in affiliations]

            click.echo('saving results...')
            with output.open('w') as csvf:
                writer = csv.writer(csvf)
                writer.writerow(CSV_MATCHES_HEADER)
                writer.writerows(
                    (result[0], result[1][0].content, result[1][0].affiliation_id, result[1][1])
                    for result in results if result is not None
                )

            click.echo('done')

        @ror.command()
        @click.argument(
            'matches', type=click.Path(dir_okay=False, exists=True, path_type=pathlib.Path)
        )
        @click.option('--force', '-f', is_flag=True, help='By-pass the header check.')
        @click.option('--keep-original', '-k', is_flag=True, help='Keep original affiliation text after updating.')
        @click.option('--dry-run', is_flag=True, help="Don't persist any changes to the database.")
        def apply(matches: pathlib.Path, force: bool, dry_run: bool, keep_original: bool) -> None:
            """Apply a set of previously found matches."""
            click.echo('reading matches from file...')
            with matches.open() as csvf:
                reader = csv.reader(csvf)
                headers = tuple(next(reader))

                # TODO: actually fetch the right columns to work with differently formatted CSVs
                if not force and headers != CSV_MATCHES_HEADER:
                    click.secho('error: CSV header mismatch; re-run with --force to proceed', fg='red')
                    return

                try:
                    correspondence = {
                        text: int(match_id) for text, _, match_id, *_ in reader
                    }
                except ValueError:
                    click.secho(f'error: invalid match ID encountered while parsing {str(matches)!r}')
                    return

            click.echo('retrieving matches from the database...')
            affiliation_texts = list(correspondence.keys())
            objects_to_update = [
                object_with_affiliation for sublist in
                [
                    cls.query.filter(cls.affiliation.in_(affiliation_texts))
                    for cls in AFFILIATION_BACKREF_CLASSES
                ]
                for object_with_affiliation in sublist
            ]

            click.echo('updating...')
            updates = 0
            for object_to_update in objects_to_update:
                match_result = correspondence.get(object_to_update.affiliation)
                if match_result is None:
                    click.secho(
                        f"warning: couldn't get match for entry {object_to_update} "
                        f"with affiliation {object_to_update.affiliation!r}",
                        fg='yellow'
                    )
                    continue

                updates += 1
                object_to_update.affiliation_id = match_result
                if not keep_original:
                    object_to_update.affiliation = None

            if not dry_run:
                db.session.commit()

            click.echo(f'updated {updates}/{len(objects_to_update)} entries')

        return ror
