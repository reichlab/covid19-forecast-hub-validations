import os
import sys

path = sys.argv[1]
print(sys.argv)

os.system('pipenv run python3 main.py '+path)

