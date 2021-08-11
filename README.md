# COVID19-forecast Hub Validations

This repository contains the source code for the validations that is run on forecast submission made a Pull Requests to the [covid19-forecast-hub](https://github.com/reichlab/covid19-forecast-hub) repository. 

The main entry point for the code is `main.py`. This script is intended to run on a Github Actions CI runner. Using the [default environment variables](https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables) set by Github Actions on the worker, the script identifies the PR that it is being run against. 

Using this information, the scipt downloads the files modified into a temporary `forecasts` directory and runs model and, if applicable, metadata validations on these files. 

The script also adds appropriate labels to the PR based on the files changed. The main validations code is present inside the `code` directory.
