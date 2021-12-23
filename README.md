# ea-giving-optimizer
Tool for running scenarios with different assumptions (returns, discounting, leaking money) to see total lifetime giving.
The idea is to be able to model trade-offs with different assumptions:
- Interest on money saved to give more later (stock market return etc.)
- Cost of waiting
  - Existential risk compounding
  - Though saving QALY in the future might be as valuable as now, the problem of global suffering might be bigger now
  - Risk of "leaking" from intended giving to other causes (loans to relatives, inheritance etc., bigger amounts later "feeling more expensive")
- Constraints
  - Might need minimum amount X at age Y (apartment, retirement)

<b>Draft version:</b><br>
This is a draft version and costs for waiting are not yet implemented, hence the current solution is trivial - just wait as long as possible with giving after return on the savings. 


## 1. Set up a virtualenv and activate it
It is suggested to create a virtualenv for installing required dependencies in it

```bash
python3 -m venv .env 
source .env/bin/activate
```

## 2. Install dependencies
cd to root where setup.py is, and make sure the right virtualenv is activated
```bash
pip install -e .
```

## 3. Open notebook and explore
Having the virtualenv activated and being in the project directory, launch jupyter notebook and explore (e.g. check out the example notebook in ea_giving_optimizer)
```bash
jupyter notebook
```

## Optional - Set up pytest for unit tests in Pycharm
- Having installed pytest from the dependencies, from the configuration panel up in the top right of Pycharm, select Edit configurations from the dropdown
- Click the + sign to add a new configuration and go to Python tests --> pytest
- In "Target:", select script path, and add the path for the tests folder (or specific script in it)
- Also select the right virtualenv for the project to run the tests in that window
- After Pycharm has updated, you should be able to run all tests for the script file at once (play button in top right panel), or run individual tests with a play button on the test function
