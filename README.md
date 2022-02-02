# Forecast Hub Validations

This repository contains the source code for the implementation of the validation rules that are enforced on forecast submissions in the form of pull requests to forecast hub repositories. The validations were adapted from the [covid19-forecast-hub](https://github.com/reichlab/covid19-forecast-hub) repo for the [2022 FluSight hospitalization forecasting project](https://github.com/cdcepi/Flusight-forecast-data). 

The vision is that this code (which is under active development) could eventually serve as a general validations repository for forecast hubs. A key difference from the main branch of this repo, which runs the validations for the [covid19-forecast-hub](https://github.com/reichlab/covid19-forecast-hub), is that we have implemented validations based on project-specific configurations defined in JSON files (e.g. [FluSight 2022](https://github.com/cdcepi/Flusight-forecast-data/blob/master/project-config.json)). 

The main entry point for the code is `main.py`. This script is intended to be run on a Github Actions CI runner. Using the [default environment variables](https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables) set by Github Actions on the worker, the script identifies the PR that it is being run against. 

Using this information, the script downloads the files modified into a temporary directory and runs forecast and, if applicable, metadata validations on these files. 

The script also adds appropriate labels to the PR based on the files changed. The main validations code is present inside the `forecast_validation` directory (a python module).
