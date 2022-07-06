import collections
import copy
import glob
import logging
import os
import pathlib
import re
from typing import Any

import dateutil
import pandas as pd
import pykwalify.core
import yaml
from github.File import File

from forecast_validation import PullRequestFileType
from forecast_validation.validation import ValidationStepResult


SCHEMA_FILE = 'forecast_validation/static/schema.yml'
DESIGNATED_MODEL_CACHE_KEY = 'designated_model_cache'

logger = logging.getLogger("hub-validations")


def get_all_metadata_filepaths(store: dict[str, Any]) -> ValidationStepResult:
    directory: pathlib.Path = store["PULL_REQUEST_DIRECTORY_ROOT"]
    metadata_files: list[File] = store["filtered_files"].get(PullRequestFileType.METADATA, [])
    return ValidationStepResult(success=True,
                                to_store={"metadata_files":
                                              {directory / pathlib.Path(f.filename) for f in metadata_files}})


def validate_metadata_contents(metadata, filepath):
    # Initialize output
    is_metadata_error = False
    metadata_error_output = []

    core = pykwalify.core.Core(source_file=filepath, schema_files=[SCHEMA_FILE])
    core.validate(raise_exception=False, silent=True)
    if core.validation_errors:
        metadata_error_output.extend(['METADATA_ERROR: %s' % err for err in core.validation_errors])
        is_metadata_error = True

    pat_model = re.compile(r"metadata-(.+)\.txt")
    model_name_file = re.findall(pat_model, os.path.basename(filepath))[0]

    # This is a critical error and hence do not run further checks.
    if 'model_abbr' not in metadata:
        metadata_error_output.extend(['METADATA_ERROR: model_abbr key not present in the metadata file'])
        is_metadata_error = True
        return is_metadata_error, metadata_error_output

    if model_name_file != metadata['model_abbr']:
        metadata_error_output.append(f"METADATA_ERROR: Model abreviation in metadata inconsistent with folder name "
                                     f"for model_abbr={metadata['model_abbr']} as specified in metadata. NOTE: model "
                                     f"name on file is: {model_name_file}")
        is_metadata_error = True

    # Check if forecast_startdate is date
    if 'forecast_startdate' in metadata:
        forecast_startdate = str(metadata['forecast_startdate'])
        try:
            dateutil.parser.parse(forecast_startdate)
            is_date = True
        except ValueError:
            is_date = False
        if not is_date:
            is_metadata_error = True
            metadata_error_output += [
                "METADATA ERROR: %s forecast_startdate %s must be a date and should be in YYYY-MM-DD format" %
                (filepath, forecast_startdate)]

    # Check if this_model_is_an_ensemble and this_model_is_unconditional are boolean
    boolean_fields = ['this_model_is_an_ensemble', 'this_model_is_unconditional',
                      'include_in_ensemble_and_visualization', 'ensemble_of_hub_models']
    for field in boolean_fields:
        if (field in metadata) and (metadata[field] not in ['true', 'false']):  # possible_booleans
            is_metadata_error = True
            metadata_error_output += [
                "METADATA ERROR: %s '%s' field must be lowercase boolean (true, false) not '%s'" %
                (filepath, field, metadata[field])]

    # Validate licenses
    license_df = pd.read_csv('forecast_validation/static/accepted-licenses.csv')
    accepted_licenses = list(license_df['license'])
    if ('license' in metadata) and (metadata['license'] not in accepted_licenses):
        is_metadata_error = True
        metadata_error_output += [
            "METADATA ERROR: %s 'license' field must be in `accepted-licenses.csv` 'license' column '%s'" %
            (filepath, metadata['license'])]

    return is_metadata_error, metadata_error_output


