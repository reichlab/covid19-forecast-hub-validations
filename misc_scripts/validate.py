def validate() -> None:
    """Entry point and main body of validations script.
    """

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
        logger.info("PR %s can be automerged", pull_request_number)
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
