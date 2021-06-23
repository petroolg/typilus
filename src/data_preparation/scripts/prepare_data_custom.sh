#!/usr/bin/env bash

cd /usr/data

###
# Run deduplication. This assumes that .NET Core is installed.
###

git clone --depth=1 https://github.com/microsoft/near-duplicate-code-detector.git
mkdir -p ./repo_tokens
python3 ./near-duplicate-code-detector/tokenizers/python/tokenizepythoncorpus.py ./bug/ ./repo_tokens/
echo "In " $PWD
dotnet run --project ./near-duplicate-code-detector/DuplicateCodeDetector/DuplicateCodeDetector.csproj -- --dir="./repo_tokens/" "./corpus_duplicates"

###
# Run AST extraction.
###

readonly SRC_BASE="/usr/src/datasetbuilder/scripts/"
export PYTHONPATH="$SRC_BASE"
mkdir -p graph-dataset
python3 /usr/src/datasetbuilder/job.py ./bug/ ./corpus_duplicates.json ./graph-dataset $SRC_BASE/../metadata/typingRules.json ./flake8/
mkdir -p graph-dataset-split
python3 /usr/src/datasetbuilder/scripts/utils/split.py -data-dir ./graph-dataset -out-dir ./graph-dataset-split