def validate_metadata_files(store: dict[str, Any]) -> ValidationStepResult:
    success: bool = True
    comments: list[str] = []
    errors: dict[os.PathLike, list[str]] = {}

    # check individual metadata files
    logger.info("Checking metadata content...")
    for file in store["metadata_files"]:
        logger.info("  Checking metadata content for %s", file)
        is_metadata_error, metadata_error_output = check_metadata_file(file)
        if not is_metadata_error:
            logger.info("    %s content validated", file)
            comments.append(f"✔️ {file} passed (non-filename) content checks.")
        else:
            file_result = [f"Error when validating metadata content: " + e for e in metadata_error_output]
            success = False
            error_list = errors.get(file, [])
            error_list.extend(file_result)
            errors[file] = error_list
            for error in file_result:
                logger.error("    " + error)

    # check metadata files at the team level to validate `team_model_designation`
    if store["HUB_REPOSITORY_NAME"] == "reichlab/covid19-forecast-hub":  # todo should not be hard-coded
        error_str = _validate_team_model_designation(store)
        if error_str:
            success = False
            comments.append(error_str)

    return ValidationStepResult(success=success, comments=comments, file_errors=errors)


def check_metadata_file(filepath):
    with open(filepath, 'rt', encoding='utf8') as stream:
        try:
            metadata = yaml.load(stream, Loader=yaml.BaseLoader)  # specify Loader to avoid true/false auto conversion
            is_metadata_error, metadata_error_output = validate_metadata_contents(metadata, filepath.as_posix())
            if is_metadata_error:
                return True, metadata_error_output
            else:
                return False, "no errors"
        except yaml.YAMLError as exc:
            return True, [
                "METADATA ERROR: Metadata YAML Format Error for %s file. \
                    \nCommon fixes (if parse error message is unclear):\
                    \n* Try converting all tabs to spaces \
                    \n* Try copying the example metadata file and follow formatting closely \
                    \n Parse Error Message:\n%s \n"
                % (filepath, exc)]


# Check for metadata file
def check_for_metadata(store: dict[str, Any], filepath, cache={}):
    meta_error_outputs = {}
    is_metadata_error = False
    txt_files = []
    for metadata_file in glob.iglob(filepath + "*.txt", recursive=False):
        txt_files += [os.path.basename(metadata_file)]
    is_metadata_error, metadata_error_output = False, "no errors"
    for metadata_filename in txt_files:
        metadata_filepath = filepath + metadata_filename
        is_metadata_error, metadata_error_output = check_metadata_file(metadata_filepath)
        if is_metadata_error:
            meta_error_outputs[metadata_filepath] = metadata_error_output

    return is_metadata_error, meta_error_outputs


def get_metadata_model(filepath):
    team_model = os.path.basename(os.path.dirname(filepath))
    metadata_filename = "metadata-" + team_model + ".txt"
    metdata_dir = filepath + metadata_filename
    model_name = None
    model_abbr = None
    with open(metdata_dir, 'r') as stream:
        try:
            metadata = yaml.safe_load(stream)
            # Output model name and model abbr if exists
            if 'model_name' in metadata.keys():
                model_name = metadata['model_name']
            if 'model_abbr' in metadata.keys():
                model_abbr = metadata['model_abbr']

            return model_name, model_abbr
        except yaml.YAMLError as exc:
            return None, None


def output_duplicate_models(existing_metadata_name, output_errors):
    for mname, mfiledir in existing_metadata_name.items():
        if len(mfiledir) > 1:
            error_string = ["METADATA ERROR: Found duplicate model abbreviation %s - in %s metadata" %
                            (mname, mfiledir)]
            output_errors[mname + "METADATA model_name"] = error_string
    return output_errors


#
# `team_model_designation` functions
#

def _validate_team_model_designation(store):
    """
    `validate_metadata_files()` helper that checks metadata files at the team level to validate
    `team_model_designation`. The rule (from https://github.com/reichlab/covid19-forecast-hub/wiki/Metadata-Checks ):

        `team_model_designation` should be one of `primary`, `secondary`, `proposed`, or `other`. There should be only
        one `primary` model for every `model_abbr`.

    :return: error_str as returned by `_compare_team_model_desig_dicts()`
    """
    pr_dict = _team_model_desig_dict_from_pr(store)
    repo_dict = _team_model_desig_dict_from_repo(store, pr_dict.keys())
    return _compare_team_model_desig_dicts(repo_dict, pr_dict)


