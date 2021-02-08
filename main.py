
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

pat = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$")

forecasts = []

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
repo = g.get_repo('hannanabdul55/covid19-forecast-hub')
print(f"Github event name: {os.environ.get('GITHUB_EVENT_NAME')}")

if not local:
    event = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))
else:
    event = json.load(open("test/test_event.json"))

# print(f"Event: {event}")
pr = None
comment = ''
if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target' or local:
    # pr_num = int(os.environ.get('GITHUB_REF').split('/')[-2])
    pr_num = event['pull_request']['number']
    print(f"PR number: {pr_num}")
    pr = repo.get_pull(pr_num)
    forecasts +=[f for f in pr.get_files()]
forecasts = [file for file in forecasts if pat.match(file.filename) is not None]
other_files = [file for file in forecasts if pat.match(file.filename) is None]

if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
    if len(other_files) > 0:
        print(f"PR has other files changed too.")
    else:
        if pr is not None and not local:
            pr.add_to_labels('data-submission')

    deleted_forecasts = False
    for f in forecasts:
        if f.deletions >0:
            deleted_forecasts = True
    if deleted_forecasts and not local:
        pr.add_to_labels('forecast-updated')
        comment += "\n Your submission seem to have updated/deleted some forecasts. Could you provide a reason for the updation/deletion? Thank you!\n\n"



# print(f"Forecasts updated/added: {forecasts}")

# Download all forecasts
# create a forecasts directory
os.makedirs('forecasts', exist_ok=True)

# Download all forecasts into the forecasts folder
for f in forecasts:
    urllib.request.urlretrieve(f.raw_url, f"forecasts/{f.filename.split('/')[-1]}")


# Run validations on each of these files
errors = {}
for file in glob.glob("forecasts/*.csv"):
    error_file = forecast_check(file)
    if len(error_file) >0:
        errors[os.path.basename(file)] = error_file
    
    # Check for the forecast date column check
    is_err, err_message = filename_match_forecast_date(file)
    if is_err:
        comment+= err_message
if len(errors) > 0:
    comment+="\n\n Your submission has some validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
    print_output_errors(errors, prefix='data')

# add the consolidated comment to the PR
if comment!='' and not local:
    pr.create_issue_comment(comment)





