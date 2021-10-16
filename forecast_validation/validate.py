def check_new_model(
    file: pathlib.Path,
    existing_models: list[str],
    all_labels: dict[str, list[Label]],
    *, # forces latter parameters to be keyword-only arguments
    labels_to_apply: Optional[list[Label]] = None,
    comments_to_apply: Optional[list[str]] = None
) -> None:

    model = '-'.join(file.stem.split('-')[-2:])  
    if model not in existing_models:
        labels_to_apply.append(all_labels['new-team-submission'])
        if not os.path.isfile(f"forecasts/metadata-{model}.txt"):
            error_str = (
                "This seems to be a new submission and you have not "
                "included a metadata file."
            )
            if file_path.name in errors:
                errors[file_path.name].append(error_str)
            else:
                errors[file_path.name] = [error_str]

def validate() -> None:
    """Entry point and main body of validations script.
    """

    # Run validations on each of these files
    errors = {}
    is_forecast_date_mismatch = False
    for file_path in FORECASTS_DIRECTORY.glob("*.csv"):

        # zoltpy checks
        file_error = forecast_check(file_path)

        # everything below - hub-specific checks

        # extract just the filename and remove the path.
        if file_error:
            errors[file_path.name] = file_error

        # Check whether the `model_abbr` directory is present in the
        # `data-processed` folder.
        # This is a test to check if this submission is a new submission or not

        # extract model_abbr from the filename
        model = '-'.join(file_path.stem.split('-')[-2:])  
        if model not in models:
            labels.append('new-team-submission')
            if not os.path.isfile(f"forecasts/metadata-{model}.txt"):
                error_str = (
                    "This seems to be a new submission and you have not "
                    "included a metadata file."
                )
                if file_path.name in errors:
                    errors[file_path.name].append(error_str)
                else:
                    errors[file_path.name] = [error_str]

        # Check for implicit and explicit retractions
        # `forecasts_master` is a directory with the older version of the
        # forecast (if present).
        if os.path.isfile(f"forecasts_master/{file_path.name}"):
            with open(f"forecasts_master/{file_path.name}", 'r') as f:
                print("Checking old forecast for any retractions")
                compare_result = compare_forecasts(
                    old_forecast_file_path=f,
                    new_forecast_file_path=open(file_path, 'r')
                )
                if compare_result['invalid']:
                    error_msg = compare_result['error']
                    # if there were no previous errors
                    if len(file_error) == 0:
                        errors[file_path.name] = [compare_result['error']]
                    else:
                        errors[file_path.name].append(compare_result['error'])
                if compare_result['implicit-retraction']:
                    labels.append('forecast-implicit-retractions')
                    retract_error = (
                        f"The forecast {file_path.name} has an invalid "
                        "implicit retraction. Please review the retraction "
                        "rules for a forecast in the wiki here - "
                        "https://github.com/reichlab/covid19-forecast-hub/wiki/Forecast-Checks"
                    )
                    # throw an error now with Zoltar 4
                    if len(file_error) == 0:
                        errors[file_path.name] = [retract_error]
                    else:
                        errors[file_path.name].append(retract_error)
                # explicit retractions
                if compare_result['retraction']:
                    labels.append('retractions')

        # Check for the forecast date column check is +-1 day from the current
        # date the PR build is running
        is_forecast_date_mismatch, err_message = \
            check_filename_match_forecast_date(file_path)
        if is_forecast_date_mismatch:
            comments.append(err_message)

    # Check for metadata file validation
    FILEPATH_META = "forecasts/"
    is_meta_error, meta_err_output = check_for_metadata(filepath=FILEPATH_META)

    if len(errors) > 0:
        comments.append(
            "Your submission has some validation errors. Please check the logs "
            "of the build under the \"Checks\" tab to get more details about "
            "the error."
        )
        print_output_errors(errors, prefix='data')

    if is_meta_error:
        comments.append(
            "Your submission has some metadata validation errors. Please check "
            "the logs of the build under the \"Checks\" tab to get more "
            "details about the error. "
        )
        print_output_errors(meta_err_output, prefix="metadata")

    # add the consolidated comment to the PR
    if comments:
        pull_request.create_issue_comment("\n\n".join(comments))

    # Check if PR could be merged automatically
    # Logic - The PR is set to automatically merge
    # if ALL the following conditions are TRUE: 
    #  - If there are no comments added to PR
    #  - If it is not run locally
    #  - If there are not metadata errors
    #  - If there were no validation errors
    #  - If there were any other files updated which includes: 
    #      - any errorneously named forecast file in data-processed folder
    #      - any changes/additions on a metadata file. 
    #  - There is ONLY 1 valid forecast file added that passed the validations.
    #    That means, there was atleast one valid forecast file
    #    (that also passed the validations) added to the PR.

    no_errors: bool = len(errors) == 0
    has_non_csv_or_metadata: bool = (
            len(filtered_files[FileType.METADATA]) +
            len(filtered_files[FileType.OTHER_NONFS])
    ) != 0
    only_one_forecast_csv: bool = len(filtered_files[FileType.FORECAST]) == 1
    all_csvs_in_correct_location: bool = (
        len(filtered_files[FileType.OTHER_FS]) ==
        len(filtered_files[FileType.FORECAST])
    )

    if (comments and
        not is_meta_error and
        no_errors and 
        not has_non_csv_or_metadata and 
        all_csvs_in_correct_location and
        only_one_forecast_csv
    ):
        logger.info("Auto merging PR %s", pull_request_number)
        labels.append(all_labels['automerge'])

    # set labels: labeler labels + validation labels
    labels_to_set = labels + list(filter(
        lambda l: l.name in {'data-submission', 'viz', 'code'},
        pull_request.labels)
    )
    if len(labels_to_set) > 0:
        pull_request.set_labels(*labels_to_set)

    print(f"Using validations version {VALIDATIONS_VERSION}")
    # fail validations build if any error occurs.
    if is_meta_error or len(errors) > 0 or is_forecast_date_mismatch:
        sys.exit("\n ERRORS FOUND EXITING BUILD...")
