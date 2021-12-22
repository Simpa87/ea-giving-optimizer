# ea-giving-optimizer
Tool for running scenarios with different assumptions (returns, discounting, leaking money) to see total lifetime giving


## 1. Set up a virtualenv and activate it
The library specific virtualenv should be located in the library specific root folder

```bash
python3 -m venv .env 
source .env/bin/activate
```

## 2. Install dependencies
cd to root where setup.py is, and make sure right virtualenv is activated
```bash
pip install -e .
```

## 3. Open notebook
Go to ea_giving_optimizer and check out the notebook or create your own and explore!

## Optional - Set up pytest for unit tests in Pycharm
- Make sure pytest is added in a test section of the setup.py file, and that it is installed in the virtualenv
- From the configuration panel up in the top right of Pycharm, select Edit configurations from the dropdown
- Click the + sign to add a new configuration and go to Python tests --> pytest
- In "Target:", select script path, and add the path for the tests folder (or specific script in it)
- Also select the right virtualenv for the project to run the tests in that window
- After Pycharm has updated, you should be able to run all tests for the script file at once (play button in top right panel), or run individual tests with a play button on the test function