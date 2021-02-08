
import json
import re
import os
import urllib.request
import glob
from github import Github


from code.validation_functions.metadata import check_for_metadata, get_metadata_model, output_duplicate_models
from code.validation_functions.forecast_filename import validate_forecast_file_name
from code.validation_functions.forecast_date import filename_match_forecast_date
from code.test_formatting import forecast_check, validate_forecast_file, print_output_errors

# Pattern that matches a forecast file add to the data-processed folder.
# Test this regex usiing this link: https://regex101.com/r/f0bSR3/1 
pat = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$")


local = os.environ.get('CI') != 'true'
# local = True
if local:
    token = None
    print("Running on LOCAL mode!!")
else:
    print("Added token")
    token  = os.environ.get('GH_TOKEN')
    print(f"Token length: {len(token)}")

if token is None:
    g = Github()
else:
    g = Github(token)
repo_name = os.env.get('GITHUB_REPOSITORY')
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
    files_changed +=[f for f in pr.get_files()]

# Split all files in `files_changed` list into valid forecasts and other files
forecasts = [file for file in files_changed if pat.match(file.filename) is not None]
other_files = [file for file in files_changed if pat.match(file.filename) is None]

if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
    # IF there are other fiels changed in the PR 
    #TODO: If there are other files changed as well as forecast files added, then add a comment saying so. 
    if len(other_files) > 0 and len(forecasts) >0:
        print(f"PR has other files changed too.")
        if pr is not None:
            pr.add_to_labels('other-files-updated')
    # Do not require this as it is done by the PR labeler action.
    # else:
    #     if pr is not None:
    #         pr.add_to_labels('data-submission')

    deleted_forecasts = False
    
    # `f` is ab object of type: https://pygithub.readthedocs.io/en/latest/github_objects/File.html 
    # `forecasts` is a list of `File`s that are changed in the PR.
    for f in forecasts:
        # TODO: Add a better way of checking whether a file is deleted or not. Currently, this checks if there are ANY deletion in a forecast file.
        if f.deletions >0:
            deleted_forecasts = True
    if deleted_forecasts:
        # Add the `forecast-updated` label when there are deletions in the forecast file
        pr.add_to_labels('forecast-updated')
        comment += "\n Your submission seem to have updated/deleted some forecasts. Could you provide a reason for the updation/deletion? Thank you!\n\n"


# Download all forecasts
# create a forecasts directory
os.makedirs('forecasts', exist_ok=True)

# Download all forecasts changed in the PR into the forecasts folder
for f in forecasts:
    urllib.request.urlretrieve(f.raw_url, f"forecasts/{f.filename.split('/')[-1]}")


# Run validations on each of these files
errors = {}
for file in glob.glob("forecasts/*.csv"):
    error_file = forecast_check(file)
    if len(error_file) >0:
        errors[os.path.basename(file)] = error_file
    
    # Check for the forecast date column check is +-1 day from the current date the PR build is running
    is_err, err_message = filename_match_forecast_date(file)
    if is_err:
        comment+= err_message
if len(errors) > 0:
    comment+="\n\n Your submission has some validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
    print_output_errors(errors, prefix='data')

# add the consolidated comment to the PR
if comment!='' and not local:
    pr.create_issue_comment(comment)





