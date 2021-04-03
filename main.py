import json
import re
import os
import sys
import urllib.request
import glob
from github import Github

from code.validation_functions.metadata import check_for_metadata, get_metadata_model, \
    output_duplicate_models
from code.validation_functions.forecast_filename import validate_forecast_file_name
from code.validation_functions.forecast_date import filename_match_forecast_date
from code.test_formatting import forecast_check, validate_forecast_file, print_output_errors

from model_utils import *

validations_version = 2

# Pattern that matches a forecast file add to the data-processed folder.
# Test this regex usiing this link: https://regex101.com/r/f0bSR3/1 
pat = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$")
# pat_other = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-(.+)\.csv$")
pat_other = re.compile(r"^data-processed/(.+)\.csv$")

pat_meta = re.compile(r"^data-processed/(.+)/metadata-\1\.txt$")

local = os.environ.get('CI') != 'true'
# local = True
if local:
    token = None
    print("Running on LOCAL mode!!")
else:
    print("Added token")
    token = os.environ.get('GH_TOKEN')

if token is None:
    g = Github()
else:
    g = Github(token)
repo_name = os.environ.get('GITHUB_REPOSITORY')
if repo_name is None:
    repo_name = 'reichlab/covid19-forecast-hub'
repo = g.get_repo(repo_name)

print(f"Github repository: {repo_name}")
print(f"Github event name: {os.environ.get('GITHUB_EVENT_NAME')}")

if not local:
    event = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))
else:
    event = json.load(open("test/test_event.json"))

pr = None
comment = ''
files_changed = []

if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target' or local:
    # Fetch the  PR number from the event json
    pr_num = event['pull_request']['number']
    print(f"PR number: {pr_num}")

    # Use the Github API to fetch the Pullrequest Object. Refer to details here: https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html 
    # pr is the Pullrequest object
    pr = repo.get_pull(pr_num)

    # fetch all files changed in this PR and add it to the files_changed list.
    files_changed += [f for f in pr.get_files()]

# Split all files in `files_changed` list into valid forecasts and other files
forecasts = [file for file in files_changed if pat.match(file.filename) is not None]
forecasts_err = [file for file in files_changed if pat_other.match(file.filename) is not None]
metadatas = [file for file in files_changed if pat_meta.match(file.filename) is not None]
other_files = [file for file in files_changed if
               pat.match(file.filename) is None and pat_meta.match(file.filename) is None]

changed_forecasts = False

if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
    # IF there are other fiels changed in the PR 
    # TODO: If there are other files changed as well as forecast files added, then add a comment saying so.
    if len(other_files) > 0 and len(forecasts) > 0:
        print(f"PR has other files changed too.")
        if pr is not None:
            pr.add_to_labels('other-files-updated')
    # if there are no forecasts matched to the valid regex and the PR has added a CSV file to the data-processed drectory, most likely, it is an erroneous 
    # forecast which should be caught.
    # TODO: add more documentation for this logic
    if len(forecasts) == 0 and len(forecasts_err) > 0:
        comment += f"\n\nYou seem to have added a forecast in an incorrect format. Please refer to https://github.com/reichlab/covid19-forecast-hub/tree/master/data-processed#data-formatting to correct your error.\n\n "

    if len(metadatas) > 0:
        print(f"PR has metata files changed.")
        if pr is not None:
            pr.add_to_labels('metadata-change')
    # Do not require this as it is done by the PR labeler action.
    # else:
    #     if pr is not None:
    #         pr.add_to_labels('data-submission')

# deleted_forecasts = False
# `f` is an object of type: https://pygithub.readthedocs.io/en/latest/github_objects/File.html 
# `forecasts` is a list of `File`s that are changed in the PR.
for f in forecasts:
    # Taken from https://github.com/KITmetricslab/covid19-forecast-hub-de-validations/blob/main/main.py#L113 
    # if file status is not "added" it is probably "renamed" or "changed"
    if f.status == "modified":
        # If file is modified, fetch the original one and save it to the forecasts_master directory
        get_model_master(repo, filename=f.filename)
    changed_forecasts = changed_forecasts or (f.status != "added")

if changed_forecasts and not local:
    # Add the `forecast-updated` label when there are deletions in the forecast file
    pr.add_to_labels('forecast-updated')
    comment += "\n Your submission seem to have updated/deleted some forecasts. Could you provide a reason for the updation/deletion and confirm that any updated forecasts only used data that were available at the time the original forecasts were made?\n\n"

# Download all forecasts
# create a forecasts directory
os.makedirs('forecasts', exist_ok=True)

# Download all forecasts changed in the PR into the forecasts folder
for f in forecasts:
    urllib.request.urlretrieve(f.raw_url, f"forecasts/{f.filename.split('/')[-1]}")

# Download all metadat files changed in the PR into the forecasts folder
for f in metadatas:
    urllib.request.urlretrieve(f.raw_url, f"forecasts/{f.filename.split('/')[-1]}")

# Run validations on each of these files
errors = {}
for file in glob.glob("forecasts/*.csv"):
    error_file = forecast_check(file)
    if len(error_file) > 0:
        errors[os.path.basename(file)] = error_file

    f_name = os.path.basename(file)
    with open(f"forecasts_master/{f_name}", 'r') as f:
        print("Checking old forecast for any retractions")
        if compare_forecasts(old=f, new=open(file, 'r')) and not local:

            pr.add_to_labels('forecast-retraction')

    # Check for the forecast date column check is +-1 day from the current date the PR build is running
    is_val_err, err_message = filename_match_forecast_date(file)
    if is_val_err:
        comment += err_message

# Check for metadata file validation
FILEPATH_META = "forecasts/"
is_meta_error, meta_err_output = check_for_metadata(filepath=FILEPATH_META)

if len(errors) > 0:
    comment += "\n\n Your submission has some validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
    print_output_errors(errors, prefix='data')

if is_meta_error:
    comment += "\n\n Your submission has some metadata validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
    print_output_errors(meta_err_output, prefix="metadata")

# add the consolidated comment to the PR
if comment != '' and not local:
    pr.create_issue_comment(comment)

# Check if PR could be merged automatically
# Logic - The PR is set to automatically merge if ALL the following conditions are TRUE: 
#  - If there are no comments added to PR
#  - If it is not run locally
#  - If there are not metadata errors
#  - If there were no validation errors
#  - If there were any other files updated which includes: 
#      - any errorneously named forecast file in data-processed folder
#      - any changes/additions on a metadata file. 
#  - There is ONLY 1 valid forecast file added that has passed the validations. That means, there was atleast one valid forecast file (that also passed the validations) added to the PR.

if comment == '' and not local and not is_meta_error and len(errors) == 0 and (
        len(metadatas) + len(other_files)) == 0 and len(forecasts_err) == len(forecasts) and len(
        forecasts) == 1:
    print(f"Auto merging PR {pr_num if pr_num else -1}")
    pr.add_to_labels('automerge')

print(f"Using validations version {validations_version}")
# fail validations build if any error occurs.
if is_meta_error or len(errors) > 0:
    sys.exit("\n ERRORS FOUND EXITING BUILD...")
