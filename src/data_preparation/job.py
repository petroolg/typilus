"""
Usage:
    extractgraphs.py [options] SOURCE_FOLDER DUPLICATES_JSON SAVE_FOLDER TYPING_RULES FLAKE8_DIR

Main file for data preprocessing. Walk recursively through the source folder's files to generate a code graph for each (concatenated in one jsonl output file) and a global type lattice.

Options:
    -h --help              Show this screen.
    --debug                Debugging mode.
"""

from scripts.graph_generator import extract_graphs
from docopt import docopt
from dpu_utils.utils import run_and_debug

if __name__ == '__main__':
    args = docopt(__doc__)
    run_and_debug(lambda: extract_graphs.main(args), args['--debug'])