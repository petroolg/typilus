#!/usr/bin/env python3
"""
Usage:
    extractgraphs.py [options] SOURCE_FOLDER DUPLICATES_JSON SAVE_FOLDER TYPING_RULES

Main file for data preprocessing. Walk recursively through the source folder's files to generate a code graph for each (concatenated in one jsonl output file) and a global type lattice.

Options:
    -h --help              Show this screen.
    --debug                Debugging mode.
"""
import bdb
import json
import os
import time
import traceback
from glob import iglob
from typing import Tuple, List, Optional, Set, Iterator

from docopt import docopt
from dpu_utils.utils import save_jsonl_gz, run_and_debug, ChunkWriter

from .graphgenerator import AstGraphGenerator
from .type_lattice_generator import TypeLatticeGenerator
from .typeparsing import FaultyAnnotation


class Monitoring:
    def __init__(self):
        self.count = 0  # type: int
        self.errors = []
        self.file = ""  # type: str
        self.current_repo = ""
        self.empty_files = []

    def increment_count(self) -> None:
        self.count += 1

    def found_error(self, err, trace) -> None:
        self.errors.append([self.file, err, trace])

    def enter_file(self, filename: str) -> None:
        self.file = filename

    def enter_repo(self, repo_name: str) -> None:
        self.current_repo = repo_name


def build_graph(source_code, monitoring: Monitoring, type_lattice: TypeLatticeGenerator, flake8_json: list) -> Tuple[
    Optional[List], Optional[List]]:
    """
    Parses the code of a file into a custom abstract syntax tree.
    """
    try:
        visitor = AstGraphGenerator(source_code, type_lattice)
        return visitor.build(flake8_json)
    except FaultyAnnotation as e:
        print("Faulty Annotation: ", e)
        print("at file: ", monitoring.file)
    except SyntaxError as e:
        monitoring.found_error(e, traceback.format_exc())
    except Exception as e:
        print(traceback.format_exc())
        monitoring.found_error(e, traceback.format_exc())


def explore_files(root_dir: str, duplicates_to_remove: Set[str], monitoring: Monitoring,
                  type_lattice: TypeLatticeGenerator, flake8_root_dir: str) -> Iterator[Tuple]:
    """
    Walks through the root_dir and process each file.
    """
    for file_path in iglob(os.path.join(root_dir, '**', '*.py'), recursive=True):
        if file_path in duplicates_to_remove:
            print(f"Ignoring duplicate {file_path}.")
            continue
        print(file_path)
        if not os.path.isfile(file_path):
            continue
        with open(file_path, encoding="utf-8", errors='ignore') as f:
            monitoring.increment_count()
            monitoring.enter_file(file_path)
            repo = file_path.replace(root_dir, '').split('/')[0]
            if monitoring.current_repo != repo:
                monitoring.enter_repo(repo)
                type_lattice.build_graph()

            flake8_report_path = os.path.join(flake8_root_dir, file_path.replace(root_dir, '')[:-2] + ".json")
            if not os.path.isfile(file_path):
                flake8_report = []
            else:
                with open(flake8_report_path, "r") as file:
                    flake8_report = json.load(file)

            graph = build_graph(f.read(), monitoring, type_lattice, flake8_report)
            if graph is None or len(graph["supernodes"]) == 0:
                continue
            graph["filename"] = file_path[len(root_dir):]
            yield graph


def main(arguments):
    monitoring = Monitoring()
    type_lattice = TypeLatticeGenerator(arguments['TYPING_RULES'])
    try:
        start_time = time.clock()
        print("Exploring folders ...")
        walk_dir = arguments['SOURCE_FOLDER']

        with open(arguments['DUPLICATES_JSON'], errors='ignore') as f:
            duplicates = json.load(f)
            all_to_remove = set()  # type: Set[str]
            for duplicate_cluster in duplicates:
                # Keep the first element, everything else should be ignored
                all_to_remove.update(duplicate_cluster[1:])

        # Extract graphs
        outputs = explore_files(walk_dir, all_to_remove, monitoring, type_lattice)

        # Save results
        with ChunkWriter(out_folder=arguments['SAVE_FOLDER'], file_prefix='all-graphs',
                max_chunk_size=5000, file_suffix='.jsonl.gz') as writer:
            for graph in outputs:
                writer.add(graph)
    except bdb.BdbQuit:
        return
    except Exception as e:
        print("e: ", e)
        print(monitoring.current_repo)
        print(monitoring.file)

    print("Building and saving the type graph...")
    type_lattice.build_graph()
    save_jsonl_gz([type_lattice.return_json()], os.path.join(arguments['SAVE_FOLDER'], "_type_lattice.json.gz"))

    print("Done.")
    print(f"Generated {monitoring.count - len(monitoring.errors)} graphs out of {monitoring.count} snippets")

    with open(os.path.join(arguments['SAVE_FOLDER'], 'logs_graph_generator.txt'), 'w') as f:
        for item in monitoring.errors:
            try:
                f.write(f"{item}\n")
            except:
                pass

    print("\nExecution in: ", time.clock() - start_time, " seconds")


if __name__ == '__main__':
    args = docopt(__doc__)
    run_and_debug(lambda: main(args), args['--debug'])