def _compare_team_model_desig_dicts(repo_dict, pr_dict):
    """
    Compares the result of merging pr_dict into repo_dict. The rule: A team's models' `team_model_designation` values
    are valid if there is either zero or one 'primary' one.

    :param repo_dict: a model_designation_dict from the repo. see `_team_model_desig_dict_from_pr()` for details
    :param pr_dict: "" from the PR
    :return: error_str: either '' (empty) if the merged dicts are valid, or a string describing how the merged dicts are
        invalid
    """
    # update repo_dict from pr_dict
    repo_dict = copy.deepcopy(repo_dict)
    for team_abbr, model_designation_dict in pr_dict.items():
        if team_abbr in repo_dict:
            repo_dict[team_abbr].update(model_designation_dict)
        else:
            repo_dict[team_abbr] = model_designation_dict

    # use a dict that maps {team_abbr -> list_of_primary_model_abbrs} to help filter out valid teams
    team_primary_models_dict = collections.defaultdict(list)
    for team_abbr, model_designation_dict in repo_dict.items():
        for model_abbr, team_model_desig in model_designation_dict.items():
            if team_model_desig == 'primary':
                team_primary_models_dict[team_abbr].append(model_abbr)

    # get invalid teams and return results
    ge_2_primary_teams = {team_abbr: model_abbrs for team_abbr, model_abbrs in team_primary_models_dict.items()
                          if len(model_abbrs) >= 2}
    if ge_2_primary_teams:
        team_model_strs = []
        for team_abbr, model_abbrs in team_primary_models_dict.items():
            team_model_strs.extend([f"'{team_abbr}-{model_abbr}'" for model_abbr in model_abbrs])
        return f"❌ PR merge would result in team_model_designations with more than one 'primary' model for the " \
               f"same team: {', '.join(team_model_strs)}"
    else:
        return ''


def _team_model_desig_dict_from_pr(store):
    """
    :param store: a dict that contains the "metadata_files" key -> list of metadata file Paths
    :return: a model_designation_dict from the metadata files in `store`. the dict maps
        team_abbr -> model_designation_dict, where model_designation_dict maps model_abbr -> team_model_designation.
        team_model_designation is one of: 'primary', 'secondary', 'proposed', or 'other'. For example:
            {'teamA': {'model1': 'primary', 'model2': 'primary'},
             'teamB': {'model3': 'primary', 'model4': 'primary'}}
    """
    # note that we assume each team has unique models. if not, this will be caught by
    # other validations, but this check will be incorrect b/c data will be overwritten
    team_model_designation_dict = collections.defaultdict(collections.defaultdict)
    for metadata_file in store["metadata_files"]:
        with open(metadata_file) as fp:
            metadata = yaml.safe_load(fp)
            model_name = metadata['model_name']  # ex: 'baseline'
            model_abbr = metadata['model_abbr']  # ex: 'COVIDhub-baseline'
            team_abbr = model_abbr.split('-')[0]  # ex: 'COVIDhub'
            team_model_desig = metadata['team_model_designation']  # ex: 'primary'
            team_model_designation_dict[team_abbr][model_name] = team_model_desig

    return team_model_designation_dict


def _team_model_desig_dict_from_repo(store, team_abbrs):
    """
    :param store: a dict containing the "repository" key -> a github.Repository
    :param team_abbrs: a set of team_abbr's to limit the search to. typically pulled from metadata files in a PR
    :return: a model_designation_dict (same as `_team_model_desig_dict_from_pr()` - see)
    """
    repo = store["repository"]
    data_processed_dirs = repo.get_contents(store["FORECAST_FOLDER_NAME"])
    team_model_designation_dict = collections.defaultdict(collections.defaultdict)
    for data_processed_dir in data_processed_dirs:
        team_abbr = data_processed_dir.name.split('-')[0]  # e.g., 'COVIDhub'
        if team_abbr not in team_abbrs:
            continue

        metadata_file_path = f'{data_processed_dir.path}/metadata-{data_processed_dir.name}.txt'
        metadata_file = repo.get_contents(metadata_file_path)
        metadata = yaml.safe_load(metadata_file.decoded_content)
        team_model_designation_dict[team_abbr][metadata['model_name']] = metadata['team_model_designation']

    return team_model_designation_dict
